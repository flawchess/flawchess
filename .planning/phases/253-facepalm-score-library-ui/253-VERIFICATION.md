---
phase: 253-facepalm-score-library-ui
verified: 2026-11-14T17:50:00Z
status: passed
score: 19/19 must-haves verified
covered_files:
  - ".planning/phases/253-facepalm-score-library-ui/253-01-PLAN.md"
  - ".planning/phases/253-facepalm-score-library-ui/253-01-SUMMARY.md"
  - ".planning/phases/253-facepalm-score-library-ui/253-02-PLAN.md"
  - ".planning/phases/253-facepalm-score-library-ui/253-02-SUMMARY.md"
  - ".planning/phases/253-facepalm-score-library-ui/253-03-PLAN.md"
  - ".planning/phases/253-facepalm-score-library-ui/253-03-SUMMARY.md"
  - "CHANGELOG.md"
  - "app/repositories/library_repository.py"
  - "app/repositories/query_utils.py"
  - "app/routers/library.py"
  - "app/schemas/library.py"
  - "app/services/library_service.py"
  - "frontend/src/api/client.ts"
  - "frontend/src/components/analysis/FacepalmMoveChip.tsx"
  - "frontend/src/components/analysis/VariationTree.tsx"
  - "frontend/src/components/filters/FacepalmFilter.tsx"
  - "frontend/src/components/filters/FlawFilterControl.tsx"
  - "frontend/src/components/filters/PresetRangeFilter.tsx"
  - "frontend/src/components/library/EvalChart.tsx"
  - "frontend/src/components/library/FacepalmBadgePopover.tsx"
  - "frontend/src/components/library/FacepalmChip.tsx"
  - "frontend/src/components/library/FacepalmExplanation.tsx"
  - "frontend/src/components/library/FlawCard.tsx"
  - "frontend/src/components/library/SeverityBadge.tsx"
  - "frontend/src/hooks/analysis/useAnalysisGemMarkers.ts"
  - "frontend/src/hooks/useFlawFilterStore.ts"
  - "frontend/src/hooks/useLibrary.ts"
  - "frontend/src/lib/analytics.ts"
  - "frontend/src/lib/facepalm.ts"
  - "frontend/src/lib/theme.ts"
  - "frontend/src/pages/library/FlawsTab.tsx"
  - "frontend/src/pages/library/GamesTab.tsx"
  - "frontend/src/types/library.ts"
covered_digest: "v4:sha256:5a65ae979a7d7ca968dc8d68b186515280ee0f2d3aa6d48277a4e6ea14aba411"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 19/19
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Flaws-tab card look after the UAT redesign (desktop and 375 px mobile)"
    expected: "A scored blunder reads [?? glyph + Blunder] [palm Facepalm 94%]: the Facepalm chip is a neutral white pill (tag-sized, text-xs, same family as the context tags), clearly not blunder red, sitting right after the Blunder badge; the move-quality glyph in each severity badge (?? / ? / ?!) is not squashed and the badge keeps its height next to the tag pills; unscored blunders show the glyph badge and no chip; Games-card count badges (3 Blunders) are still icon-less"
    why_human: "D-20 / D-21 visual appearance (colors, icon size, spacing, wrap behavior on a narrow tags row). The component tests assert DOM, testids and text, not rendered look. This look was not covered by the earlier browser UAT, which checked the pre-redesign inside-badge design."
  - test: "Analysis move-list mini-chip (desktop vertical tree and the mobile horizontal move list) on a game with a scored blunder"
    expected: "After the red ?? glyph the move shows a small neutral '<palm> 95%' chip; the row height and move-chip layout do not jump; hover (desktop) or tap (mobile) opens the shared explanation popover with the 'Facepalm 95%' heading and the D-23 copy; tapping the mini-chip on mobile opens the popover and does NOT navigate to that move; no nested-button warning in the console"
    why_human: "D-22. The VariationTree test asserts the chip and its percent, but not the rendered look, the real touch path through the clickable mobile move chip (propagation stop), or the popover position near the move list."
  - test: "Eval chart tooltip line on a scored blunder (Games-card chart and analysis chart)"
    expected: "Hovering or touching a scored blunder marker shows a 'Facepalm 95%' line with a small palm icon directly below the 'You . Blunder' verdict, in blunder color; a mistake marker, an unscored blunder and an opponent marker show no such line; the tooltip box does not overflow or reflow awkwardly"
    why_human: "D-22. No automated test covers the tooltip line (see Warnings), and tooltip placement is visual."
  - test: "Real-phone tap on the Facepalm chip on the Flaws tab (iOS Safari and Android Chrome)"
    expected: "One tap opens the Facepalm popover and leaves it open (no open-then-close flicker); tapping outside closes it; a scroll that starts on the chip does not open it; a later keyboard or switch-control focus still opens it"
    why_human: "D-16 carried by D-20. jsdom tests simulate pointer events, but real touch compat-mouse events, Safari's no-focus-on-button-press quirk and scroll-vs-tap are not reproducible there. Still pending in 253-UAT.md, and the trigger is now the chip, not the badge."
