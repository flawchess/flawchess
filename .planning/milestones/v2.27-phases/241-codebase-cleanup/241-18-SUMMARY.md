---
phase: 241-codebase-cleanup
plan: 18
subsystem: backend-services
tags: [cleanup, comments, endgame, zones, benchmark-citations]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "cleanup.py codemod/decision"
provides:
  - "endgame_service.py, endgame_zones.py, endgame_ranked_service.py free of planning tags, with ledgers/241-18.txt"
affects: [241-54, 241-67, 241-70]

actuals:
  tokens: 42000
  tasks: 2
  commits: 2
plan_head_before: fae6dc0d39bb4e4b43029724116c1bbe1171383b
plan_head_after: 3adf5c2282512d31dc85312b3bf529f1e03f2bf1

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-18.txt
  modified:
    - app/services/endgame_service.py
    - app/services/endgame_zones.py
    - app/services/endgame_ranked_service.py

key-decisions:
  - "Dated benchmark citations (reports/benchmarks-YYYY-MM-DD.md, which no longer exist in reports/benchmark/) became '(YYYY-MM-DD benchmark)' provenance; only the five sections that still exist in benchmarks-latest.md (3.1.5, 3.4.2, 3.3.1, 3.3.3, 3.4.1, 3.2.1) keep a path, with the reports/benchmark/ prefix"
  - "INV-L731 was extended to the two sibling narrations of the same shape in PER_CLASS_GAUGE_ZONES (queen 'Lower edge tightened', minor_piece 'drifts -3.3pp from old midpoint'), since they cite 'diff item D/F' of a report that no longer exists"
  - "Cited-but-gone identifiers were fixed or dropped rather than carried: SCORE_GAP_PARITY_NEUTRAL_* (now ZONE_REGISTRY['score_gap_parity']), _SECTION_LAYOUT (no definition left), SCORE_GAP_NEUTRAL_MIN/MAX in EndgamePerformanceSection.tsx, the notable_endgame_elo_divergence flag"

requirements-completed: [D-01, D-04, D-10, D-11, D-12, D-13, D-15]

duration: ~75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 18: Endgame Services Comment Cleanup Summary

**All planning tags are gone from the three endgame services, 27 INVENTORY rows are applied against re-verified code, zone bands and the generated frontend file are unchanged.**

## Accomplishments

