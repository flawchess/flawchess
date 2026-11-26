---
phase: 257-facepalm-rate-library-stats
verified: 2026-11-20T14:45:00Z
status: human_needed
score: 9/9 must-haves verified
covered_files:
  - .planning/phases/257-facepalm-rate-library-stats/257-01-PLAN.md
  - .planning/phases/257-facepalm-rate-library-stats/257-01-SUMMARY.md
  - .planning/phases/257-facepalm-rate-library-stats/257-02-PLAN.md
  - .planning/phases/257-facepalm-rate-library-stats/257-02-SUMMARY.md
  - .planning/phases/257-facepalm-rate-library-stats/257-03-PLAN.md
  - .planning/phases/257-facepalm-rate-library-stats/257-03-SUMMARY.md
  - .planning/phases/257-facepalm-rate-library-stats/257-04-PLAN.md
  - .planning/phases/257-facepalm-rate-library-stats/257-04-SUMMARY.md
  - .planning/phases/257-facepalm-rate-library-stats/257-05-PLAN.md
  - .planning/phases/257-facepalm-rate-library-stats/257-05-SUMMARY.md
  - .planning/phases/257-facepalm-rate-library-stats/257-06-PLAN.md
  - .planning/phases/257-facepalm-rate-library-stats/257-06-SUMMARY.md
  - .planning/phases/257-facepalm-rate-library-stats/257-07-PLAN.md
  - .planning/phases/257-facepalm-rate-library-stats/257-07-SUMMARY.md
  - CHANGELOG.md
  - app/repositories/library_repository.py
  - app/schemas/library.py
  - app/services/blunder_check_rules.py
  - app/services/facepalm_score.py
  - app/services/library_service.py
  - frontend/src/components/analysis/FacepalmMoveChip.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
  - frontend/src/components/library/EvalChart.tsx
  - frontend/src/components/library/FacepalmBadgePopover.tsx
  - frontend/src/components/library/FacepalmChip.tsx
  - frontend/src/components/library/FacepalmExplanation.tsx
  - frontend/src/components/library/FacepalmShareChart.tsx
  - frontend/src/components/library/FlawCard.tsx
  - frontend/src/components/library/__tests__/EvalChart.test.tsx
  - frontend/src/components/library/__tests__/FacepalmBadgePopover.test.tsx
  - frontend/src/components/library/__tests__/FacepalmExplanation.test.tsx
  - frontend/src/components/library/__tests__/FacepalmShareChart.test.tsx
  - frontend/src/components/library/__tests__/FlawCard.test.tsx
  - frontend/src/components/library/stats/ContextTagCards.tsx
  - frontend/src/components/library/stats/FacepalmCard.tsx
  - frontend/src/components/library/stats/GapPopover.tsx
  - frontend/src/components/library/stats/LibraryStatsSections.tsx
  - frontend/src/components/library/stats/__tests__/FacepalmCard.test.tsx
  - frontend/src/components/library/stats/__tests__/GapBar.test.tsx
  - frontend/src/components/library/stats/__tests__/GapPopover.test.tsx
  - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
  - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
  - frontend/src/hooks/analysis/useAnalysisGemMarkers.ts
  - frontend/src/lib/__tests__/gapBar.test.ts
  - frontend/src/lib/facepalm.ts
  - frontend/src/lib/flawComparisonMeta.ts
  - frontend/src/lib/gapBar.ts
  - frontend/src/lib/theme.ts
  - frontend/src/types/library.ts
  - tests/facepalm_seed.py
  - tests/repositories/test_library_repository.py
  - tests/services/test_eval_chart_service.py
  - tests/services/test_facepalm_score.py
  - tests/services/test_facepalm_seed.py
  - tests/services/test_flaw_comparison.py
  - tests/services/test_library_service.py
  - tests/test_library_repository.py
  - tests/test_library_router.py
