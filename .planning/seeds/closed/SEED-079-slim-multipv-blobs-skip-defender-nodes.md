---
id: SEED-079
status: dormant
planted: 2026-07-03
planted_during: v1.30 Forcing-Line Tactic Gate (post-release, defender-gate A/B follow-up)
trigger_when: next eval-pipeline / worker-infra milestone, or before the tier-4 blob backfill passes ~30% coverage (the savings shrink as the backfill completes)
scope: Medium
---

# SEED-079: Slim MultiPV blobs — skip defender-node engine evals in flaw-blob building

## Why This Matters

The 2026-07-03 defender-gate A/B (prod-28 + dev-28) settled that the forcing-line
gate must NOT be applied to defender nodes: it would suppress 28.5% of surviving
tags on prod (23.6% even at a lenient 50 cp threshold), concentrated in genuine
tactics (forced mates 265/912 drops, discovered attacks ~75%, sacrifices 62-85%,
depth>=1 tags lose 58-83%). Minimax makes defender-side false positives impossible
in PV-derived data, so the defender MultiPV-2 data has no gating use.

That decision makes defender-node blob content confirmed dead weight:

- **Compute (the big one):** every continuation node costs a 1M-node MultiPV-2
  Stockfish eval. On prod, ~8.0M continuation evals have been paid so far, 4.1M
  (51%) on defender (odd-index) nodes the gate never reads. Blob coverage is only
  ~14% (460k of 3.38M flaws), so skipping defender nodes roughly HALVES the
  remaining tier-4 backfill compute (~doubles throughput).
- **Storage:** blob JSONB is 509 MB (31% of game_flaws' 1.6 GB); defender nodes
  are 46% of stored nodes (~235 MB). `su` (second-best UCI) is written on every
  node but read nowhere in app/ — droppable everywhere.

Gate read surface (verified): only solver nodes (even indices) are read —
only-move check through firing depth, still-winning floor, trailing strip. One
exception: `_is_forced_mate_firing` reads `line[firing_depth]`, which can be a
defender node when the detector reports an odd firing depth (WR-02 k-1 quirk,
mainly DISCOVERED_ATTACK depth 1).

## When to Surface

**Trigger:** next milestone touching the eval pipeline / worker infra, or
proactively while the tier-4 blob backfill is still early (~14% coverage as of
2026-07-03). Value decays as the backfill burns the compute this would save.

## Scope Estimate

**Medium** — a phase. Server-side changes plus one optional worker change:

1. **Tier-4 lease path (no worker update needed, bulk of the win):**
   `_build_flaw_blob_lease_positions` stops emitting odd `node_k`; workers are
   blob-structure-agnostic by design (D-04a opaque tokens).
2. **Assembler:** `_assemble_one_line_blob` walks k=0,1,2,... and BREAKS at the
   first gap — naively leasing only even nodes truncates every line to 1 node and
   the one-mover discard kills everything. Must fill skipped odd indices with
   placeholder PvNodes (all-None) and treat only a missing EVEN node as a gap.
3. **Odd-firing-depth mate exemption:** with placeholder defender nodes,
   `_is_forced_mate_firing` returns False at odd firing depths (loses the
   forced-mate exemption from D-08/D-10 for ~5% of gated tags). Either accept
   (conservative) or normalize the WR-02 depth quirk to even indices first.
4. **Local drain** (`_build_flaw_multipv2_blobs`): backend code, skip odd-k
   engine calls — normal deploy.
5. **Atomic path (Phase 147, optional lazy worker rollout):** the worker
   enumerates blob nodes itself, so compute saving there needs a worker update;
   server can discard odd-node submissions at assembly meanwhile (storage-only).
   Old/new workers coexist safely (server authoritative at submit).

Non-goals: do NOT rewrite existing 460k fat blobs (WAL churn > 235 MB reclaimed;
they also keep historical defender-side re-analysis possible). Mixed fat/slim
blobs stay valid — readers unchanged.

## Breadcrumbs

- `app/services/forcing_line_gate.py` — gate read surface (solver-only, D-10);
  `_is_forced_mate_firing` odd-depth read
- `app/services/eval_drain.py` — `_build_flaw_blob_lease_positions`,
  `_assemble_one_line_blob` (gap-break), `_build_flaw_multipv2_blobs` (local drain)
- `app/schemas/eval_remote.py` — D-04a token scheme `{flaw_ply}:{line}:{node_k}`;
  `FlawBlobLeasePosition`, `AtomicBlobNode`
- `app/services/tactic_detector.py` — WR-02 depth quirk (k-1, odd depths)
- Defender-gate A/B evidence: session scratchpad reports
  `defender-gate-ab-{prod,dev}-28.md` (2026-07-03); harness pattern in
  `scripts/ab_validate_gate.py`
- Prod numbers (2026-07-03): 460,007 blob flaws / 3,380,646 total; 8.93M nodes,
  4.11M defender; blob JSONB 509 MB; avg line length ~9.7 nodes

## Notes

Decision context: defender gate rejected (this A/B); lichess-puzzler likewise
checks uniqueness only on the winner's moves. Slim blobs close the door on
re-running a defender-side A/B on NEW data (old fat blobs keep it partially
open) — accepted trade-off.
