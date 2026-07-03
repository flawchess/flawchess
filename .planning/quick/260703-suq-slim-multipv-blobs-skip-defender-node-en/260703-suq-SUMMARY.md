---
phase: quick-260703-suq
plan: 01
subsystem: eval-pipeline
status: complete
tags: [seed-079, tier-4, multipv, forcing-line-gate, backend]
requires: []
provides:
  - even-only tier-4 flaw-blob leasing (defender nodes never engine-evaluated)
  - placeholder-filling slim-blob assembler (tier-4 + atomic submit paths)
  - slim local drain (_build_flaw_multipv2_blobs skips odd-k engine calls)
affects:
  - app/services/eval_drain.py
  - app/services/forcing_line_gate.py
tech-stack:
  added: []
  patterns:
    - "Slim blob scheme: even indices = real solver nodes, odd indices = all-None placeholder PvNodes (su='')"
    - "Missing EVEN node = gap (stop); missing/extra odd node = placeholder/discarded (server authoritative)"
key-files:
  created: []
  modified:
    - app/services/eval_drain.py
    - app/services/forcing_line_gate.py
    - tests/services/test_eval_drain.py
    - tests/services/test_full_eval_drain.py
    - tests/services/test_forcing_line_gate.py
    - tests/test_eval_worker_endpoints.py
decisions:
  - "SEED-079 item 3 resolved as ACCEPT CONSERVATIVELY: no gate logic change; slim blobs lose the forced-mate exemption at odd firing depths (placeholder read -> bm=None -> False). Normalizing to an even index would read a different node and change credit decisions on the ~460k existing fat blobs — both non-goals."
  - "Old workers' odd-node submissions are discarded at assembly (never read), not rejected: the atomic path validates tokens only structurally (parse + in-game-range), so old atomic workers keep working; tier-4 workers echo server tokens, so post-deploy leases are even-only by construction."
metrics:
  duration: 22min
  completed: 2026-07-03
---

# Quick Task 260703-suq: Slim MultiPV Blobs — Skip Defender-Node Engine Evals Summary

**One-liner:** Tier-4 flaw-blob leases and the local drain now emit/evaluate only even (solver) PV nodes, with all-None placeholder PvNodes reconstructing full-index blobs at assembly — roughly halving the remaining tier-4 blob-backfill Stockfish compute (SEED-079 items 1–5, server-side).

## What Was Built

- **`_placeholder_defender_node()`** (eval_drain.py): the shared all-None `PvNode(b=None, bm=None, s=None, sm=None, su="")` odd-index placeholder (su str, never None — Pitfall 3), reused by both assembly paths.
- **Even-only tier-4 leasing** (`_build_flaw_blob_lease_positions`): token emission iterates `range(0, len(walk), 2)` — defender (odd) nodes are never leased. The `len(walk) < 2` sentinel semantics are unchanged. Workers are blob-structure-agnostic (D-04a opaque tokens), so no worker update is needed for the bulk of the win.
- **Placeholder-filling assembler** (`_assemble_one_line_blob`): walks even k in steps of 2, inserting the placeholder for each skipped odd index before each real node; a missing EVEN node is a gap (stop). The blob therefore always ends on a real even solver node, preserving `_strip_trailing_only_moves`' "last solver node is real" assumption. Odd-k entries in `node_results` (old fat-lease/atomic workers) are never read — server-authoritative discard (item 5). This one function covers both the tier-4 `/flaw-blob-submit` path and the Phase 147 `/atomic-submit` path (both route through `_assemble_flaw_blobs_from_submit`).
- **Slim local drain** (`_build_flaw_multipv2_blobs` + `_build_line_blobs`): both continuation-gather loops enqueue only even indices >= 2, so defender boards never reach `engine_service.evaluate_nodes_multipv2`; `_build_line_blobs` keeps node-0 assembly from `pos_eval` + `second_best_map` unchanged and fills odd indices with the placeholder.
- **Odd-firing-depth mate exemption — conservative acceptance** (forcing_line_gate.py): documentation-only change on `_is_forced_mate_firing`. On a slim blob with an odd `firing_depth` (WR-02 k-1 quirk, mainly DISCOVERED_ATTACK depth 1, ~5% of gated tags) the function reads a placeholder and returns False — the D-08/D-10 forced-mate exemption conservatively degrades to non-exempt. Fat blobs are unaffected (their odd nodes carry real data). No gate logic changed; the solver-node read surface is untouched.

