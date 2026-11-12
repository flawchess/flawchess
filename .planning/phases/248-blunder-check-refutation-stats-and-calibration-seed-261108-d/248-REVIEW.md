---
phase: 248-blunder-check-refutation-stats-and-calibration-seed-261108-d
reviewed: 2026-11-10T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - alembic/versions/20261109_120000_c4e9b1d7f248_phase_248_maia_refutation.py
  - app/models/game.py
  - app/models/game_flaw.py
  - app/repositories/game_flaws_repository.py
  - app/services/maia_flaw_scoring.py
  - app/services/maia_flaw_stats.py
  - scripts/backfill_maia_flaws.py
  - scripts/blunder_check/__init__.py
  - scripts/blunder_check/metrics.py
  - scripts/blunder_check/oddness.py
  - scripts/blunder_check/render.py
  - scripts/blunder_check/sample.py
  - scripts/blunder_check/spot_check.py
  - scripts/blunder_check_calibration.py
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 248: Code Review Report

**Reviewed:** 2026-11-10
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the migration, model/repository changes, the shared Maia scorer (full and refutation
modes), the refutation backfill mode, and the read-only calibration/spot-check scripts. I traced
the data path end to end: the flaw fingerprint SELECT (column order against the unpack in
`_read_flaw_inputs`), the ply+1 refutation source (`best_move` then first `pv` token), the two-stamp
protocol (`write_game_maia_scores` stamps only the chosen mode's column; `clear_maia_flaws_completed`
clears both), the selector predicates for both modes, the ES/ply conventions against
`_run_all_moves_pass` and `is_opponent_expr`, and the `FlawRow(*row[1:])` / `GameRow` positional
unpacks in `sample.py`. All of those are consistent. The migration is metadata-only and matches the
models. The scorer's guards all run before inference (one `full_policy` call per scorable blunder),
the refutation row correctly omits the eight base keys so the write leaves them untouched, and the
fingerprint is checked under the advisory lock.

I found no data-loss or correctness bug in the production scoring path that I could prove with a
concrete failure scenario. The findings are robustness and calibration-report defects: a script path
that can silently resolve cached window ids against the wrong database, inconsistent
`StaleDataError` handling in the backfill, and two places where report constants are coupled only by
comment. Nothing here blocks the already-deployed backfill.

## Warnings

### WR-01: `--from-cache` with a mismatching `--db` resolves cached game ids against the wrong database

**File:** `scripts/blunder_check_calibration.py:313-314` (consumed at `scripts/blunder_check/spot_check.py:428-430`)
**Issue:** `target = args.db or collection.meta.db_target`. When the cache was written from `--db dev`
and the user re-renders with `--from-cache <dev cache> --db prod` (or the reverse), the spot-check
opens the other database and looks up the cached `game_id` / `ply` pairs there. Game ids are plain
serial integers shared by namespace across the two databases, so the lookup does not fail: it
returns whatever unrelated game owns that id (or is silently dropped by `if w.game_id in infos`).
The resulting `spot-check-*.md` then shows moves, FENs, links and "answers" that do not belong to
the windows' blunder records, and the file is meant to be shown to a human expert as ground truth.
Nothing in the output flags the mismatch; `meta.db_name` / `meta.db_target` are not compared.
**Fix:**
```python
target = args.db or collection.meta.db_target
if args.from_cache is not None and args.db and collection.meta.db_target \
        and args.db != collection.meta.db_target:
    _log(f"--db {args.db} differs from the cache's target {collection.meta.db_target}; "
         "refusing to build a spot-check against a different database")
    want_spot_check = False
```
Also assert in `fetch_window_details` caller that the banner `current_database()` equals
`collection.meta.db_name` before resolving windows.

### WR-02: Backfill treats `StaleDataError` as a generic write failure (Sentry noise, counts toward the abort threshold)

**File:** `scripts/backfill_maia_flaws.py:316-333, 336-346, 427-431`
**Issue:** `score_game_flaws_after_apply` explicitly handles `StaleDataError` as an expected race
(game deleted between the in-lock fingerprint re-read and the bulk UPDATE; FLAWCHESS-8D) and
returns quietly. The backfill path runs the same `write_game_maia_scores` but catches only
`Exception`: a deleted game raises `StaleDataError` in the batch write, falls into
`_write_one_by_one`, is reported to Sentry via `capture_exception`, and increments
`games_write_failed`. Any batch with such a game counts as a "failed batch", and
`MAX_CONSECUTIVE_BATCH_FAILURES = 5` consecutive such batches ends the shard with
`too_many_batch_failures` (exit 4). The window is narrow, but a multi-hour prod run over thousands of
active users is exactly where concurrent account/game deletion happens, and the abort throws away the
rest of the shard's selector snapshot until someone notices and re-runs.
**Fix:** in `_write_one_by_one`, catch `StaleDataError` before the generic handler, log at INFO,
count it as `games_missing` (not `games_write_failed`), and do not capture it:
```python
except StaleDataError:
    report.games_missing += 1  # deleted mid-write: expected race, same as the live lane
except Exception:
    ...
```

### WR-03: `MAX_BLUNDER_POSITION` is coupled to `WINDOW_LENGTHS` only by a comment; a mismatch silently zeroes the fit