covered_digest: "v4:sha256:8596d7104c7cc9575366b5adb531ee8f9855b925307a7d77fbb168772220b37e"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Share-floor jumpiness on real accounts (D-03 fallback decision)"
    expected: "Owner decides: keep the pooled share with FACEPALM_SHARE_MIN_SCORED = 50, raise the floor / widen smoothing, or switch to the D-03 fallback (rolling mean of the score). Orchestrator prod probe (top 15 accounts): the 50 floor barely binds, max_step_below50 is mostly < 0.05, but max_step_at_or_above50 is often 0.08 to 0.34 (median step 0.01 to 0.03, p90 0.02 to 0.08). The plan's keep-50 rule (below50 > 0.08 while above50 < 0.06) is not met, and the large weekly steps occur above the floor, so a floor change would not fix them."
    why_human: "A threshold rule in the plan failed to decide; whether the line is acceptable is a product call on real data."
  - test: "Facepalm comparison latency on the largest prod account (D-11)"
    expected: "Plan threshold about 1 s; if above, move the three facepalm rows to their own endpoint in a follow-up so the Stats page TC switch does not wait on them. Measured by the orchestrator (EXPLAIN ANALYZE of the shipped statement, user 95, 40,218 analyzed games, about 165k blunders): 11,048 ms cold (148k buffers read), of which JIT 4,020 ms (62 functions, recurs every call). Owner decides: ship as is, split into its own endpoint, or disable JIT for the statement."
    why_human: "Threshold exceeded roughly 11x on the largest account; whether to ship, split or tune is a scope/priority call (the plan routes the split to a follow-up)."
  - test: "Opponent side of the Facepalm blunders card on prod (D-12)"
    expected: "After the release: prod user 28, Library, Stats, You vs. your opponents. The opponent column shows real non-zero rates in each time control. Dev user 28 has only 144 of 5,624 opponent blunders scored, so dev reads near zero."
    why_human: "Needs the release and prod data."
  - test: "Dev-stack visual check of the type tint on the three surfaces (D-08 to D-10)"
    expected: "Flaws card chip, analysis move-list mini-chip and eval-chart tooltip line show teal for a missed win and crimson for an allowed loss on every scored blunder, both types, and the popover names the type in words."
    why_human: "Visual; plans 03 human-check, not run."
  - test: "Dev-stack visual check of the share chart and the Facepalm blunders card (D-03, D-11, D-13)"
    expected: "Share chart sits under the Flaws Timeline with the same dates, volume bars and caption; hover shows share and the two counts; thin-TC text fallback appears; the Facepalm blunders card sits after the context-tag cards, follows the TC switch, bars are neutral (no band, no red/green), three popovers read correctly on desktop and phone width. Also see IN-02 (uneven rounded y tick labels on narrow domains) and IN-03 (two stacked empty cards when a TC has no trend)."
    why_human: "Visual; plans 04 and 06 human-checks, not run."
  - test: "Owner copy confirmation (D-05 / D-13) and WR-01 type wording"
    expected: "(a) 'The gap is too large to be chance.' and COPY_CHANCE read as statements about the gap, not as probability wording about the score; the card-text regex only bans /probab|likel/. (b) WR-01: the 'Missed win: the best move won material that was not taken.' sentence, the row hint 'passed up a material win' and the Missed wins count also cover rows with no material in either line or an unknown best line (D-02 puts them in missed_win). Measure on prod/benchmark how many scored blunders >= 0.7 are typed missed_win with missed = 0; if not negligible, soften the sentence (for example 'the move did not lose material.') or add a fallback sentence."
    why_human: "Owner copy call; the review finding is still open in 257-REVIEW-DISPOSITION.md."
---

# Phase 257: Facepalm Rate in the Library Stats Verification Report

**Phase Goal:** Add facepalm statistics to the library stats, limited to the part that needs no benchmark: the facepalm share of the player's blunders over time, a "you vs your opponents" facepalm comparison (total and per type), and the facepalm chip tinted by type (decisions in the seed "Current scope" and CONTEXT D-01..D-16).
**Verified:** 2026-11-20
**Status:** human_needed
**Re-verification:** No, initial verification