- First scan of scopes/241-18.txt: 213 blocking matches in 3 files. Final `scan --gate`: 0.
- Task 1 (endgame_service.py): codemod rewrote 53 comment/docstring lines, 56 more were hand-edited (exact-string batch, 56 replacements, plus 4 follow-ups). 12 rows applied.
- Task 2 (endgame_zones.py, endgame_ranked_service.py): codemod rewrote 61 lines, 72 hand edits in zones and 9 in ranked (D-14 verdict-gate docstrings now say "verdict gate"). 15 rows applied plus the INV-L653 secondary clause in endgame_service.py (kept as a `#` comment line in the ledger because the ledger parser rejects non-standard lines).
- Unreferenced code stays: `NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD` (no reader, INVENTORY 7.1 #17) lost only its stale flag comment; `EVAL_CLIP_MAX_CP` and `EVAL_OUTLIER_TRIM_CP` remain two constants (D-04).
- The algorithm step labels `Phase 1/2/3` in `compute_clock_diff_timeline` are not tags and stay.

## Task Commits

1. Task 1: `61a307d8f` `chore(comments): app/services/endgame_service`
2. Task 2: `3adf5c228` `chore(comments): app/services (endgame_zones, endgame_ranked_service)`

`commits: 2` is measured with `git rev-list --count fae6dc0d39..HEAD` before this SUMMARY commit.

## Commands and exit codes (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-18.txt` | exit 0, 3 files, 0 matches |
| `cleanup.py diff --scope scopes/241-18.txt` | exit 0, 3 changed, no residue |
| `cleanup.py ledger --scope scopes/241-18.txt --ledger ledgers/241-18.txt` | exit 0 |
| `scripts/gen_endgame_zones_ts.py --check` | OK, `frontend/src/generated/endgameZones.ts` up to date (`git diff` over frontend/src/generated since base: 0 lines) |
| `ruff check app/services`, `ruff format --check app/services` | clean |
| `ty check app/ tests/ scripts/` | All checks passed (baseline also clean) |
| source-scan tests, python half (run serially, no `-n`) | 95 passed + 5 passed |
| source-scan tests, frontend half | 9 files, 131 tests passed |
| `pytest tests/test_endgame_service.py tests/services/test_endgame_zones.py` | 187 passed |

Mutation check (not vacuous): `TREND_MIN_WEEKLY_POINTS: int = 20` changed to `21` made `cleanup.py diff --scope scopes/241-18.txt` exit 1 (`endgame_zones.py:166: - 20 / + 21`); restored, exit 0.

## Ledger (ledgers/241-18.txt)

27 rows, all APPLIED: L636, L646, L647, L648, L649, L650, L651, L652, L653 (+ secondary clause as comment), L667, L690-L699, L712, L726-L731. Re-verification outcomes worth knowing:

- L691: `_aggregate_endgame_stats` gaps_by_bucket is not consumed (get_endgame_stats binds it to `_gaps_by_bucket`); `_compute_score_gap_material` does not exist.
- L694: `get_endgame_elo_timeline` does not exist; endgame_ranked_service is the only caller of `build_endgame_elo_combos`.
- L696: `NEUTRAL_TIMEOUT_THRESHOLD` is not in the generated endgameZones.ts, so no codegen claim was added (L695's `NEUTRAL_PCT_THRESHOLD` is, and is used by EndgameClockDiffOverTimeChart).
- L699: INVENTORY said the §3.4.4 citation is gone; it also named §3.2.2 as a live match for the Section 2 bands, but per the row the path was dropped and only the 2026-05-15 date kept.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags**
- endgame_service.py: "UAT 2026-05-17" Sunday-of-week comment became the rule "Don't label the point with the Sunday of the week: that shifts the two charts against each other by 6 days"; `_build_category_stats` docstring "same schema defaults the per-TC breakdown always produced pre-split" became present tense; "locked decision 4" dropped; `_aggregate_endgame_stats` "Per D-02: multi-class per game" became "so a game can count toward several classes"; `_endgame_elo_logistic` docstring's "Supersedes the earlier Phase 87.6 PR-direct mapping ... UAT showed" became a "Don't derive the sides from a per-side FIDE Performance Rating" rule.
- endgame_zones.py: the `_SECTION_LAYOUT` mention (no definition exists) and a memory-file reference (`feedback_zone_band_judgement.md`) were reworded; "retired in favour of" subsection narration became "is not emitted".
- The three `.planning/notes/...` pointers: two tombstone ones were deleted with their blocks; the `endgame-elo-logistic-anchored.md` pointer in `_endgame_elo_logistic` stays (it is a path, not a tag).

**2. [Environment] Fresh worktree prep**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only).
- The python half of `source_scan_tests.sh` was run serially (its pytest command without `-n 4`) because sibling executors share the dev Postgres. Environmental, not a plan failure.

**3. [Plan note] INV-L653 secondary line is a comment**
- The ledger parser (`LEDGER_LINE_RE`) rejects `INV-L653 (secondary endgame_service.py): STATUS`; it is written as `# INV-L653 (secondary endgame_service.py): APPLIED ...`. Same treatment as 241-04.

**Total deviations:** 3 notes, no code, constant, zone value or codegen output touched.

## Seed candidates (not created)

- `NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD` has no reader (the cross-section flag it described does not exist).
- `assign_per_class_zone` / `per_class_zone_spec` have no caller anywhere except endgame_zones.py itself.
- `get_endgame_stats` receives `gaps_by_bucket` from `_aggregate_endgame_stats` and discards it.
- A pair of dated reports the file used to cite (`reports/benchmarks-2026-05-01.md` etc.) are gone, so the calibration provenance is now date-only.

## Known Stubs

None.

## Threat Flags

None. Comments and docstrings only; token diff against PHASE_BASE is empty (T-241-33 mitigated by `cleanup.py diff` and the codegen `--check`).

## Self-Check: PASSED

Files verified present: ledgers/241-18.txt and the three service files. Commits `61a307d8f` and `3adf5c228` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
