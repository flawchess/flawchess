---
phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti
plan: 03
subsystem: tactic-tagger
tags: [retag, sc4-parity, castling, en-passant, tag-delta-report, offline-backfill]

requires:
  - phase: 221-01
    provides: the real-game gate scoring harness + REALGAME_REAL_SHARE_FLOOR (referenced
      but not touched by this plan)
provides:
  - scripts/retag_flaws.py::_load_fen_maps_for_page — the ONE sanctioned full-FEN source
    (_recompute_fen_map) wired into the offline re-tagger, replacing the synthetic
    single-entry, placement-only fen_map
  - scripts/retag_flaws.py::_worker_recompute now fills positions[ply-1] from work.prv,
    matching the live drain's ply-indexed positions list
  - A four-bucket (removed/survived/motif-shifted/depth-shifted) per-motif tag-delta
    report, written on both --dry-run and a real writing run
  - TestRetagLiveClassifyParity — a permanent SC4 no-drift regression guard (castling +
    en-passant fixtures)
affects: [221-04, 221-06, 221-07]

actuals:
  tokens: 15485
  tasks: 3
  commits: 3
  plan_head_before: 2aa9361464ce7a45578586e56c5a2450b0792b29

tech-stack:
  added: []
  patterns:
    - "offline retag reads full-FEN via the SAME _recompute_fen_map the live drain uses,
      one query per page for the page's distinct games — never re-implement PGN replay"
    - "one if/elif chain per orientation classifies a report row into exactly one of
      four buckets, making 'one bucket per row' structural rather than convention"
    - "prove a drift-guard test has teeth by TEMPORARILY reverting the fix in the
      running tree, confirming the new test goes RED, then reverting the revert —
      never accept a parity test on inspection alone"

key-files:
  created: []
  modified:
    - scripts/retag_flaws.py
    - tests/scripts/test_retag_flaws.py

key-decisions:
  - "fen_map is loaded per-page (one query for all distinct game_ids in the page,
    joined against games.pgn) and sliced per-flaw to only {ply-1, ply, ply+1} before
    crossing into _FlawWork — keeps the IPC payload to three short FEN strings per flaw
    instead of a full per-game map, per the dataclass's own documented property."
  - "game_flaws.fen (piece-placement-only) is retained on _FlawWork for report/context
    use only; it no longer feeds fen_map construction anywhere."
  - "Chose NOT to add a fourth counter tuple parameter set piecemeal — motif_counters is
    passed as one 8-tuple through the new _process_page helper, since all 8 flow
    unchanged into _accumulate_motif_counts (an accumulator group, not unrelated state
    bundled to dodge a long signature)."
  - "Refactored run_backfill's per-page body into _process_page (Rule 1/CLAUDE.md
    'refactor bloated code on sight'): the function was ALREADY at nesting depth 5 (the
    hard cap is 4) before this plan touched it; the task's own counter-plumbing changes
    landed inside that same function, so the breach was fixed as part of the edit
    rather than added to."
  - "Report Mode:/provenance line switches wording by dry_run rather than adding a
    parallel writing-report template — keeps _write_retag_report's single-template
    property, matching the file's established voice."

requirements-completed: [TAGFIX-09]

