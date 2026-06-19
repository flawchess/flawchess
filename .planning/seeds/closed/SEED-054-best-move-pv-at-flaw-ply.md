---
id: SEED-054
status: implemented
implemented_by: 260618-rmk (drain fix Parts 1+2 + scripts/backfill_best_move_pv.py); prod backfill run still pending (manual, post-deploy)
planted: 2026-06-18
planted_during: v1.28 Tactic Tagging
trigger_when: ready now — implement next session via /gsd-quick (drain fix parts 1+2), then run the local in-place prod backfill once the fix is deployed
scope: small
---

# SEED-054: Store engine `best_move` + `pv` at `flaw_ply` (the better alternative), not only at `flaw_ply + 1`

## Why This Matters

The "best move" blue arrow (added 260618-oqw, commits `a71783f9` / `91a87a3a`) is meant
to show **what the player should have played instead of a blunder** — the engine's best
move *from the pre-blunder decision position* (`game_positions[flaw_ply].best_move`,
read by `library_repository.py:469` for the Flaw card and at `activePly` for the Library
Game card).

For **lichess-eval games** that arrow is **NULL on essentially every flaw**, so the arrow
silently doesn't render (the 260618-oqw "Null for lichess-eval-only games" gate). The only
engine data we capture for a lichess blunder is at `flaw_ply + 1` = **the opponent's best
reply to the blunder**, which is the wrong move to show ("the response, not the
alternative").

Verified live on dev, lichess game 681473 (`lichess_evals_at` set):

| flaw_ply | severity | `best_move[flaw_ply]` (want) | `best_move[flaw_ply+1]` (have) |
|---|---|---|---|
| 27 | inaccuracy | **NULL** | g3h5 |
| 28 | mistake | g3h5 *(coincidence: ply 27 was also a flaw)* | d6e5 |
| 55 | inaccuracy | **NULL** | b2b4 |
| 59 | mistake | **NULL** | a4b5 |

`chess.com` (pure-engine) games are **unaffected for `best_move`**: the engine runs on
every ply there, so `best_move[flaw_ply]` already exists and the arrow already works. The
gap is lichess-specific for `best_move`. `pv` at `flaw_ply` is missing on **both** platforms
(pv is only ever written at `flaw_ply + 1`).

## Root Cause (measured, precise)

Storage convention (SEED-044): row `k` holds the **post-move** eval (`eval_cp[k]` = eval of
the position *after* move `k`) but the **decision-ply** best move (`best_move[k]` = best move
*from* the position move `k` was chosen from). `pv` is written only at `flaw_ply + 1`
(D-117-02, the refutation line consumed by the SEED-039 tactic-motif classifier).

For lichess-eval games, `_full_drain_tick` (`app/services/eval_drain.py:1700-1716`) filters
the engine targets down to `_flaw_adjacent_plies(...)` — which returns **`{flaw_ply + 1}`
only** (`eval_drain.py:792-829`, `return {flaw["ply"] + 1 for flaw in flaw_result}`). The
engine evaluates the **post-blunder** board (for the refutation PV) but never the
**pre-blunder decision** board. Hence:

- `best_move[flaw_ply]` (the better alternative) → never computed → **NULL**
- `best_move[flaw_ply + 1]` (opponent's reply) → computed → stored

## The Fix — two small drain changes

`evaluate_nodes_with_pv(board)` returns `(eval_cp, eval_mate, best_move, pv)` from a single
1M-node search, so capturing the pre-blunder best move costs **one extra engine call per
flaw** (flaws are ~5-15% of plies → small bump, and only on the cheapest game class).

**Part 1 — engine target (lichess).** In `_flaw_adjacent_plies` (`eval_drain.py:792`),
return **`{flaw_ply, flaw_ply + 1}`** instead of `{flaw_ply + 1}`. The caller already
exempts this set from the lichess eval-preservation filter and from opening dedup
(`eval_drain.py:1700-1716, 1730-1737`), so adding `flaw_ply` makes the engine also evaluate
the pre-blunder board → captures `best_move[flaw_ply]` + a pv_string for it. The lichess
`%eval` at `flaw_ply` is still preserved (the `is_lichess_eval_game` write branch in
`_apply_full_eval_results` `eval_drain.py:555-559` writes best_move only, never the eval).
Update the function name/docstring (it's no longer strictly "adjacent").

**Part 2 — pv write (both platforms).** In `_classify_and_fill_oracle`
(`eval_drain.py:751-761`), the pv-write loop collects `(flaw_ply + 1, pv_string)` pairs.
**Also collect `(flaw_ply, pv_string)`** from `engine_result_map[flaw_ply]` when present, so
the ideal-continuation line is stored at the decision ply too. Near-free for chess.com (the
engine already ran at `flaw_ply`); covered by Part 1 for lichess.
- Edge case: chess.com flaws in the opening region (`ply <= _DEDUP_MAX_PLY = 20`) can be
  dedup-transplanted, and the dedup tuple carries `best_move` but **no** pv_string — so
  `pv[flaw_ply]` will be NULL there. Acceptable (opening flaws are rare, pv is display-only).
  Don't add chess.com flaw-ply dedup exclusion unless a renderer needs it.

**Refactor note:** factor the "evaluate a flaw_ply board → write `best_move` + `pv` at
`flaw_ply`" step so the drain and the backfill script (below) share it and the keying stays
identical by construction.

**Note on Part 2 value:** `best_move[flaw_ply]` (Part 1) is what the existing arrow needs.
`pv[flaw_ply]` (Part 2) is the *ideal continuation line* — **nothing renders it today**. The
user asked for both; it's cheap given Part 1's search, but flag that it's latent until a
frontend surface consumes it.

## The Backfill — local machine, prod DB, in-place (decided)

Run on **Adrian's machine targeting prod** (`--db prod` via `bin/prod_db_tunnel.sh` →
localhost:15432), NOT through the eval workers. Decisive reason: every claim path gates on
`full_evals_completed_at IS NULL` (`eval_queue_service.py` tier-3 derived ~335/365, residual
fallback ~278). Driving the backfill through the workers would require clearing
`full_evals_completed_at`, which drops those games out of the Library/stats analyzed-gate
(260617-pu4) mid-run — a visible stats regression. A dedicated script fills the columns
**in place** and never touches the completion markers.

Design (mirror `scripts/backfill_eval.py` / `resweep_holed_games.py` plumbing):

- **Lichess-only selection:** `games.lichess_evals_at IS NOT NULL`, joined to `game_flaws`.
- **Idempotent / resumable (essential):** only process flaw positions where `best_move IS NULL`
  (and `pv IS NULL`). A dropped SSH tunnel or Ctrl-C → re-run continues. This also lets the
  script naturally cover **both** `{flaw_ply, flaw_ply + 1}` and **both cohorts**: it subsumes
  SEED-043's lichess slice (never-reprocessed games, NULL at both plies) AND this keying gap
  (already-reprocessed games, NULL at `flaw_ply` only) in one pass.
- **Engine on the local machine** → zero prod compute impact. Use a **larger** local pool
  (`STOCKFISH_POOL_SIZE` = local core count); no prod 4g-container memory constraint applies.
- **Batch DB writes (~100 games)** over the tunnel to keep it responsive and bound work lost
  on disconnect. Reuse the shared write helper from the refactor above.
- **Preserve the lichess `%eval`** at every flaw ply (write best_move/pv only, never overwrite
  `eval_cp` — same `is_lichess_eval_game` discipline as the drain).
- **Eval non-determinism is acceptable** ([[project_eval_nondeterminism]]): best_move/pv
  computed on Adrian's machine may differ occasionally from a prod-side search; these are
  display aids, not aggregated stats. Within-game mixing with prod-computed `flaw_ply+1`
  values is fine (independent positions).

**Size it first** (tunnel up). Rough sizing query:

```sql
SELECT COUNT(*) AS flaw_positions_needing_best_move
FROM game_flaws gf
JOIN games g ON g.id = gf.game_id
JOIN game_positions gp ON gp.game_id = gf.game_id AND gp.ply = gf.ply
WHERE g.lichess_evals_at IS NOT NULL
  AND gp.best_move IS NULL;
```

At ~1M nodes/position and ~6 pos/s, runtime scales with that count (× ~2 if also doing
`flaw_ply + 1` for the SEED-043 cohort). "No hurry" — a multi-hour/day local run is fine
given the idempotent restart.

## Relationship to SEED-043

[[SEED-043-lichess-best-move-pv-backfill]] covers lichess games missing best_move/pv
**entirely** (`full_pv_completed_at IS NULL`, ~16.8k pre-117 games) and leaned toward a
worker re-enqueue (option a) or demand-driven (option b). This seed's **local in-place
script is strictly better for the lichess cohort**: no marker reset, no stats drop, and it
also fixes the `flaw_ply` keying gap that SEED-043's re-enqueue would only incidentally
cover. If SEED-054's backfill ships, **close SEED-043's lichess option (a) as superseded**.

## Deployment — server-side only, no worker change

The fix is **purely server-side**; the remote eval worker needs **no `git pull` / restart**:

- The remote worker never processes lichess games. `lease_eval_game`
  (`app/routers/eval_remote.py:400-409`) releases any `is_lichess_eval_game` claim and
  returns 204 ("D-4 / v1 scope: lichess PV-backfill deferred"), handing it to the in-process
  drain. So the whole bug lives in `_full_drain_tick` (backend lifespan), and `_flaw_adjacent_plies`
  (Part 1) is only ever called there.
- The worker is a dumb FEN→eval node (`_eval_positions`, `scripts/remote_eval_worker.py:96`)
  that already returns `(eval_cp, eval_mate, best_move, pv)` unchanged — the server owns
  ply-selection and storage. Part 2's chess.com `pv[flaw_ply]` works on remote submit too
  because remote chess.com leases already evaluate every ply (`engine_result_map[flaw_ply]`
  present).
- No lease/submit schema change (one extra ply selected, one extra pv write) → a stale worker
  stays compatible.

Deploy: normal `bin/deploy.sh` (backend). The backfill runs from Adrian's machine, independent
of worker state.

## Verification

- New lichess game drained post-fix: `best_move IS NOT NULL` at flaw plies (not just
  flaw+1); `pv` present at both flaw_ply and flaw_ply+1.
- Flaw card + Library Game card render the blue better-alternative arrow on a lichess game.
- Backfill: re-run is a no-op (idempotent NULL filter); spot-check a backfilled lichess game
  matches the live-drain shape; lichess `%eval` (`eval_cp`) unchanged on flaw plies.
- Gates: ruff/ty, `pytest -n auto`, frontend lint+test (no frontend change needed for Part 1
  — the arrow already reads `best_move[flaw_ply]`; it just starts being non-NULL).

## Breadcrumbs

- `app/services/eval_drain.py:792` — `_flaw_adjacent_plies` (Part 1).
- `app/services/eval_drain.py:751-761` — pv-write loop in `_classify_and_fill_oracle` (Part 2).
- `app/services/eval_drain.py:1700-1716, 1730-1737` — lichess target filter + dedup exclusion.
- `app/services/eval_drain.py:401,439,488` — `_batch_update_best_move_rows` / `_batch_update_eval_rows` / `_apply_full_eval_results` (write helpers to reuse).
- `app/services/engine.py:246` — `evaluate_nodes_with_pv` (eval+best_move+pv in one search).
- `app/repositories/library_repository.py:469` — Flaw card reads `best_move[flaw_ply]`.
- `frontend/src/components/results/LibraryGameCard.tsx` — Library card reads `best_move` at `activePly`.
- `scripts/backfill_eval.py`, `scripts/resweep_holed_games.py`, `scripts/backfill_full_evals.py` — prod-targeting script plumbing patterns (`--db prod` + tunnel).
- [[SEED-043-lichess-best-move-pv-backfill]] — entire-coverage cohort; superseded for lichess by this seed's backfill.
- [[SEED-039-tactic-family-cause-of-error-flaw-tags]] — consumes `pv[flaw_ply + 1]` (unchanged).

## Notes

Diagnosed 2026-06-18 in a `/gsd-explore` session off lichess game 681473. Confirmed: for
lichess games the engine only runs at `flaw_ply + 1`; `best_move[flaw_ply]` is NULL on all
flaws except where the prior ply was also a flaw (coincidental engine run). User decided:
implement Parts 1+2, then backfill via a local-machine, prod-targeting, in-place,
idempotent, lichess-only script. Scope is small (one predicate change + one extra pv pair +
a ~100-line script reusing existing helpers).