---

# Phase 253: Facepalm Score in the Library UI Verification Report

**Phase Goal:** Show the Phase 250 facepalm score to users in the library. A "Facepalm" range filter in the Tags side panel for the Games and Flaws tabs, modelled on the tactic depth filter, and the score as its own chip next to the Blunder badge on Flaws-tab cards (`<tree-palm> Facepalm 94%`, popover on the chip) when the flaw has a score; after UAT also a mini-chip in the analysis move list and a line in the eval chart tooltip (253-CONTEXT.md D-20 to D-23).
**Verified:** 2026-11-14
**Status:** human_needed
**Re-verification:** Yes. The earlier report (2026-11-14T16:20) went stale after commits 20127b5cc (UAT redesign), 622a07b9c (docs) and e1c547a50 (blunder-only marker fix). Every truth was re-checked against the code at HEAD (e1c547a50); nothing regressed.

All code-level checks pass at HEAD. No gaps. The status is `human_needed` because the post-redesign visuals (card chip, move-list mini-chip, eval tooltip line) have never been looked at in a browser and the real-phone tap test is still pending.

## Supersession map

253-CONTEXT.md "UAT revision" (D-20..D-23) replaces part of the original design. Superseded must-haves are checked against the replacing decision, not reported as gaps.

| Original must-have (plans / D-xx) | Superseded by | Checked against |
|---|---|---|
| D-14 score inside the Blunder badge, no new chip | D-20 own chip | `FacepalmChip.tsx` and the `FlawCard` tags row |
| D-15 badge keeps blunder colors | D-20 neutral chip colors | `FACEPALM_CHIP*` in `theme.ts`; `SeverityBadge` has no facepalm prop or popover any more |
| D-16 where the trigger lives (the Blunder badge) | D-20 (trigger is the chip, same hover / tap / focus behavior) | `FacepalmBadgePopover.tsx` wraps the chip |
| D-18 badge popover copy and `Facepalm 94%` heading text | D-23 shared copy | `FacepalmExplanation.tsx` |
| D-19 filter popover first paragraph, "Not a probability." | D-23 (second paragraph kept) | `FacepalmFilter.tsx` `infoChildren` |

## Goal Achievement

The phase has no REQUIREMENTS.md entries. Truths are the roadmap goal plus D-01..D-13, D-16 (behavior), D-17 and D-20..D-23 (19 scored truths). D-14, D-15, D-18 and D-19 are superseded (above), not scored.

### Observable Truths

