---
id: SEED-044
status: dormant
planted: 2026-06-13
planted_during: v1.26 Full-Game Eval Pipeline (Phase 117)
trigger_when: before next deploy / first flaw-pipeline or eval-pipeline phase — HIGH priority bug, ships wrong flaw stats for all chess.com users
scope: medium
severity: high
---

# SEED-044: Flaw pipeline off-by-one — engine-drain `eval_cp` stored pre-move, classifier assumes post-move (also breaks best_move + flaw PV)

## Why This Matters

Flaw stats are **wrong for every chess.com (engine-evaluated) game** — the majority of the dataset. Not merely sparse: engine-game flaws are missing or misattributed (a single real blunder can surface as a spurious adjacent pair, or as nothing). Lichess `%eval` games are correct. This is a live bug in `main` (introduced when the Phase 116/117 engine drain met the Phase 108/113 flaw classifier, which predates it). User-facing impact: Flaw-Stats panel, opponent comparison, and any flaw-derived metric are wrong for chess.com users.

## Root Cause (CONFIRMED)

`eval_cp` carries **two conventions** in the same column, and the flaw classifier assumes only one:

- `full_hash[k]` = position **before** move k (pre-push) — all sources.
- **Engine-drain rows** (`lichess_evals_at IS NULL`, all chess.com): `_collect_full_ply_targets` (`app/services/eval_drain.py:151-167`) snapshots `board.copy()` **before** `board.push(node.move)`, so `eval_cp[k]` = eval of the pre-push position = **eval BEFORE move k**. Position-keyed to `full_hash` on purpose, for cross-game dedup transplant (`eval_drain.py:183-188`).
- **Lichess `%eval` rows**: `eval_cp[k]` = eval **AFTER** move k (post-move) (`app/services/zobrist.py:182`).
- **Flaw classifier** `_run_all_moves_pass` / `classify_game_flaws` (`app/services/flaws_service.py:304`, ~316-327) assumes **post-move for all rows**. Correct for lichess, **off-by-one for engine rows**.
- **Conventions are per-GAME, not per-row**: for `is_analyzed` (lichess) games the drain *preserves* existing lichess evals and only writes `best_move` (`eval_drain.py:306-314`). So lichess games are 100% post-move and engine games are 100% pre-move — a read-side fix can key on `lichess_evals_at` per game, no per-row tagging needed.

## Proof (prod, reproducible)

`/tmp/shift_test.py` re-runs `_run_all_moves_pass` with evals shifted +1 ply:

| Game | Source | AS-IS (current) | SHIFTED +1 |
|------|--------|-----------------|------------|
| 1420780 | chess.com (engine), user 99 | **0** flaws | **12** mistakes/blunders ✓ |
| 1073118 | chess.com (engine) | 2 (off-by-one artifacts) | **10** ✓ |
| 640092  | lichess `%eval` | **3** coherent ✓ | 1 (breaks) |

- 1420780: SHIFTED ply14 = `h3`, the move that allowed `Bxf2+` (`1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.b3 Bc5 5.Bb2 d6 6.Ng5 O-O 7.O-O Ng4 8.h3?? Bxf2+`). The position after `9.Kh1` (FEN `r1bq1rk1/ppp2ppp/2np4/4p1N1/2B1P1n1/1P5P/PBPP1bP1/RN1Q1R1K b - - 1 9`) is stored as `+271` but black is winning (`Rxf2 Nxf2+` forks K+Q). That "wrong" value is the **pre-move eval of the next ply** — evidence of the shift, not a bad eval.
- 640092 confirms lichess is post-move and must **not** be shifted.

**Use these three games as regression fixtures.**

## Blast Radius — 3 entangled per-ply dimensions

The same convention ambiguity affects all per-ply outputs:

1. **`eval_cp` / `eval_mate`** — flaw detection (confirmed broken for engine games).
2. **`best_move`** — for engine games it's the best move *from* the pre-push position (the alternative to the move played at ply k); position-keyed like the engine eval. The flaw "you played X, engine preferred Y" display must align to whatever convention the fix lands on.
3. **Flaw PV (`pv_string`)** — written at `flaw_ply + 1` (D-117-02 / D-117-13) where `flaw_ply` comes from the **currently-buggy** classifier. The off-by-one likely also explains the open **~32% flaw-PV coverage** TODO (git `4b40960e`, related to [[SEED-043]] lichess best_move/PV backfill). Re-verify PV coverage after the fix.

