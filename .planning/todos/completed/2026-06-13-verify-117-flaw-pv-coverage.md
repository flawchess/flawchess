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

## Resolution (2026-06-13)

**Verdict: real bug (dominant) + a negligible benign tail.** Confirmed against prod
(read-only MCP). The "~32%" was a blend of two cleanly-separated populations:

| platform | analyzed | games | flaws | pvs | coverage |
|---|---|---|---|---|---|
| chess.com | no | 435 | 25 | 24 | ~96% |
| lichess | no | 130 | 3 | 3 | 100% |
| lichess | **yes** | 15 | **126+** | **0** | **0%** |

- **Engine-evaluated path (~98%):** the single chess.com miss was an engine NULL-hole
  (eval_cp/mate both NULL at ply 89) — expected D-116-07 mark-and-continue. Benign.
- **Analyzed lichess games (the entire gap, 0%):** every flaw-adjacent position carries a
  lichess %eval but no `best_move`/`pv`. Root cause: the `is_analyzed` eval-preservation
  filter in `_full_drain_tick` (`eval_drain.py`) drops every ply with an existing %eval
  *before* the engine gather, so `flaw_ply + 1` was never engine-evaluated, and lichess
  supplies %eval but no PV. **No off-by-one and no bug in the write loop itself.**
- The opening-dedup hypothesis (#2) contributed **nothing** in the sample (0 dedup-attributed
  misses; 0 terminal flaws among the lichess set).

**Fix (D-117-13):** `_flaw_adjacent_plies()` pre-classifies the game from the stored %evals
and the filter + opening dedup exempt `{flaw_ply + 1}` so the engine evaluates exactly those
positions for PV capture, while `_apply_full_eval_results` still preserves the lichess %eval
(D-116-04). Cost bounded to ~1 engine call per flaw. Regression test
`test_flaw_pv_written_for_analyzed_lichess_game` added; full backend suite green. CHANGELOG +
117-CONTEXT D-117-13 updated. Residual documented tail: non-analyzed opening-flaw dedup, and
a write-time-filled NULL hole materializing a flaw not seen at load-time classify — both
negligible per the prod sample.

## Context / how this came up

Found while monitoring the Phase 117 prod deploy. Otherwise the deploy is healthy:
throughput ~7k games/day, oracle↔game_flaws counts reconcile, `best_move` writing
correctly (~13.7k positions), `eval_jobs` empty by design. Separately, 4,185 pre-117
chess.com games were re-enqueued (`full_evals_completed_at=NULL`) to backfill
best_move/PV/flaws; lichess backfill deferred as SEED-043.