| # | Decision | Status | Evidence |
|---|----------|--------|----------|
| D-01 | Name "Facepalm"; code, API and docs say facepalm | VERIFIED | Params `min_facepalm_pct` / `max_facepalm_pct`, field `facepalm_score`, chip text "Facepalm"; filter label is now "Facepalm Score" per D-23 |
| D-02 | lucide `TreePalm` icon | VERIFIED | Imported and rendered `aria-hidden` in `FacepalmChip.tsx`, `FacepalmMoveChip.tsx`, `FacepalmExplanation.tsx` and the `EvalChart.tsx` tooltip; `tsc -b` and eslint clean |
| D-03 | Not a probability; no "avoidable" / "chance you'd see it" | VERIFIED | `grep -riE "avoidable\|chance you\|provisional"` over components/library, filters, analysis and lib/facepalm.ts: no matches. D-23 copy ("how easy it is to see ... as estimated by our model") makes no probability claim |
| D-04 | Full range = no clause; narrowed keeps only non-NULL in-range scores | VERIFIED | `facepalm_range_active` / `_facepalm_clause` in `library_repository.py` return None at 0/100 or None/None, else `IS NOT NULL` plus float bounds. Frontend `facepalmToQueryParams` returns `{}` at All. Backend facepalm tests pass (43) |
| D-05 | User flaws only | VERIFIED | Clause is appended in `build_flaw_filter_clauses`, used by `query_flaws` and `flaw_exists_from_table`, both scoped by user_id and `player_only_gate`. Router test seeds an opponent-ply 0.99 flaw and asserts it never matches |
| D-06 | Games tab: range joins the single flaw EXISTS | VERIFIED | `apply_game_filters` gate is `flaw_severity or flaw_tags or tactic_active or facepalm_active` and forwards both bounds; `get_library_games` threads router -> service -> `query_filtered_games`; router end-to-end Games tests (high -> game1, low -> game2) pass |
| D-07 | Provisional values accepted; no UI note; not tied to the drill cut | VERIFIED | Backend `FACEPALM_PCT_MIN/MAX` are module-local; no `blunder_check_rules` import; no "provisional" copy |
| D-08 | Third wrapper over `PresetRangeFilter`, same look as Tactic Depth | VERIFIED (look checked in browser by orchestrator pre-redesign, see 253-UAT.md test 2) | `FacepalmFilter.tsx` wraps `PresetRangeFilter` (label + info popover, summary, 4 chips, dual-thumb slider); optional `hint` prop added to the shared component |
| D-09 | Presets All/Low/Mid/High, cutoffs 30 and 70 as UI constants, All default | VERIFIED | `facepalm.ts`: `FACEPALM_MID_CUTOFF = 30`, `FACEPALM_HIGH_CUTOFF = 70`, module-private; `PRESET_ORDER = [all, low, mid, high]`; default `all` |
| D-10 | Step 5; half-open top; 27% in Low, 69.9% in Mid | VERIFIED | Slider step 5, `displayUpper` adds step-1 except at 100; API gets 0-29 / 30-69 / 70-100; backend `score >= min/100` and `score < (max+1)/100`; `toFacepalmPct` floors. Repository boundary tests (0.27, 0.2999, 0.30, 0.699, float4 0.7, 0.7001, 1.0) pass |
| D-11 | Severity toggles untouched by a narrowed range | VERIFIED | No coupling code in `FlawFilterControl.tsx` or the store; component test asserts toggles unchanged |
| D-12 | Hint "Mistakes are excluded" only while narrowed | VERIFIED | `FACEPALM_NARROWED_HINT` passed as `hint` only when `isFacepalmNarrowed(value)`; text exact; no mention of unscored blunders |
| D-13 | Panel position under Flaws, above Best Moves and Tactic Depth, both tabs | VERIFIED (browser-checked pre-redesign, 253-UAT.md test 2) | `FlawFilterControl.tsx` renders `FacepalmFilter` right after the severity block; all four call sites (FlawsTab desktop + drawer, GamesTab desktop + drawer) pass `facepalm` / `onFacepalmChange`; DOM-order test passes. The redesign did not touch panel layout, only the label text and popover copy |
| D-16 | Popover trigger behavior: hover (desktop pointer), click/tap, keyboard focus; no Tags-legend entry | VERIFIED in jsdom (real touch: human) | `FacepalmBadgePopover.tsx` (now wrapping the chip): mouse-only hover open 100 ms, 80 ms close grace, click always opens, focus opens unless caused by a pointer press, WR-01 pointerleave/pointercancel reset present; `TagChip.tsx` untouched; popover test file and FlawCard click test pass |
| D-17 | Only when `facepalm_score` non-NULL; Mistake/Inaccuracy never change; Games count badges untouched | VERIFIED | `FlawCard.tsx`: `flaw.severity === 'blunder' && flaw.facepalm_score != null` gates the chip. Tests: unscored blunder and scored mistake render no chip. `showIcon` defaults false so Games-card count badges and `TrainPuzzleCard` are unchanged |
| D-20 | Score is its own chip: `<palm> Facepalm 94%`, right after the Blunder badge, neutral colors from `FACEPALM_CHIP*`, popover trigger | VERIFIED (look: human) | `FacepalmChip.tsx`: text-xs pill with `TreePalm`, "Facepalm", `toFacepalmPct(score)%`, colors `FACEPALM_CHIP` / `FACEPALM_CHIP_BG` = `FAM_NEUTRAL` in `theme.ts` (not `SEV_BLUNDER*`), wrapped in `FacepalmBadgePopover` with testid `facepalm-badge-{gameId}-{ply}`. Rendered in `FlawCard` tags row directly after `SeverityBadge`. FlawCard test: chip text `Facepalm94%` (0.946), 0.697 floors to 69%, click opens popover |
| D-21 | Severity badges lead with the move-quality glyph on the Flaws card; Games count badges icon-less | VERIFIED (look: human) | `SeverityBadge.tsx`: `showIcon` prop renders `MoveQualityIcon quality={severity}`; only `FlawCard` passes `showIcon`. SeverityBadge tests cover each severity's glyph and the default-off case |
| D-22 | Score on analysis surfaces: move-list `<palm> 95%` mini-chip after `??` for a scored blunder with the same popover; eval tooltip `Facepalm 95%` line below the verdict; `FlawMarker` carries `facepalm_score`; no opponent scoring added | VERIFIED (look: human) | Backend: `FlawMarker.facepalm_score` in `schemas/library.py`; `_build_card` builds `facepalm_by_ply` from the both-color row list; `_build_eval_series` emits it for `severity == "blunder"` only (e1c547a50); no new scoring code. Frontend: `useAnalysisGemMarkers` maps `fm.facepalm_score` to `facepalmScore` / `facepalmByOpponent`; `VariationTree.MoveListMarker` renders `FacepalmMoveChip` after the glyph for a scored blunder (InfoPopover span trigger, propagation stopped); `EvalChart.tsx` renders `eval-chart-tooltip-facepalm` under the verdict gated on blunder + non-null score. Tests: `VariationTree` (10b), `test_flaw_marker_carries_stored_facepalm_score`, eval-chart-service tests |
| D-23 | One shared explanation copy; filter renamed "Facepalm Score"; second filter paragraph kept; no "Not a probability." sentence | VERIFIED | `FacepalmExplanation.tsx` carries the D-23 text verbatim (heading `Facepalm N%`, your/their switch) and is used by both `FacepalmBadgePopover` and `FacepalmMoveChip`; `FacepalmFilter` label `Facepalm Score` and the same first paragraph plus the band-ranges paragraph; FlawCard and FacepalmExplanation tests assert the exact copy and the "their level" variant |