All code-level must-haves hold in the codebase. The status is `human_needed` rather than `passed` because three prod-data checks and the dev visual/copy checks are unresolved, two of them with measured results that miss the plan's own thresholds (share jumpiness, comparison latency). Nothing found is a goal failure, so there is no `gaps_found`.

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | D-01: `FACEPALM_STATS_MIN = 0.7` is its own constant, separate from the drill's `FACEPALM_SCORE_MIN = 0.5`; scores use `FACEPALM_LIBRARY_LAMBDA` | VERIFIED | `app/services/blunder_check_rules.py:60,65`; every new query binds `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` and compares `>= FACEPALM_STATS_MIN` (`fetch_facepalm_share_counts`, `fetch_facepalm_comparison`); test `test_facepalm_stats_min_is_the_high_preset_cut` |
| 2 | D-02: type rule `loss > 0 and loss >= missed` -> allowed_loss, else missed_win, NULL only for unknown loss; SQL and Python twins agree; no lambda or fitted coefficient | VERIFIED | `facepalm_type_of`, `facepalm_type`, `facepalm_type_sql`, `facepalm_type_expr` in `app/services/facepalm_score.py:640-720` read the same `_loss_sql`/`_missed_sql` and `material_loss`/`material_missed`; parity tests over the grids pass (224 backend tests run in this verification pass) |
| 3 | D-08: type is carried next to the score in every payload that carries `facepalm_score` | VERIFIED | `FlawListItem.facepalm_type`, `FlawMarker.facepalm_type` (`app/schemas/library.py`); `query_flaws` adds `facepalm_type_expr().label("facepalm_type")`; `fetch_page_facepalm_scores` returns `FacepalmChipValue(score, type)`; `_build_eval_series` sets both under the blunder gate; TS mirror in `frontend/src/types/library.ts:43,194,321` |
| 4 | D-08/D-09/D-10: all three chip surfaces tinted by type (teal missed win, crimson allowed loss) for every scored blunder, the type is named in text, `FACEPALM_CHIP*` is gone | VERIFIED (visual pending) | `FACEPALM_TYPE_STYLE` maps to `TAC_MISSED*`/`TAC_ALLOWED*`; used by `FacepalmChip`, `FacepalmMoveChip`, `FacepalmTooltipLine` (EvalChart); `FacepalmExplanation` renders `FACEPALM_TYPE_LABEL: FACEPALM_TYPE_SENTENCE`; `grep FACEPALM_CHIP frontend/src` returns nothing; chip renders only when score and type are both non-null (`FlawCard.tsx:360`, `VariationTree.tsx:132`) |
| 5 | D-03/D-04/D-07: facepalm share = facepalm / scored blunders pooled over the same rolling window (sum over sum), unscored left out, user side only, one neutral line, own chart below the Flaws Timeline | VERIFIED (behavioral) | `fetch_facepalm_share_counts` (user-scoped on both tables, `player_only_gate`, `_filtered_games_base`, fenced); `_compute_flaw_trend` sums both counts over `FLAW_TREND_WINDOW`, `_window_share` is null below the floor; `FacepalmShareChart` mounted under `FlawTrendChart` in `FlawTimeline`; orchestrator mutation check (`points.slice(1)` and `trend_window + 1` fed to the chart) failed 2 tests; `FACEPALM_SHARE_LINE` is the neutral grey |
| 6 | D-11/D-12/D-04: "Facepalm blunders" card in You vs. your opponents with total, missed wins, allowed losses, per 100 of the user's moves, paired per game, a type only against the same type | VERIFIED | `fetch_facepalm_comparison` shares `_flaw_comparison_anchor` with `fetch_flaw_comparison`; `_compute_facepalm_bullets` goes through `_paired_series`; `FlawComparisonTc.facepalm_bullets`; `FacepalmCard` mounted via `ContextTagCards trailing` inside `VsOpponentsSection` (behind the analyzed-games gate, same TC switch, no new request); no field sets missed wins against allowed losses |
| 7 | D-13: neutral bar, no verdict, no band | VERIFIED | `FacepalmBullet` `has_zone=False`, `zone_lo=zone_hi=0.0`; `GapCell.noVerdict` makes `effectiveVerdict` return null (`gapBar.ts`); `facepalmMetricCell` sets it; gapBar and GapBar tests cover it |
| 8 | D-14/D-15/D-16/D-05: labels "Facepalm blunders" / "Missed wins" / "Allowed losses", hints name the 70% cut (from `FACEPALM_HIGH_CUTOFF`), intro states the comparison only, popover says no typical range, no "Fewer is better.", no probability wording, "chance/threat blindness" absent | VERIFIED (copy confirmation pending) | `FACEPALM_GAP_META`, `FACEPALM_INTRO`, `COPY_NO_RANGE`, `GapPopover omitDirection/rangeNote`; `grep -i "chance blindness\|threat blindness"` over `frontend/src` and `CHANGELOG.md` is empty; changelog bullets carry no probability wording |
| 9 | D-06: opponent scores stay out of drill selection and the library tag filters | VERIFIED | `app/repositories/blunder_check_repository.py` and `app/repositories/query_utils.py` have no diff against the merge base with main (checked); opponent scores enter only as `COUNT ... FILTER` columns in `fetch_facepalm_comparison`; `fetch_page_facepalm_scores`, share counts and `query_flaws` keep `player_only_gate` |

**Score:** 9/9 truths verified (0 present, behavior-unverified)

### D-xx Accounting (no REQUIREMENTS.md; plans claim CONTEXT decisions)

Plans claim: 01 [D-01, D-02, D-07, D-08, D-09], 02 [D-06, D-08], 03 [D-05, D-08, D-09, D-10], 04 [D-01, D-03, D-04, D-05, D-07], 05 [D-01, D-02, D-04, D-06, D-12, D-13], 06 [D-04, D-05, D-11 to D-16], 07 [D-05, D-06, D-14]. Union D-01..D-16, all 16 covered and each traced to code above. No orphans.

### Required Artifacts / Key Links

