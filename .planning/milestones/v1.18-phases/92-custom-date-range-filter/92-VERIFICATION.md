---
phase: 92-custom-date-range-filter
verified: 2026-05-22T05:00:00Z
status: human_needed
score: 13/13 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Scenario 1 — Preset parity (8 presets, WDL totals match baseline)"
    expected: "All time matches exactly; date-bounded presets within ≤24h UTC/local boundary fuzz"
    why_human: "Requires running browser + comparing WDL numbers against a pre-deploy baseline; cannot verify visually via grep"
  - test: "Scenario 2 — Desktop Custom range (Popover, auto-close, trigger label)"
    expected: "Popover opens anchored to Select trigger with no layout jump; two-month range Calendar; auto-closes on full pick; trigger label shows resolved range"
    why_human: "Visual/UX flow — popover animation, anchoring fidelity, label rendering can only be confirmed in a live browser"
  - test: "Scenario 3 — Mobile Custom range (nested Drawer, Apply, backdrop dismiss)"
    expected: "Nested bottom sheet slides up over FilterPanel drawer; Apply commits and closes; backdrop click cancels without committing partial range (D-08)"
    why_human: "Mobile viewport behavior + vaul nested sheet animation + backdrop dismiss semantics; requires DevTools mobile emulation"
  - test: "Scenario 4 — Switch back to preset (custom range cleared)"
    expected: "Picking a preset after a custom range resets the trigger label to preset name and clears customRange state; subsequent open of 'Custom range…' starts fresh"
    why_human: "End-to-end UX flow with state assertion only observable from the running app"
  - test: "Scenario 5 — Insights gating regression check"
    expected: "Endgame Insights returns 'Clear Custom date range filter' blocking message when any date filter is active; returns a report when 'All time' is set"
    why_human: "Cross-page UI flow; backend gate is unit-tested but the user-facing message rendering is not"
  - test: "Scenario 6 — Reload behavior (in-memory filters reset to defaults)"
    expected: "Hard-reload resets filters to DEFAULT_FILTERS; no stale TanStack Query keys or console errors"
    why_human: "Browser reload semantics + console error inspection cannot be grep-verified"
---

# Phase 92: Custom Date Range Filter — Verification Report

**Phase Goal:** Add a "Custom range…" entry to the recency dropdown in `FilterPanel.tsx` that opens a popover with start/end date inputs, and replace the closed `Recency` string union on the API wire with two optional `from_date` / `to_date` date params. The 95% preset case remains visually unchanged. Backend stays single-shape (`played_at >= from AND played_at < to + 1d`); frontend owns "now".