coverage:
  - id: D1
    description: "_worker_recompute receives a real per-game fen_map built by _recompute_fen_map from games.pgn, carrying FULL FENs for plies ply-1, ply and ply+1"
    requirement: TAGFIX-09
    verification:
      - kind: unit
        ref: "tests/scripts/test_retag_flaws.py#TestRetagLiveClassifyParity::test_castling_flaw_parity"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_retag_flaws.py#TestRetagLiveClassifyParity::test_en_passant_missed_parity"
        status: pass
      - kind: other
        ref: "uv run python -c \"...assert 'fen_map' in r._FlawWork.__dataclass_fields__...\" (structural, acceptance criterion)"
        status: pass
    human_judgment: false
  - id: D2
    description: "_worker_recompute fills positions[ply-1] from work.prv whenever ply >= 1"
    requirement: TAGFIX-09
    verification:
      - kind: unit
        ref: "tests/scripts/test_retag_flaws.py#TestPreFlawEvalParity (both tests, unmodified in behaviour)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The retag's 8-tuple provably equals the live classify path on a castling game and an en-passant game (SC4 no-drift), with a demonstrated fail-first proof"
    requirement: TAGFIX-09
    verification:
      - kind: unit
        ref: "tests/scripts/test_retag_flaws.py#TestRetagLiveClassifyParity (2 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "_accumulate_motif_counts maintains four bucket families per orientation (removed/survived/motif_shifted/depth_shifted); the report table has a column for each"
    requirement: TAGFIX-09
    verification:
      - kind: unit
        ref: "tests/scripts/test_retag_flaws.py#TestRetagReportShiftBuckets::test_depth_only_change_counted_as_depth_shifted"
        status: pass
      - kind: other
        ref: "uv run python scripts/retag_flaws.py --db dev --user-id 28 --limit 500 (real DISCOVERED_ATTACK depth-shift + CLEARANCE motif-shift rows observed live, see SUMMARY body)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The delta report is written on a WRITING run as well as a --dry-run run, and its Mode: line says which one produced it"
    requirement: TAGFIX-09
    verification:
      - kind: unit
        ref: "tests/scripts/test_retag_flaws.py#TestRetagReportWrittenOnEveryRun::test_write_run_also_writes_report_file"
        status: pass
    human_judgment: false
  - id: D6
    description: "The stale T-143-05 docstring paragraph no longer claims the tunnel is read-only or that --db prod writes require the prod server"
    requirement: TAGFIX-09
    verification:
      - kind: other
        ref: "uv run python -c \"...assert '220' in r.__doc__\" (acceptance criterion); before/after text recorded in this SUMMARY"
        status: pass
    human_judgment: false
  - id: D7
    description: "Per-page PGN load cost measured on dev and recorded; FLAWS_PER_BATCH left unchanged"
    requirement: TAGFIX-09
    verification:
      - kind: other
        ref: "/usr/bin/time -v uv run python scripts/retag_flaws.py --db dev --dry-run --limit 4000 (before/after, recorded in this SUMMARY)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-12
status: complete
---

# Phase 221 Plan 03: Retag Full-FEN Fix + Four-Bucket Delta Report Summary

**The offline re-tagger now replays every flaw against the same full-FEN map and ply-indexed positions the live classify path uses (fixing a silent SC4 drift on castling/en-passant flaws), and its per-motif delta report carries four buckets (removed/survived/motif-shifted/depth-shifted) written on both dry-run and writing runs.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-09-12T16:16:20Z
- **Completed:** 2026-09-12T16:35:59Z
- **Tasks:** 3 completed
- **Files modified:** 2 (`scripts/retag_flaws.py`, `tests/scripts/test_retag_flaws.py`)

## Accomplishments