## Task Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| 1 (RED) | 3f68131b | test | Failing tests: even-only leasing + slim assembler + odd-discard + fat/slim gate parity |
| 1 (GREEN) | e9cc6660 | feat | Even-only tier-4 leasing + placeholder-filling assembler (items 1, 2, 5) |
| 2 (RED) | 64129c1d | test | Failing tests: slim `_build_line_blobs` + drain-tick placeholder assertions |
| 2 (GREEN) | 49a57cc1 | feat | Slim local drain — skip odd-k defender engine calls (item 4) |
| 3 | d8b81a14 | docs | Conservative odd-firing acceptance documented + 4 slim-blob gate tests (item 3) |

## Verification

- `uv run ty check app/ tests/` — zero errors.
- `uv run ruff check app/ tests/` + `ruff format` — clean.
- Targeted: `tests/services/test_eval_drain.py` + `test_full_eval_drain.py` + `test_forcing_line_gate.py` + `tests/test_eval_worker_endpoints.py` — 229 passed.
- Full backend suite `uv run pytest -n auto -x` — **3168 passed, 18 skipped**.
- Endpoint lease-length asserts checked: the roundtrip/sentinel submit tests echo leased tokens (adapt automatically); the two tests that hard-coded fat node counts (`test_blob_lease_token_parses_correctly`, `test_blob_assembly_full_sequence_assembles_pvnodes`) were updated to the even-only contract.
- No DB migration; existing 460k fat blobs untouched; mixed fat/slim blobs valid (gate reads only solver nodes).

## TDD Gate Compliance

Tasks 1 and 2 followed RED → GREEN: failing-test commits (3f68131b, 64129c1d) verified failing before their implementation commits (e9cc6660, 49a57cc1). Task 3 was documentation + tests only (no logic change to fail against).

## Deviations from Plan

**1. [Rule 3 - Blocking] Updated two fat-contract tests in tests/test_eval_worker_endpoints.py**
- **Found during:** Task 1
- **Issue:** `test_blob_lease_token_parses_correctly` asserted missed k=[0,1,2] / allowed k=[0,1], and `test_blob_assembly_full_sequence_assembles_pvnodes` submitted k=0,1 expecting a 2-node blob — both encode the fat (defender-inclusive) contract the plan removes. The file was not in the plan's `files_modified` but is in its verification command.
- **Fix:** Updated both to the even-only/slim contract (even tokens only; odd index asserted to be the all-None placeholder).
- **Files modified:** tests/test_eval_worker_endpoints.py
- **Commit:** 3f68131b

No other deviations — plan executed as written.

## Operational Notes

- **In-flight tier-4 leases at deploy time:** a worker holding a pre-deploy fat lease (odd tokens included) will get its whole submit 422'd by the T-145-09 re-derived-lease validation once the server is even-only. This is a one-shot transient per in-flight job; the game stays NULL-blob and re-enters the tier-4 lottery. No data loss, self-healing — no code change warranted.
- **Old atomic workers** enumerate blob nodes themselves and keep submitting odd tokens; the atomic path's structural token validation (parse + in-range) accepts them and assembly discards them (storage+compute saving on the atomic path needs the optional lazy worker rollout — out of scope per seed item 5).
- The accepted odd-firing degradation means slim-blob DISCOVERED_ATTACK-depth-1-style motifs that were already winning (>800 cp pre-flaw) or single-solver-move lose their forced-mate exemption and get suppressed; fat blobs keep the old behavior exactly.

## Known Stubs

None.

## Threat Flags

None — no new endpoints, auth paths, file access, or schema changes (token validation surfaces unchanged).

## Self-Check: PASSED

- All 5 commits present on `main` (3f68131b, e9cc6660, 64129c1d, 49a57cc1, d8b81a14).
- All modified files exist; working tree clean after final commit.
- Full backend suite green; ty + ruff clean.
