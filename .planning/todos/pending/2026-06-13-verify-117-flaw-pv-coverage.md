---
created: 2026-06-13T13:11:00.000Z
title: Verify Phase 117 flaw-PV coverage (~32% of flaws got a PV)
area: backend
files:
  - app/services/eval_drain.py (_classify_and_fill_oracle — flaw-PV write loop, ~lines 439-458)
  - app/services/engine.py (evaluate_nodes_with_pv / pv_string capture)
  - .planning/phases/117-priority-queue-flaw-integration/117-CONTEXT.md (D-117-01/02)
  - .planning/seeds/SEED-043-lichess-best-move-pv-backfill.md
---

## Problem

Prod sanity check ~55 min after the Phase 117 deploy (2026-06-13, server `f38a3fce`)
surfaced a flaw-PV coverage gap. Over the games processed under 117 so far
(`full_pv_completed_at IS NOT NULL`):

- `game_flaws` rows = **60**, oracle blunder+mistake sum = **60** (these reconcile ✓)
- `game_positions.pv` written = **19** → only **~32%** of flaws got a refutation PV

D-117-02 says: write the full PV (UCI, ~12-ply cap) at the position **after** each
flawed move (`flaw_ply + 1`) — the SEED-039 refutation line. So we'd expect roughly
one `pv` per flaw (60), not 19.

**Reproduce (prod read-only MCP, tunnel via `bin/prod_db_tunnel.sh`):**
```sql
WITH p AS (SELECT id FROM games WHERE full_pv_completed_at IS NOT NULL)
SELECT
  (SELECT count(*) FROM game_flaws gf JOIN p ON p.id=gf.game_id) AS flaws,
  (SELECT count(*) FROM game_positions gp JOIN p ON p.id=gp.game_id WHERE gp.pv IS NOT NULL) AS pvs;
```
(Numbers will be larger now — the drain keeps processing — but the ratio is the signal.)

## Solution

Investigate the flaw-PV write in `_classify_and_fill_oracle` (`eval_drain.py`, the loop
that does `pv_ply = flaw_ply + 1; engine_entry = engine_result_map.get(pv_ply); write pv`).
Determine whether the ~68% gap is **benign** or a **bug**.

Likely-benign causes (confirm magnitude, don't assume):
1. **Terminal-move flaws** — a flaw on the final move has no `flaw_ply+1` position
   evaluated (terminal excluded), so no PV to attach. Quantify how many of the 60 are last-move flaws.
2. **Opening-region dedup** — for `ply ≤ DEDUP_MAX_PLY (20)`, `_fetch_dedup_evals`
   transplants `eval_cp`/`eval_mate`/`best_move` by `full_hash` but **does NOT carry
   `pv_string`**. If `flaw_ply+1` lands on a dedup-transplanted opening ply, its
   `engine_result_map` entry has no `pv_string` → PV skipped. Check whether flaws near
   the opening boundary are losing their PV this way. (Opening flaws are rare, so this
   alone shouldn't explain 41 missing.)

Possible-bug causes to rule out:
- `engine_result_map` not populated with `pv_string` for non-flaw plies (if the impl
  only retained PV for plies it *thought* were flaw-adjacent, the `flaw_ply+1` lookup
  would miss). Verify `evaluate_nodes_with_pv` returns and the drain stores `pv_string`
  for **every** engine-evaluated ply, not a subset.
- Off-by-one in `flaw_ply+1` vs how `game_flaws.ply` / `game_positions.ply` are indexed.
- `pv_string` being dropped/None when it shouldn't be (e.g. a `None` short-circuit in
  the write loop that's too aggressive).

If a real gap is found, fix the write so every non-terminal flaw gets its `flaw_ply+1`
PV (and document the genuinely-unavoidable cases, e.g. terminal-move flaws).

## Urgency: LOW

The only consumer of flaw PVs is **SEED-039 (tactic-motif tagging)**, which is **not
built**. No live feature is affected today. This must be resolved (or confirmed benign)
**before SEED-039 ships**. Natural place to fold it in: the SEED-043 revisit, or a
pre-SEED-039 verify pass.

## Context / how this came up

Found while monitoring the Phase 117 prod deploy. Otherwise the deploy is healthy:
throughput ~7k games/day, oracle↔game_flaws counts reconcile, `best_move` writing
correctly (~13.7k positions), `eval_jobs` empty by design. Separately, 4,185 pre-117
chess.com games were re-enqueued (`full_evals_completed_at=NULL`) to backfill
best_move/PV/flaws; lichess backfill deferred as SEED-043.