**Score:** 19/19 truths verified (0 behavior-unverified). Visual and real-device aspects are routed to human verification, not scored as failures.

None of the truths asserts a state transition or a cancellation / cleanup / ordering invariant that is not exercised by a test, except the D-16 real-touch path, which is already a human item and has jsdom coverage (popover test: 247 lines, includes the WR-01 stuck-flag regressions).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/repositories/library_repository.py` | range clause, params on the flaw filter / EXISTS / list / games queries, `facepalm_score` in `_build_flaw_item` | VERIFIED | Present, wired, compiled and run end to end by tests |
| `app/repositories/query_utils.py` | `facepalm_active` gate in `apply_game_filters` | VERIFIED | Present, forwards both bounds |
| `app/routers/library.py` | `min/max_facepalm_pct` (ge/le) on the games and flaws endpoints | VERIFIED | Both endpoints; 422 outside 0..100 tested |
| `app/schemas/library.py` | `FlawListItem.facepalm_score`, `FlawMarker.facepalm_score` | VERIFIED | Both `float \| None = None` |
| `app/services/library_service.py` | param pass-through; `facepalm_by_ply` into `FlawMarker`, blunder only | VERIFIED | |
| `frontend/src/lib/facepalm.ts` | constants, presets, helpers, query params, `toFacepalmPct` | VERIFIED | |
| `frontend/src/components/filters/FacepalmFilter.tsx` | wrapper, `filter-facepalm` testid prefix | VERIFIED | |
| `frontend/src/components/filters/PresetRangeFilter.tsx` | optional `hint` | VERIFIED | |
| `frontend/src/hooks/useFlawFilterStore.ts` | `facepalmMin/Max`, defaults, active-dot clause | VERIFIED | |
| `frontend/src/components/library/FacepalmChip.tsx` | own pill, popover trigger | VERIFIED | New in 20127b5cc |
| `frontend/src/components/library/FacepalmExplanation.tsx` | shared D-23 copy | VERIFIED | New in 20127b5cc |
| `frontend/src/components/library/FacepalmBadgePopover.tsx` | hover / click / focus popover shell | VERIFIED | Now wraps the chip; filename kept |
| `frontend/src/components/analysis/FacepalmMoveChip.tsx` | move-list mini-chip | VERIFIED | Mirrors `GemMoveBadge` (shared `InfoPopover`, span trigger) |
| `frontend/src/components/analysis/VariationTree.tsx` | `facepalmScore` on `FlawMarkerEntry`, chip after glyph | VERIFIED | |
| `frontend/src/components/library/EvalChart.tsx` | tooltip line | VERIFIED | |
| `frontend/src/hooks/analysis/useAnalysisGemMarkers.ts` | score to marker entry | VERIFIED | |
| `frontend/src/lib/theme.ts` | `FACEPALM_CHIP`, `FACEPALM_CHIP_BG` | VERIFIED | Aliases of the neutral family tokens |
| `frontend/src/components/library/SeverityBadge.tsx` | `showIcon` only; no facepalm prop | VERIFIED | |
| `frontend/src/types/library.ts` | `FlawListItem.facepalm_score`, `FlawMarker.facepalm_score` | VERIFIED | |
| `CHANGELOG.md` | bullet under `[Unreleased]` | VERIFIED | Bullet rewritten for the redesign (chip, move list, tooltip) |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `apply_game_filters` | `facepalm_range_active` / `flaw_exists_from_table` | `or facepalm_active` gate, bounds forwarded | WIRED |
| `build_flaw_filter_clauses` | `_facepalm_clause` | appended once, shared by `query_flaws` and the EXISTS | WIRED |
| router -> service -> repository | min/max params | keyword forwards on both list endpoints | WIRED |
| FlawsTab / GamesTab (x2 each) | `FlawFilterControl` -> `FacepalmFilter` | `facepalm` / `onFacepalmChange` | WIRED |
| `useLibraryGames` / `useLibraryFlaws` | `facepalmToQueryParams` -> `client.ts` -> endpoints | query key and request | WIRED |
| `FlawCard` tags row | `FacepalmChip` -> `FacepalmBadgePopover` -> `FacepalmExplanation` | gated on blunder + non-null score | WIRED |
| `FlawCard` | `SeverityBadge showIcon` -> `MoveQualityIcon` | prop | WIRED |
| `game_flaws.facepalm_score` | `FlawMarker.facepalm_score` | `_build_card` -> `facepalm_by_ply` -> `_build_eval_series` (blunder only) | WIRED |
| `FlawMarker` (game data) | `useAnalysisGemMarkers` -> `flawMarkerByNodeId` -> `VariationTree` -> `FacepalmMoveChip` | `facepalmScore`, `facepalmByOpponent` | WIRED |
| `FlawMarker` | `EvalChart` tooltip | `activeMarker.facepalm_score` | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| Filter range | `facepalmMin/Max` | store -> params -> clause on `game_flaws.facepalm_score` | Yes (router tests hit the DB) | FLOWING |
| Chip percent | `flaw.facepalm_score` | `_build_flaw_item` reads the stored REAL column | Yes | FLOWING |
| Move-list mini-chip and tooltip | `fm.facepalm_score` | `facepalm_by_ply` from stored rows; router test reads a seeded 0.87 back through the games payload | Yes | FLOWING |

### Behavioral Spot-Checks and Test Runs

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Backend facepalm tests | `uv run pytest tests/services/test_eval_chart_service.py tests/test_library_router.py tests/test_library_repository.py tests/repositories/test_library_repository.py tests/test_query_utils.py -n auto -q -k facepalm` | 43 passed | PASS |
| Frontend suites over the touched areas | `npx vitest run src/components/library src/components/analysis src/components/filters src/lib/__tests__/facepalm.test.ts src/hooks` | 93 files, 1568 passed | PASS |
| Type check, lint | `npx tsc -b`; `npx eslint` over the touched files; `uv run ruff check app/ tests/` | clean | PASS |
| Nesting-depth gate | `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` | 1507 functions, no breaches | PASS |
| Banned copy | `grep -riE "avoidable\|chance you\|provisional"` over new copy | no matches | PASS |
| Full gate | run by the orchestrator at 622a07b9c (green); targeted re-run after e1c547a50 (115 backend, 311 frontend, green) | not re-run here | accepted |

### Probe Execution

Step 7c: SKIPPED. The phase declares no probes.

### Requirements Coverage

No REQUIREMENTS.md entries map to Phase 253. No orphaned requirements.

### Anti-Patterns Found

No TBD / FIXME / XXX markers, stubs or hardcoded-empty data in the phase's files. Notes:

| File | Observation | Severity |
|------|-------------|----------|
| `app/services/library_service.py` | Comment says "Bug fix (253 review WR-01)" but the review's WR-01 was the badge press-flag; the marker fix came from the post-UAT review. Wording only | Info |
| `frontend/src/components/library/FacepalmBadgePopover.tsx` | Names (`FacepalmBadgePopover`, `facepalm-badge-*` testid) still say "badge" although the trigger is now the chip. Cosmetic; testids are Umami targets, so renaming would change analytics | Info |

### Warnings (not gaps)

1. **No automated test for two of the D-22 frontend links.** Nothing asserts the `eval-chart-tooltip-facepalm` line in `EvalChart` (no EvalChart test mentions facepalm), and nothing asserts that `useAnalysisGemMarkers` maps `fm.facepalm_score` into `FlawMarkerEntry` (the `Analysis.test.tsx` suite does not mention facepalm). Both are plain conditionals that read correctly in the code, and the data into them (backend marker payload) and out of them (`VariationTree` chip) are tested, so they are marked VERIFIED, but a regression in either would not be caught. The tooltip line is on the human list.
2. **253-REVIEW.md predates the redesign.** It reviewed the 30 files at the pre-UAT state (6 findings: WR-01 fixed, IN-01..IN-05 open as dispositioned). The post-UAT files (`FacepalmChip`, `FacepalmExplanation`, `FacepalmMoveChip`, and the changes to `VariationTree`, `EvalChart`, `useAnalysisGemMarkers`, `SeverityBadge`, `theme.ts`) have had no separate code review; 253-SECURITY.md likewise predates them (display-only, no new input surface). An optional `/gsd-code-review 253` would close that.
3. Review IN-01..IN-05 stay open as dispositioned (key-shape wording, redundant `IS NOT NULL`, one over-long comment line, duplicate testid across mobile/desktop bodies, no cross-user isolation test). None blocks; the cross-user case is covered by construction (`GameFlaw.user_id == user_id` on both paths).

### Human Verification Required

The earlier browser UAT (253-UAT.md) covered the Tags panel layout (test 2, still valid: the redesign changed only the filter label and popover copy) and the old inside-badge look (test 3, superseded by D-20 / D-21). What genuinely needs a human or a browser for the current design:

1. **Flaws-card look (D-20, D-21).** Neutral Facepalm chip after the Blunder badge; move-quality glyph in the severity badges; glyph not squashed, badge height unchanged, tags row wraps sensibly at 375 px; unscored blunders show no chip; Games count badges icon-less.
2. **Analysis move-list mini-chip (D-22), desktop and mobile horizontal list.** Placement after `??`, no layout jump, popover content, and on mobile that a tap opens the popover without navigating to the move.
3. **Eval chart tooltip line (D-22).** `Facepalm 95%` below the verdict on a scored blunder only; no line on mistake, unscored or opponent markers; tooltip layout.
4. **Real-phone tap on the Facepalm chip (D-16, iOS Safari and Android Chrome).** Open on one tap and stay open, outside tap closes, scroll starting on the chip does not open, keyboard / switch-control focus still opens. Pending since the first report.

### Gaps Summary

No gaps. Every locked, non-superseded decision (D-01..D-13, D-16 behavior, D-17) and every UAT revision decision (D-20..D-23) is implemented, wired end to end (UI -> store -> query key -> client -> router -> service -> repository -> DB clause; DB column -> marker payload -> move list and chart tooltip) and covered by passing tests, with the two test-coverage warnings above. Superseded decisions D-14, D-15, D-18 and D-19 were checked against their replacements. The status is `human_needed` solely because of the four visual and real-device items.

---

_Verified: 2026-11-14_
_Verifier: Claude (gsd-verifier)_