## Two Fix Strategies (decide in the processing session)

**A. Read-side, per-source alignment (keep evals, NO re-eval) — recommended:**
- In the classifier, "eval after move N" = `eval_cp[N+1]` for engine-sourced games, `eval_cp[N]` for lichess (key on `lichess_evals_at`). Per-game flag suffices (conventions not mixed within a game).
- Align `best_move` and PV ply-selection the same way.
- Then re-run `scripts/backfill_flaws.py --db prod --full-evald-only` (flag added in commit `376cb169`) to re-materialize all engine-game flaws from the existing (correct) evals.
- Pros: cheap, no ~4-day re-eval, evals are already correct. Cons: threads source-awareness through classifier + best_move + PV; engine/lichess divergence to maintain; terminal-move edge (engine game's last move has no `N+1` eval → last-move flaw unassessable; acceptable).

**B. Wipe + canonicalize + re-eval (user's initial lean; "ok to lose 24h of evals"):**
- NULL `eval_cp`/`eval_mate` (+ `best_move` + flaw PV) for `full_evals_completed_at IS NOT NULL` engine games, drop their `game_flaws`, change the drain to write ONE canonical convention, fix dedup + classifier to match, re-eval (~4 days at 5.83 pos/s over ~33.7k games).
- Pros: single consistent convention, no read-side shims. Cons: ~4-day Stockfish re-run; **also must fix dedup position-keying and reconcile lichess data**; re-eval ALONE fixes nothing unless the write/classifier convention also changes.

**Recommendation (Claude, low confidence — defer to session):** Strategy A. The evals and `best_move` are correct and position-keyed; the only true bug is the classifier's convention assumption. Canonical convention to standardize on = **position-keyed** (matches `full_hash`, supports dedup); lichess is the outlier, handled with a per-game read shim rather than a migration. User flagged the multi-dimension shift (eval + best_move + PV) "could get messy" — weigh A's shim complexity against B's re-eval cost in the session.

## Breadcrumbs

- `app/services/eval_drain.py:151-167` — `_collect_full_ply_targets` (pre-push board snapshot = root of the engine convention)
- `app/services/eval_drain.py:183-188` — comment documenting the two conventions (lichess post-move vs engine pre-push)
- `app/services/eval_drain.py:306-314` — `_apply_full_eval_results` preserves lichess evals (→ conventions are per-game, not per-row)
- `app/services/flaws_service.py:304, 316-327` — classifier's post-move assumption (`_run_all_moves_pass`)
- `app/services/zobrist.py:182` — lichess `%eval` post-move storage
- `scripts/backfill_flaws.py` — re-materialization tool (`--full-evald-only` flag, commit `376cb169`)
- Repro: `/tmp/shift_test.py`, `/tmp/diag2.py` (may be cleaned; logic is in this seed)
- Fixtures (prod): games 1420780, 1073118 (chess.com engine), 640092 (lichess)
- Related: [[SEED-043]] lichess best_move/PV backfill; git TODO `4b40960e` (~32% flaw-PV coverage)

## Context / Dead Ends (save the next session time)

- The first hypothesis this session — "bad/shallow eval data, needs re-eval" — was **WRONG**. The evals are correct Stockfish 1M-node values; the incoherent-looking eval line is the pre-move convention read as post-move. **Do not re-investigate eval quality or re-eval on quality grounds.**
- A flaw backfill was already run on prod this session (33,742 games, 221k rows) on that wrong hypothesis — harmless/idempotent but it re-applied the **same** misalignment. Current prod `game_flaws` for engine games is still wrong; re-materialize **after** the code fix.
- Discovery context: investigating user 99 (prod) — ~9,289 chess.com games full-eval'd but flaw-less; today's drain ran 90%+ flaw-less at 11:00–14:00 UTC (the per-hour rate variation is platform/game mix, not a partial fix).

## Notes

Captured mid-investigation for processing in a fresh session. High priority: this ships wrong flaw stats to all chess.com users right now. Sits in milestone v1.26 (Full-Game Eval Pipeline) scope.