**File:** `scripts/blunder_check/metrics.py:38-42`, `:156-171`, `:266-271`; `scripts/blunder_check/render.py:69`; `scripts/blunder_check/sample.py:75`
**Issue:** `MAX_BLUNDER_POSITION = 5` carries the comment "matches max(WINDOW_LENGTHS)" but is an
independent literal. `hazard_position_weights` builds weights for `1..max(lengths)`, while
`FIT_POSITIONS` (render) and `PRECEDING_MOVES_KEPT` (sample, stored in the cache) are built from
`MAX_BLUNDER_POSITION`. If `WINDOW_LENGTHS` is ever extended (say to `(3, 4, 5, 6)`), position 6 gets a
hazard weight, `fit_shares` never computes a share for it (`FIT_POSITIONS` stops at 5), and
`weighted_fit_share` does `fit_by_position.get(k, 0.0)`: the position-6 weight is silently counted as
a 0% fit, deflating every "hazard-weighted fit" and supply number, with no error. The cached
`preceding` lists would also be too short for position 6.
**Fix:** derive the constant, so the two cannot drift:
```python
WINDOW_LENGTHS: tuple[int, ...] = (3, 4, 5)
MAX_BLUNDER_POSITION: int = max(WINDOW_LENGTHS)
```
and make `weighted_fit_share` raise (or `assert`) when a weighted position has no fit entry instead of
defaulting to 0.0.

## Info

### IN-01: Spot-check overwrite guard fires for a file that will not be written

**File:** `scripts/blunder_check_calibration.py:295-298`
**Issue:** The overwrite check iterates `(out_path, spot_path)` unconditionally. With
`--spot-check-per-bucket 0`, or a `--from-cache` re-render where the spot-check is skipped
(`want_spot_check` false), a leftover `spot-check-{date}.md` still makes the run exit `EXIT_EXISTS`
unless `--overwrite` is passed, even though that file is never touched. Conversely, `--overwrite`
needed only for the spot-check means the report is also overwritten.
**Fix:** only include `spot_path` in the guard when `args.spot_check_per_bucket > 0`.

### IN-02: Refutation-mode backfill reports flaws counters that are always zero

**File:** `scripts/backfill_maia_flaws.py:249-262, 372-390`
**Issue:** `_tally_stamped` only updates `flaws_scored` / `flaws_null` in full mode, but
`_progress_line` and `_finish_report` still print and compute `flaws_scored=0 (0.0 flaws/s)` for a
refutation run, and the combined `total:` line carries `flaws_scored=0 flaws_null=0`. Harmless, but a
monitor greping that line during a refutation run sees a frozen metric next to a live one.
**Fix:** print the refutation counters only when `report.mode == "refutation"` (and the flaws
counters only in full mode).

### IN-03: The "user-side blunder" predicate is implemented three separate ways

**File:** `app/services/maia_flaw_scoring.py:340-344`, `scripts/blunder_check/sample.py:596-600`, `scripts/backfill_maia_flaws.py:652-667`
**Issue:** The scorer uses `mover_is_white_at_ply(ply) == (user_color == "white")`, the sampler
repeats that inline, and the backfill status SQL uses `not_(is_opponent_expr(...))`. All three agree
today (they share `_PLY_EVEN_MOVER_WHITE`), but this is the exact shape of the "prior off-by-one bug"
the `is_opponent_expr` docstring warns about: one change to the convention (or to the severity
filter) has to be made in three places, and the report's blunder population is only guaranteed to
equal the scorer's scope by inspection.
**Fix:** expose one `is_user_flaw_ply(ply, user_color)` helper next to `mover_is_white_at_ply` in
`query_utils.py` and call it from the scorer and the sampler.

### IN-04: `sample.py` imports a constant from a script module

**File:** `scripts/blunder_check/sample.py:44`
**Issue:** `from scripts.backfill_maia_flaws import SHARD_RESIDUE_SQL` makes a read-only calibration
library import the whole backfill script (Sentry, multiprocessing, `maia_engine`, a
`sys.path.insert` side effect, and a second `DEFAULT_BATCH_GAMES` with a different value, 50 vs
500). It works, but it couples the report tooling to a script's top-level imports.
**Fix:** move `SHARD_RESIDUE_SQL` into a small shared module (for example
`app/repositories/query_utils.py` or `scripts/_sharding.py`) imported by both.

### IN-05: Good-move oddness sample includes forced single-legal-move plies

**File:** `scripts/blunder_check/oddness.py:71-94, 123-127`
**Issue:** `select_good_moves` samples every judged Good user move. A ply with exactly one legal
move is always Good (nothing can be lost) and always scores Maia probability 1.0, rank 1, while a
blunder can never occur at such a ply. These plies inflate the Good-side probability distribution and
push the reported AUC upward, overstating how much "arrow oddness" leaks the answer. The unselected
baseline shares the bias, so the drill-minus-unselected delta is mostly unaffected, but the absolute
AUC columns are. Impact is small (forced-move plies are a few percent of moves) and it is a
calibration judgement, so Info only.
**Fix:** skip targets where `len(probs) == 1` in `_score_game` (count them in `skipped`), or note the
bias in the section text.

### IN-06: Minor report hygiene (hard-coded numbers in prose, unvalidated `--date`)

**File:** `scripts/blunder_check/render.py:141,165-166`; `scripts/blunder_check_calibration.py:123-126,292`
**Issue:** `render.section_how_to_read` hard-codes `1000`, `100` and "3 to 5" in prose even though
`PERMILLE_BASE`, `PERCENT` and `WINDOW_LENGTHS` exist (the spot-check header does use
`WINDOW_LENGTHS`), so a constant change leaves stale report text. `--date` is formatted straight
into the output filename without validation, so `--date ../../x` writes outside `--out-dir`
(local owner-run CLI, so no trust boundary, but cheap to close with `datetime.strptime`).
**Fix:** reference the constants in the f-strings; validate `--date` with
`datetime.strptime(date, DATE_FORMAT)`.

---

_Reviewed: 2026-11-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