- `_load_fen_maps_for_page` loads each page's distinct games' PGNs in one query and recomputes a real `{ply: full FEN}` map per game via `_recompute_fen_map` (the same sanctioned full-FEN source the live drain and `eval_remote.py`'s per-game retag already use). `_FlawWork.fen_map` is now a `dict[int, str]` slice (`ply-1`/`ply`/`ply+1`), replacing the synthetic single-entry, placement-only map built from `game_flaws.fen`.
- `_worker_recompute` fills `positions[ply - 1]` from `work.prv` whenever `ply >= 1`, closing the sparse-positions gap that silently diverged from the live drain's ply-indexed list.
- `TestRetagLiveClassifyParity` (2 new tests) proves the retag's 8-tuple equals a direct live `_classify_tactic_gated` call on a castling flaw (ALLOWED orientation, `O-O` parse needs castling rights) and an en-passant PV (MISSED orientation, the recommended line needs the en-passant target carried in the FEN string itself, since no push precedes that replay). Both tests were proven to have teeth: temporarily reverting `fen_map` to the old single-entry placement-only form made both go RED with a tuple mismatch (see below); reverting the revert brought the suite back to green.
- `_bucket_motif_change` classifies each orientation's before/after (motif, depth) pair into exactly one of four buckets via an if/elif chain (removed, survived, motif_shifted, depth_shifted) — structural, not four independent ifs. `_accumulate_motif_counts` and `_write_retag_report` both thread all four buckets per orientation; the report table gained `Motif shifted` / `Depth shifted` columns, and `Previously tagged` is now the sum of all four.
- The report is written on **every** run now — dry-run or a real write — with an accurate `Mode:` line (`dry-run (no writes to DB)` vs `write (N rows changed)`) and a provenance line naming the command that actually produced it.
- Fixed the stale `T-143-05` module-docstring paragraph (see before/after below), recording the Phase-220 precedent that writes over `bin/prod_db_tunnel.sh` from the local box are proven at multi-million-row scale.
- Refactored `run_backfill`'s per-page body into `_process_page`: the function was already at nesting depth 5 (pre-existing, over the hard cap of 4) before this plan's own counter-plumbing edits landed in the same place; extracted per CLAUDE.md's "refactor bloated code on sight" rule. `scripts/check_function_size.py scripts/retag_flaws.py --fail-over-depth 4 --fail-over-loc 200` reports 0 breaches after.
- Auto-fixed a latent test-pollution bug the report-on-every-run change exposed: four pre-existing tests called `run_backfill(dry_run=False, ...)` without a `report_dir`, which was safe under the old dry-run-only gate but would now leak real report files into the committed `reports/retag/` tree. All four now inject `report_dir=tmp_path`.

## Measured cost (T-221-03-01 acceptance criterion)

`--db dev --dry-run --limit 4000`, `FLAWS_PER_BATCH = 2000` (unchanged):

| | Before (synthetic single-entry fen_map) | After (real per-page fen_map load) | Δ |
|---|---:|---:|---:|
| Wall clock | 18.23 s | 20.79 s | +2.56 s (+14%) |
| Peak RSS | 132,212 KB (~129 MB) | 146,624 KB (~143 MB) | +14,412 KB (+11%) |

Modest increase for 2 pages / 4000 flaws (one extra batched PGN-load query per page, one `_recompute_fen_map` replay per distinct game in the page). No `FLAWS_PER_BATCH` adjustment needed.

## Fail-first proof (T-221-03-02 acceptance criterion)

Temporarily reverted `_worker_recompute`'s `fen_map = work.fen_map` back to the old `fen_map = {ply: work.fen}` (single-entry, placement-only), then re-ran `TestRetagLiveClassifyParity`:

```
FAILED tests/scripts/test_retag_flaws.py::TestRetagLiveClassifyParity::test_castling_flaw_parity
E   AssertionError: SC4 violated on the castling fixture: retag (None, None, None, None, None, None, None, None) != live (2, 2, 100, 0, None, None, None, None)
E   At index 0 diff: None != 2

FAILED tests/scripts/test_retag_flaws.py::TestRetagLiveClassifyParity::test_en_passant_missed_parity
E   AssertionError: SC4 violated on the en-passant fixture: retag (None, None, None, None, None, None, None, None) != live (None, None, None, None, 27, 1, 100, 0)
E   At index 4 diff: None != 27

2 failed, 8 deselected
```

Both went RED as predicted (index 0 = `allowed_tactic_motif` for the castling fixture; index 4 = `missed_tactic_motif` for the en-passant fixture). Reverted the revert (`diff` against a pre-edit backup confirmed byte-identical restoration); full suite green again (10/10 at that point, 12/12 after task 3's two new tests).

## T-143-05 docstring correction (T-221-03-01 acceptance criterion)

**Before:**
```
    => T-143-05: --db prod writes require running on the prod server. The local SSH tunnel
       (bin/prod_db_tunnel.sh) is read-only. Pass --db prod only from the prod server.
```

**After:**
```
    => T-143-05 UPDATE (Phase 220 precedent, D-14): writes over the local SSH tunnel
       (bin/prod_db_tunnel.sh) from the local box are proven at multi-million-row scale —
       Phase 220 screened 2.57M rows and wrote ~11k cells over the tunnel in ~10h48m
       (220-06-SUMMARY.md). The tunnel is NOT read-only; --db prod writes are no longer
       restricted to running on the prod server. The round-trip-latency argument above for
       preferring the prod server when convenient still stands and is unchanged by this —
       prefer it for a full-scale run, but a local-box tunnel run is a proven fallback.
       Prod remains memory- and write-sensitive regardless of where the script runs: use
       --throttle-ms and run off-peak either way.
```

## Sample four-column report (T-221-03-03 acceptance criterion)

Real dev-DB smoke (`--db dev --user-id 28 --limit 500`, 31/500 rows changed) — note `DISCOVERED_ATTACK`'s single row landing in **Depth shifted** (D-11's depth-only change from an earlier plan, exactly the shape the new bucket exists to catch) and `CLEARANCE`'s row landing in **Motif shifted**:

```
## Allowed-orientation tag changes

| Motif | Previously tagged | Gate suppressed | Survived | Motif shifted | Depth shifted | Suppression % |
|-------|------------------|-----------------|----------|---------------|---------------|---------------|
| ATTRACTION | 3 | 0 | 3 | 0 | 0 | 0.0% |
| BACK_RANK_MATE | 1 | 0 | 1 | 0 | 0 | 0.0% |
| CAPTURING_DEFENDER | 1 | 0 | 1 | 0 | 0 | 0.0% |
| CLEARANCE | 2 | 0 | 1 | 1 | 0 | 0.0% |
| DEFLECTION | 1 | 0 | 1 | 0 | 0 | 0.0% |
| DISCOVERED_ATTACK | 1 | 0 | 0 | 0 | 1 | 0.0% |
| DISCOVERED_CHECK | 1 | 0 | 1 | 0 | 0 | 0.0% |
| FORK | 13 | 0 | 13 | 0 | 0 | 0.0% |
| HANGING_PIECE | 11 | 0 | 11 | 0 | 0 | 0.0% |
| HOOK_MATE | 2 | 0 | 2 | 0 | 0 | 0.0% |
| MATE | 13 | 0 | 13 | 0 | 0 | 0.0% |
| PIN | 7 | 0 | 7 | 0 | 0 | 0.0% |
| PROMOTION | 1 | 0 | 1 | 0 | 0 | 0.0% |
| SACRIFICE | 5 | 0 | 5 | 0 | 0 | 0.0% |
| SKEWER | 1 | 0 | 1 | 0 | 0 | 0.0% |
| TRAPPED_PIECE | 1 | 0 | 1 | 0 | 0 | 0.0% |
```

with `**Mode:** write (31 rows changed)` (not `dry-run`) — confirming both the writing-run trigger and the new columns in one real run. The report file itself was deleted after this smoke (not a plan deliverable; `git status --porcelain reports/retag/` is clean).

## Task Commits

Each task was committed atomically:

1. **T-221-03-01: Give the retag a real full-FEN map and a real `positions[ply-1]`** - `d3527bcd1` (feat)
2. **T-221-03-02: Prove the retag and the live classify path agree on a castling game and an en-passant game** - `d281bdbaf` (test)
3. **T-221-03-03: Four report buckets, written on the run that writes** - `47c8ae85f` (feat)

**Plan metadata:** committed separately per `git_commit_metadata`.

## Files Created/Modified

- `scripts/retag_flaws.py` — `_load_fen_maps_for_page` (new), `_FlawWork.fen_map` (new field), `_worker_recompute` (fills `positions[ply-1]`, uses `work.fen_map`), `_bucket_motif_change` (new), `_accumulate_motif_counts` (4 buckets), `_write_retag_report` (4 buckets + `dry_run` param), `_process_page` (new, extracted from `run_backfill` to fix a pre-existing nesting-depth breach), corrected `T-143-05` docstring paragraph
- `tests/scripts/test_retag_flaws.py` — `TestRetagLiveClassifyParity` (2 tests, castling + en-passant), `TestRetagReportWrittenOnEveryRun` (1 test), `TestRetagReportShiftBuckets` (1 test), `_seed_parity_game`/`_live_classify_tuple` shared helpers, `report_dir=tmp_path` added to 4 pre-existing call sites that were about to leak into the committed tree

## Decisions Made

- `motif_counters` threads through `_process_page` as a single 8-tuple (not 8 named parameters) — every counter flows unchanged into `_accumulate_motif_counts`, so this is an accumulator group rather than unrelated state bundled to dodge a long signature.
- The depth-shift test's fixture reuses the castling parity fixture's exact hanging-knight shape (same PGN skeleton, different filler move) rather than inventing a new tactical scenario from scratch, keeping the diff surface small and the scenario easy to verify by hand.
- Kept `_write_retag_report`'s single content template (branching only the `Mode:`/provenance strings by `dry_run`) instead of a parallel writing-run template, matching the module's established one-function-one-report-shape style.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `TestPreFlawEvalParity`'s direct `_FlawWork` construction needed the new required `fen_map` field**
- **Found during:** Task 1 (adding `fen_map` to `_FlawWork`)
- **Issue:** Adding `fen_map: dict[int, str]` as a required field broke the one existing test that constructs `_FlawWork` directly, without a default.
- **Fix:** Set `fen_map={ply: fen}` in that test, mirroring the live path's own `{ply: fen}` blobs dict exactly — preserves that test's Bug-A pre-flaw-eval parity semantics unchanged (it targets a different, orthogonal divergence than this plan's fen_map fix).
- **Files modified:** `tests/scripts/test_retag_flaws.py`
- **Verification:** `uv run pytest tests/scripts/test_retag_flaws.py -q` — all 8 pre-existing tests pass unmodified in behaviour.
- **Committed in:** `d3527bcd1` (Task 1 commit)

**2. [Rule 1 - Bug] `run_backfill`'s pre-existing nesting-depth-5 breach refactored while editing the function**
- **Found during:** Task 3 (adding counter plumbing to the same function)
- **Issue:** `scripts/check_function_size.py app/ --fail-over-depth 4` (measured against the commit before this task) already reported `run_backfill -- depth 5 > 4`, pre-dating this plan. CLAUDE.md requires refactoring bloated code encountered while editing a file, not adding to it.
- **Fix:** Extracted the per-page fetch/detect/write body (including its `try`/`except` Sentry-context handler) into a new `_process_page` helper; `run_backfill`'s own nesting drops back under the cap.
- **Files modified:** `scripts/retag_flaws.py`
- **Verification:** `uv run python scripts/check_function_size.py scripts/retag_flaws.py --fail-over-depth 4 --fail-over-loc 200` → `OK: 15 functions scanned, no breaches`; `uv run pytest tests/scripts/test_retag_flaws.py -q` and `uv run pytest -n auto -x` both green before and after.
- **Committed in:** `47c8ae85f` (Task 3 commit)

**3. [Rule 1 - Bug] Four pre-existing tests would have leaked report files into the committed tree**
- **Found during:** Task 3, after making the report write unconditionally
- **Issue:** `TestRetagIdempotency` (2 tests) and `TestRetagMarginSensitivity` (1 test, 2 `run_backfill` calls) call `run_backfill(dry_run=False, ...)` without a `report_dir`. Under the OLD dry-run-only report gate this was safe (no report was ever written on those calls); the moment the report became unconditional, the very next full-suite run wrote a real file into `reports/retag/` (caught via `git status --short reports/retag/` immediately after a manual `uv run pytest -n auto -x`, never staged or committed).
- **Fix:** Added `tmp_path: Path` fixture parameter and `report_dir=tmp_path` to all four affected `run_backfill` calls.
- **Files modified:** `tests/scripts/test_retag_flaws.py`
- **Verification:** Re-ran `uv run pytest tests/scripts/test_retag_flaws.py -q` (12 passed) and `uv run pytest -n auto -x` (4620 passed, 19 skipped); `git status --porcelain reports/retag/` clean after both.
- **Committed in:** `47c8ae85f` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking test-construction fix, 1 bloated-code refactor, 1 blocking test-pollution fix). **Impact:** all three are corrections required by this plan's own changes landing correctly; no scope creep — no unrelated code was touched.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Ready for plan 04 (missed-orientation parity / D-09) and later plans in this phase. `TestRetagLiveClassifyParity` is a permanent regression guard: any future change to `flaws_service._recompute_fen_map`, `_classify_tactic_gated`, or the retag's fen_map/positions plumbing will be caught if it reintroduces drift.
- The retag report now gives plan 07's TAGFIX-09 prod acceptance step a complete before/after instrument (removed/survived/motif-shifted/depth-shifted) on the actual writing run, not just a dry-run preview.
- Real dev-DB smoke already surfaced a live `DISCOVERED_ATTACK` depth-shift and a `CLEARANCE` motif-shift row — the report's new columns are exercised on real data, not just synthetic fixtures.
- `uv run pytest -n auto -x` (whole suite, excluding the tagger harness per `pyproject.toml`'s `addopts`) passed 4620/4620 (19 skipped) — nothing outside this plan's scope regressed. `uv run pytest tests/scripts/tagger -q` passed 3/3.

## Self-Check: PASSED

All 2 modified files found on disk with the expected changes; all 3 task commit hashes (`d3527bcd1`, `d281bdbaf`, `47c8ae85f`) found in `git log --oneline --all`.

---
*Phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti*
*Completed: 2026-09-12*