| Artifact / link | Status | Details |
| --------------- | ------ | ------- |
| `facepalm_score.py` type twins, `blunder_check_rules.py` constant | VERIFIED | exists, substantive, wired (imported by repository and service) |
| `library_repository.py` `fetch_facepalm_share_counts`, `fetch_facepalm_comparison`, `fetch_page_facepalm_scores`, `query_flaws` type column | VERIFIED | all called from `library_service.py` (`get_flaw_stats`, `get_flaw_comparison`, card/eval series builders) |
| `FacepalmShareChart.tsx`, `FacepalmCard.tsx` | VERIFIED | mounted in `LibraryStatsSections.tsx` (`FlawTimeline`, `VsOpponentsSection`) |
| Type tint chain `FlawCard -> FacepalmChip -> FACEPALM_TYPE_STYLE`; `useAnalysisGemMarkers -> VariationTree -> FacepalmMoveChip`; `EvalChart -> FacepalmTooltipLine` | WIRED | types required together with score at each call site |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
| -------- | ---- | ------ | --------- | ------ |
| `FacepalmShareChart` | `facepalm_share`, counts | `fetch_facepalm_share_counts` over `game_flaws` via `get_flaw_stats` | Yes | FLOWING |
| `FacepalmCard` | `facepalm_bullets` | `fetch_facepalm_comparison` via `get_flaw_comparison` | Yes (dev opponent side near zero, see human item 3) | FLOWING |
| Chips | `facepalm_type` | `facepalm_type_expr()` in SQL | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Type twin parity, stats cut, comparison and share rows | `uv run pytest tests/services/test_facepalm_score.py tests/services/test_flaw_comparison.py -k "facepalm or type or stats_min" -n 4` | 224 passed | PASS |
| Card, share chart, flaw card, gap bar | `npx vitest run` on FacepalmCard, FacepalmShareChart, FlawCard, gapBar tests | 106 passed (4 files) | PASS |
| Full pre-merge gate at HEAD ea90a768b (orchestrator, not re-run) | ruff, ty, function-size, pytest 7264 passed / 19 skipped, lint, build, knip, npm test 6661 passed | green; no source change since | PASS |

### Probe Execution

SKIPPED: the phase declares no probe scripts (`scripts/*/tests/probe-*.sh`); the `temp/facepalm-257/` SQL probes are one-off prod reads handled by the orchestrator.

### Requirements Coverage

No REQUIREMENTS.md. See the D-xx accounting above: 16 of 16 decisions satisfied in code.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (all phase-modified files) | - | TBD / FIXME / XXX / TODO / HACK in added lines | none | no debt markers found |
| `app/services/library_service.py` | 1117-1122 | comment "The prod probe is still pending (plan 07)" is now stale; floor 50 also differs from CONTEXT's 20 | Warning (IN-05, open) | Misleading comment only |
| `frontend/src/lib/facepalm.ts:159-174`, `EvalChart.tsx:533`, `types/library.ts:570`, `FacepalmChip.tsx:4-5` | - | orphaned or stale doc comments | Info (IN-01, open) | None functional |
| `FacepalmShareChart.tsx:36-46,136-144` | - | share-unit y domain with whole-percent ticks can give uneven labels (IN-02, open) | Info | Cosmetic, narrow domains |
| `LibraryStatsSections.tsx:79-92` | - | two stacked empty cards when a TC has no trend (IN-03, open) | Info | Cosmetic |
| `FacepalmCard.tsx` vs `ContextTagCards.tsx`; chart ticks `fontSize: 12` | - | near-duplicate row, tick size below text-sm floor (copies FlawTrendChart) (IN-04, open) | Info | Quality debt |

### Code Review Findings (257-REVIEW.md, all six still open)

- **WR-01 (warning):** the "missed win" type is the `else` branch of D-02, so rows with no material in either line or an unknown best line are typed missed win while the copy says "the best move won material that was not taken" / "passed up a material win". The rule is owner-locked; the wording over-claims for those rows. Prod share of such rows not measured. Carried as human item 6.
- IN-01 to IN-05: see the anti-pattern table. None is a blocker; the disposition file records all as `open`.

### Human Verification Required

See the `human_verification` frontmatter: six items (share jumpiness owner call, comparison latency, post-release opponent-side read, tint visual check, share chart and card visual check, owner copy confirmation with the WR-01 wording).

### Gaps Summary

No code-level gaps: all 16 decisions and the four scope items are implemented, wired and tested, and the D-06 guard files are unchanged. Two prod measurements the plan asked for missed their thresholds and need an owner decision rather than a code fix: (1) the share line has large week-to-week steps even above the 50 floor, so a floor change would not help and the D-03 fallback (rolling mean of the score) is the alternative; (2) the shipped comparison statement takes about 11 s cold (4 s of it JIT) for the largest account against a 1 s plan threshold, which would slow the Stats page for heavy accounts because the facepalm rows ride on the existing flaw-comparison request. The plan routes the latter to a follow-up endpoint split, and it is non-blocking for the phase goal as written, but it is a user-visible performance risk for the largest accounts and should be decided before release.

---

_Verified: 2026-11-20_
_Verifier: Claude (gsd-verifier)_