**Verified:** 2026-05-22T05:00:00Z
**Status:** human_needed (all 13 automatable truths verified; 6 UAT scenarios deferred — explicitly per Plan 06 Task 3 deferred)
**Re-verification:** No — initial verification.

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | Wire-format flip complete: no `recency` request fields cross the wire from frontend → backend | ✓ VERIFIED | `grep -rn "recency_cutoff\|RECENCY_DELTAS" app/` returns ZERO matches. Remaining frontend `recency` matches are UI-only (FilterState field, visibleFilters key, label copy, type-only refs); none flow into `dateRangeToWireParams` output |
| 2  | `apply_game_filters` uses inclusive `>= from_date` and `< to_date + 1 day` (D-10) | ✓ VERIFIED | `app/repositories/query_utils.py:70-73` — `if from_date is not None: stmt = stmt.where(Game.played_at >= from_date)` + `if to_date is not None: stmt = stmt.where(Game.played_at < to_date + datetime.timedelta(days=1))` |
| 3  | 422 cross-field validation via Pydantic `model_validator` AND inline Query-param `HTTPException` | ✓ VERIFIED | Four `_check_date_range` model_validators in `app/schemas/{openings,insights,stats,opening_insights}.py`; three `HTTPException(status_code=422, detail="from_date must be <= to_date")` Query-path guards in `app/routers/stats.py:39,68,99` and two in `app/routers/endgames.py:51,93` |
| 4  | Insights gate blocks when `from_date is not None or to_date is not None`, message contains `"Clear Custom date range filter"` | ✓ VERIFIED | `app/routers/insights.py:69-70` shows the new gate predicate + `blocking.append("Clear Custom date range filter")` |
| 5  | All 7 frontend hooks pass `from_date`/`to_date` to backend (including hidden `useBookmarkPhaseEntryMetrics`) | ✓ VERIFIED | All hooks import `resolveDateRange, dateRangeToWireParams` from `@/lib/recency` and spread `dateParams` into request bodies + queryKeys: `useOpenings.ts:6`, `useEndgames.ts:3`, `useEndgameInsights.ts:4`, `useOpeningInsights.ts:11`, `useNextMoves.ts:7`, `useStats.ts:6` (four functions: `useRatingHistory`, `useGlobalStats`, `useMostPlayedOpenings`, `useBookmarkPhaseEntryMetrics`) |
| 6  | `Recency` renamed to `RecencyPreset` and marked UI-only; no `Recency` type identifier crosses the API boundary | ✓ VERIFIED | `frontend/src/types/api.ts:39` exports `RecencyPreset` with comment "UI-only preset, not sent to the API"; `grep -c "^export type Recency " frontend/src/types/api.ts` returns 0 |
| 7  | Custom range UI: 9th SelectItem; `CustomRangePopover` (desktop) + `CustomRangeDrawer` (mobile via `DrawerNested`) wired into `FilterPanel`; resolved-range label; custom cleared on preset pick | ✓ VERIFIED | `FilterPanel.tsx:251` (9th `SelectItem value="custom" data-testid="filter-recency-custom"`); imports `CustomRangePopover, formatCustomRangeLabel` and `CustomRangeDrawer` at lines 18-19; `PopoverAnchor` wraps the Select (line 223); trigger label conditional at line 239 `filters.customRange ? formatCustomRangeLabel(filters.customRange) : <SelectValue />`; preset-pick path at line 232 sets `customRange: null` |
| 8  | Calendar primitive: `react-day-picker@10.0.1` in package.json; `frontend/src/components/ui/calendar.tsx` exists; `calendar-day-YYYY-MM-DD` testid present | ✓ VERIFIED | `frontend/package.json:34` shows `"react-day-picker": "^10.0.1"`; `calendar.tsx:204` renders `data-testid={`calendar-day-${format(day.date, 'yyyy-MM-dd')}`}` |
| 9  | `DrawerNested` exported from `frontend/src/components/ui/drawer.tsx` (wraps `DrawerPrimitive.NestedRoot`) | ✓ VERIFIED | `drawer.tsx:17-20` defines the wrapper with `data-slot="drawer-nested"`; line 108 exports it |
| 10 | Boundary tests pass: 6 in `TestDateFilterBoundarySemantics` + 1 insights-gate test; full backend suite (1617) and frontend suite (611) green | ✓ VERIFIED | `uv run pytest tests/test_integration_routers.py::TestDateFilterBoundarySemantics tests/routers/test_insights_openings.py::test_insights_blocked_when_from_date_set tests/test_query_utils.py -x` → 11 passed; `cd frontend && npm test -- --run` → 54 files, 611 tests passed; SUMMARY 92-06 reports `pytest -x` → 1617 passed, 6 skipped |
| 11 | `CHANGELOG.md [Unreleased]` populated with Added/Changed/Removed/Tests entries referencing Phase 92 | ✓ VERIFIED | CHANGELOG `[Unreleased]` section contains four subsections, each with a Phase 92 bullet; `grep -c "Phase 92" CHANGELOG.md` ≥ 4; `grep -c "Custom date range" CHANGELOG.md` ≥ 2 |
| 12 | `92-HUMAN-UAT.md` exists with 6 scenarios; runnable against existing dev DB | ✓ VERIFIED | File exists with 6 `### Scenario N` headers + checklist; setup section explicitly notes "Per Adrian's memory ('No dev DB reset in plans'): Do NOT run `bin/reset_db.sh`" |
| 13 | Code review status `fixed` — all three warnings (WR-01/02/03) closed by commits 59dce407+fd113a23, 588add37, 71fb6336 | ✓ VERIFIED | `92-REVIEW.md` frontmatter `status: fixed`; commits referenced in `git log` confirmed (`fd113a23 fix(92): use derive-state-during-render for CustomRangeDrawer resync (WR-01)`, `71fb6336 fix(92): drop unused open prop from CustomRangePopover (WR-03)`, `588add37 fix(92): update stale recency docstrings to from_date/to_date (WR-02)`) |

**Score:** 13 / 13 truths verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app/repositories/query_utils.py` | `apply_game_filters` with `from_date`/`to_date` predicates | ✓ VERIFIED | Lines 18-19 declare params; lines 68-73 emit conditional WHERE; `recency_cutoff` removed everywhere in `app/` (grep zero hits) |
| `app/schemas/openings.py` | `OpeningsRequest` + `NextMovesRequest` with `from_date`/`to_date` + `_check_date_range` | ✓ VERIFIED | Lines 39-40 (OpeningsRequest), 227-228 (NextMovesRequest); both have `@model_validator(mode="after")` checks at lines 50, 234 |
| `app/schemas/insights.py` | `FilterContext` with date fields + validator | ✓ VERIFIED | Lines 135-136 + validator at line 143-150 |
| `app/schemas/stats.py` | `BookmarkPhaseEntryRequest` with date fields + validator | ✓ VERIFIED | Lines 133-134 + validator at line 136-143 |
| `app/schemas/opening_insights.py` | `OpeningInsightsRequest` with date fields + validator | ✓ VERIFIED | Lines 29-30 + validator at line 39-46 |
| `tests/test_query_utils.py` | Direct unit tests for date predicates (RED→GREEN scaffold from Plan 02 Task 1) | ✓ VERIFIED | File present; 4 test functions; all pass |
| `frontend/src/lib/recency.ts` | `presetToDates`, `dateToWire`, `dateRangeToWireParams`, `resolveDateRange` | ✓ VERIFIED | Four exports at lines 74, 97, 107, 126 |
| `frontend/src/lib/__tests__/recency.test.ts` | Unit tests including memoization and wire format | ✓ VERIFIED | 10 tests, all pass |
| `frontend/src/types/api.ts` | `RecencyPreset` type with UI-only comment | ✓ VERIFIED | Line 39 |
| `frontend/src/components/ui/calendar.tsx` | shadcn Calendar primitive with day-cell testid | ✓ VERIFIED | File exists; uses react-day-picker; day-cell testid present (line 204) |
| `frontend/src/components/ui/drawer.tsx` | `DrawerNested` re-export | ✓ VERIFIED | Lines 13-20 + line 108 |
| `frontend/src/components/filters/CustomRangePopover.tsx` | Desktop popover with range Calendar; emits `custom-range-popover` + `custom-range-calendar` testids | ✓ VERIFIED | Testids present at lines 91, 100 |
| `frontend/src/components/filters/CustomRangeDrawer.tsx` | Mobile nested-drawer Calendar with Apply CTA | ✓ VERIFIED | Lines 110, 121, 132 cover `drawer-custom-range`, `custom-range-calendar`, `btn-apply-custom-range` testids |
| `frontend/src/components/filters/FilterPanel.tsx` | 9th SelectItem + PopoverAnchor wrapping + breakpoint-branched custom UI + customRange in DEFAULT_FILTERS/FILTER_DOT_FIELDS/areFiltersEqual | ✓ VERIFIED | All wired (lines 50, 52, 64-65, 84, 122-124, 217-271) |
| `tests/test_integration_routers.py` | `TestDateFilterBoundarySemantics` class with 6 tests | ✓ VERIFIED | Class at line 524; 6 `async def test_` methods inside |
| `tests/routers/test_insights_openings.py` | `test_insights_blocked_when_from_date_set` | ✓ VERIFIED | Line 160 |
| `.planning/phases/92-custom-date-range-filter/92-HUMAN-UAT.md` | 6-scenario UAT script | ✓ VERIFIED | File present, 6 scenarios |
| `CHANGELOG.md` | `[Unreleased]` with Phase 92 entries | ✓ VERIFIED | Added/Changed/Removed/Tests subsections each with Phase 92 bullet |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `app/repositories/query_utils.py` | `app/repositories/{openings,endgame,stats}_repository.py` | `apply_game_filters` callsites pass `from_date`/`to_date` | ✓ WIRED | `recency_cutoff` removed across repositories; no residuals |
| `app/routers/insights.py` | `_validate_full_history_filters` gate | `from_date is not None or to_date is not None` → `"Clear Custom date range filter"` | ✓ WIRED | Confirmed at lines 55, 69-70 |
| `app/services/insights_service.py` | `endgame_service.get_endgame_overview` | Internal LLM windows: `last_3mo = today - 90d`, `all_time = both None` (D-18) | ✓ WIRED | REVIEW.md confirms the resolved code; SUMMARY confirms; docstring corrected via WR-02 |
| `frontend/src/components/filters/FilterPanel.tsx` | `useFilterStore` / FilterState | `customRange` sibling field present; cleared on non-custom preset; lit in FILTER_DOT_FIELDS | ✓ WIRED | Lines 52, 65, 84, 122-124, 232, 257-275 |
| `frontend/src/lib/recency.ts` | Every consuming hook | `dateRangeToWireParams(resolveDateRange(filters))` spread into request body + queryKey | ✓ WIRED | 7 hooks verified by import + queryFn inspection |
| `frontend/src/components/filters/CustomRangePopover.tsx` | `frontend/src/components/ui/popover.tsx` | `PopoverContent`/`PopoverAnchor` anchor flow | ✓ WIRED | Component imports + uses these; FilterPanel wraps Select in `<Popover>...<PopoverAnchor asChild>` |
| `frontend/src/components/filters/CustomRangeDrawer.tsx` | `frontend/src/components/ui/drawer.tsx` (DrawerNested) | Mobile nested sheet anchored over FilterPanel drawer | ✓ WIRED | Component imports `DrawerNested`; renders nested drawer with Apply CTA |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `FilterPanel.tsx` Recency Select trigger | `filters.customRange` (display) + `filters.recency` | Parent `useFilterStore` / passed via props; updated by Select handlers + Apply commit | ✓ Real (consumer state) | ✓ FLOWING |
| `CustomRangeDrawer` Calendar | `localRange` `useState`, resynced from `value` (WR-01 fix) | Calendar `onSelect` writes locally; Apply commits to parent | ✓ Real | ✓ FLOWING |
| Hook queryFn → backend | `dateParams.from_date` / `dateParams.to_date` | `dateRangeToWireParams(resolveDateRange(filters))` from `lib/recency.ts` | ✓ Real (date-fns format yyyy-MM-dd) | ✓ FLOWING |
| `apply_game_filters` SQL | `played_at >= from_date AND played_at < to_date + 1 day` | Direct SQLAlchemy `select.where` chain | ✓ Real (verified by boundary integration tests) | ✓ FLOWING |
| `_validate_full_history_filters` | `filters.from_date`, `filters.to_date` | `FilterContext` body from request | ✓ Real (gated by integration test) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase 92 boundary integration tests pass | `uv run pytest tests/test_integration_routers.py::TestDateFilterBoundarySemantics tests/routers/test_insights_openings.py::test_insights_blocked_when_from_date_set tests/test_query_utils.py -x` | 11 passed in 1.21s | ✓ PASS |
| Frontend `recency.ts` unit tests pass | `npm test -- --run src/lib/__tests__/recency.test.ts` | 10/10 passed | ✓ PASS |
| Full frontend test suite | `npm test -- --run` | 54 files, 611 tests passed | ✓ PASS |
| Frontend lint clean | `npm run lint` | exit 0, no output | ✓ PASS |
| `recency.ts` exports the 4 expected helpers | `grep ^export frontend/src/lib/recency.ts` | `presetToDates`, `dateToWire`, `dateRangeToWireParams`, `resolveDateRange` | ✓ PASS |
| Calendar primitive renders day-cell testid | `grep calendar-day frontend/src/components/ui/calendar.tsx` | 1 match (line 204) | ✓ PASS |
| No residual `recency_cutoff` in backend | `grep -rn "recency_cutoff\|RECENCY_DELTAS" app/` | 0 matches | ✓ PASS |
| Only `RecencyPreset` type identifier in frontend | `rg "\bRecency\b" frontend/src/ \| grep -v RecencyPreset` | 2 matches — both are user-facing label strings ("Recency" comment + heading), not types | ✓ PASS |
| Custom-range UI testids present | `grep data-testid frontend/src/components/filters/CustomRange*.tsx` | 5 matches across the two files | ✓ PASS |
| 9 SelectItems in Recency Select | `sed -n '243,251p' frontend/src/components/filters/FilterPanel.tsx` | 9 SelectItems incl. `value="custom"` | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| (no `scripts/*/tests/probe-*.sh` files declared by phase or project) | — | — | SKIPPED (no probes apply) |

### Requirements Coverage

Phase 92 uses **synthetic requirement IDs** documented in Plan 01's frontmatter comment block (REQUIREMENTS.md has no formal `P92-*` entries; the IDs map directly to ROADMAP §Scope (in) bullets 1-7).

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| P92-R1 | Plan 01 | Bookmark time-series recency removal (D-19) | ✓ SATISFIED | `TimeSeriesRequest` in `app/schemas/openings.py:155` documents the removal; `frontend/src/types/position_bookmarks.ts` no longer has `recency` field; CHANGELOG [Removed] entry references Phase 92 D-19 |
| P92-R2 | Plans 02, 06 | API contract: `from_date`/`to_date` replaces closed `Recency` union | ✓ SATISFIED | Truths 1, 2, 3, 10 (backend flip + 422 + boundary tests) |
| P92-R3 | Plan 03 | FE preset → date conversion, TZ canonicalization, memoization | ✓ SATISFIED | Truth 5 + recency.ts unit tests (memoization Test 4-5; local-TZ Test 7) |
| P92-R4 | Plans 04, 05, 06 | Custom range UI (9th item + popover + drawer + Calendar + DrawerNested + UAT script) | ✓ SATISFIED (automated) / ? HUMAN UAT pending | Truths 7, 8, 9, 12; visual UAT scenarios deferred to user run |
| P92-R5 | Plan 03 | Hook + URL param migration | ✓ SATISFIED | Truth 5; D-14 audit confirmed zero URL-param `recency` matches |
| P92-R6 | Plan 03 | `Recency` → `RecencyPreset` UI-only | ✓ SATISFIED | Truth 6 |
| P92-R7 | Plan 02 | LLM insight prompt audit (D-18) — internal windows preserve semantics; gate updated | ✓ SATISFIED | Truth 4 + insights-gate test + WR-02 docstring fix |

No orphaned requirements: every ROADMAP scope-in item (1-7) maps to a synthetic `P92-RN` covered by at least one plan. REQUIREMENTS.md has no Phase 92 entries to cross-check, consistent with Plan 01's documented "synthetic" disclosure.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `app/repositories/openings_repository.py` | 111-114 | Duplicated date-filter predicate in `_build_base_query` (IN-01 from REVIEW.md) | ℹ️ Info | Pre-existing duplication of `apply_game_filters` filter cluster — mirrored the prior `recency_cutoff` predicate. Tracked as out-of-scope refactor in REVIEW.md IN-01. Not introduced by Phase 92. |
| `app/repositories/query_utils.py` | 34-35 | `to_date` docstring lead phrase could be misread as exclusive (IN-02 from REVIEW.md) | ℹ️ Info | Minor doc clarity issue; the parenthesised clarification is correct. Cosmetic; out-of-scope. |
| `app/schemas/{opening_insights,openings,stats,insights}.py` | various | No min/max date guard (IN-03 from REVIEW.md) | ℹ️ Info | Defense-in-depth only; SQL tolerates degenerate inputs. Flagged YAGNI; out-of-scope. |
| `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx` | 53-64 | Mock fixture missing required Pydantic fields (IN-04 from REVIEW.md) | ℹ️ Info | Pre-existing test-mock divergence from schema; not introduced by Phase 92. |

No `TODO`/`FIXME`/`XXX` debt markers introduced by Phase 92 changes. The three REVIEW.md warnings (WR-01/02/03) have all been resolved (status `fixed`, fix commits verified in git log).

### Deferred Items

No items deferred to later phases. The 6 UAT scenarios (Scenario 1-6 in `92-HUMAN-UAT.md`) are deferred to the human verification flow within this phase (Plan 06 Task 3), not to a later phase.

### Human Verification Required

Six UAT scenarios that automation cannot cover. Each maps directly to a checkbox in `92-HUMAN-UAT.md`. Plan 06 Task 3 was explicitly deferred per the SUMMARY: "Task 3 (run the 6 UAT scenarios in a browser) is deferred to the HUMAN-UAT.md flow. The script is written … Scenarios pending user run."

#### 1. Preset parity (the 95% case)

**Test:** Open Openings, iterate through all 8 presets (All time / Past week / Past month / 3 months / 6 months / 1 year / 3 years / 5 years), record the WDL total for each.
**Expected:** "All time" matches a pre-deploy baseline exactly; date-bounded presets within ≤24h UTC/local boundary fuzz per D-16 / RESEARCH.md §Pitfall 2.
**Why human:** Requires running browser + comparing WDL numbers against a pre-deploy baseline; cannot verify visually via grep.

#### 2. Desktop Custom range

**Test:** At ≥768 px viewport: click Recency Select → pick "Custom range…" (9th item) → verify Popover opens anchored to the Select trigger with no layout jump → pick `from` and `to` on the two-month Calendar → verify Popover auto-closes → verify the Select trigger label shows `"MMM d, yyyy – MMM d, yyyy"`.
**Expected:** Smooth popover open/close, anchored cleanly to the trigger, label readable.
**Why human:** Visual/UX flow — popover animation, anchoring fidelity, label rendering can only be confirmed in a live browser.

#### 3. Mobile Custom range

**Test:** Switch to mobile width (Chrome DevTools or <768 px) → open the FilterPanel drawer → pick "Custom range…" → verify a nested bottom sheet (`DrawerNested`) slides up over the FilterPanel drawer → pick `from` + `to` → tap Apply → verify the nested drawer closes, outer drawer remains open. **Then reopen Custom range, pick only `from`, tap the backdrop**, verify the partial range is NOT committed (D-08).
**Expected:** Nested sheet animates correctly; Apply commits; backdrop cancels.
**Why human:** Mobile viewport behavior + vaul nested sheet animation + backdrop dismiss semantics; requires DevTools mobile emulation.

#### 4. Switch back to preset

**Test:** With a custom range active, open Recency Select → pick "Past month" → verify trigger label updates to "Past month" → reopen "Custom range…" and confirm no pre-selected range.
**Expected:** Preset pick clears `customRange`; subsequent custom-range opens start fresh.
**Why human:** End-to-end UX flow with state assertion only observable from the running app.

#### 5. Insights gating regression check

**Test:** Set Recency to "All time", navigate to Endgames, click "Get Insights" — report should generate. Then set a custom range (or non-all-time preset), click "Get Insights" — verify the UI displays a message containing `"Clear Custom date range filter"`.
**Expected:** Insights blocked when any date filter is active; message matches expected substring.
**Why human:** Cross-page UI flow; backend gate is unit-tested but the user-facing message rendering is not.

#### 6. Reload behavior

**Test:** Set a custom range, hard-reload the page, verify filters reset to `DEFAULT_FILTERS` with no stale TanStack Query cache errors in the console.
**Expected:** In-memory filter store resets cleanly; no errors.
**Why human:** Browser reload semantics + console error inspection cannot be grep-verified.

### Gaps Summary

No automated gaps. The full backend (1617 tests) and frontend (611 tests) suites pass. All 13 must-have truths verify against the codebase. All three REVIEW.md warnings are resolved with verifiable fix commits. The remaining work is exactly the 6 UAT scenarios from `92-HUMAN-UAT.md`, which Plan 06 Task 3 deferred to the human verification flow; the orchestrator should persist these 6 items into the follow-up UAT track.

---

_Verified: 2026-05-22T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
