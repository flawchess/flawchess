---
phase: 98-per-tc-collapsible-endgame-type-cards
verified: 2026-05-30T13:22:10Z
status: verified
gap_resolution: "Blocking ruff-format gap resolved at merge (PR #163, CI ruff format --check green; confirmed clean again at v1.21 close 2026-05-31). The 2 visual/human-confirm items accepted: UI shipped to prod (deployed via release PR #164) and confirmed live."
score: 8/9 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Frontend lint/test/knip gates pass — ruff format --check passes (SC-10)"
    status: failed
    reason: "5 backend files modified by phase 98 are not ruff-formatted. CI gate `uv run ruff format --check app/ tests/` exits 1."
    artifacts:
      - path: "app/schemas/endgames.py"
        issue: "Line-length formatting: `| None` continuation style"
      - path: "app/services/endgame_service.py"
        issue: "3 formatting hunks: dict type annotation line-wrap, inline ternaries"
      - path: "tests/services/test_insights_service.py"
        issue: "2 formatting hunks: inline ternaries in ConversionRecoveryStats calls"
      - path: "tests/test_endgame_service.py"
        issue: "4 formatting hunks: trailing spaces after inline comments"
      - path: "tests/test_endgame_zones.py"
        issue: "Literal list formatting: multi-value list should be split to one-per-line"
    missing:
      - "Run `uv run ruff format app/ tests/` and commit the result before merging"
human_verification:
  - test: "Open Endgames page on desktop + narrow the viewport"
    expected: "Collapsible per-TC cards render full-width; four tiles per card show vertical and horizontal dividers (not bordered boxes) at the 2x2 breakpoint; gauges remain readable on mobile 1x4 layout"
    why_human: "Visual divider grammar and responsive staircase (4x1 -> 2x2 -> 1x4) not reliably asserted in jsdom"
  - test: "Import a user with substantially more bullet games but non-trivial rapid count (e.g. 400 bullet / 60 rapid)"
    expected: "Rapid card expands by default because 60 * 600 = 36 000 > 400 * 60 = 24 000 (time-weighted beats raw count). Bullet card starts collapsed."
    why_human: "Requires real imported game distribution; jsdom tests cover the algorithm but not the real-data user perception"
---

# Phase 98: Per-TC Collapsible Endgame Type Cards Verification Report

**Phase Goal:** Replace the 3-col grid of five per-type EndgameTypeCards with full-width vertically-stacked collapsible per-TC accordion cards (bullet/blitz/rapid/classical), the user's primary TC expanded by default, each card holding a 4-tile grid (rook/minor_piece/pawn/queen — Mixed dropped), Conv/Recov gauges restored and banded per-(class x TC).
**Verified:** 2026-05-30T13:22:10Z
**Status:** gaps_found (1 blocking gap: ruff format; 2 HUMAN-UAT items)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Per-(class x TC) Conv/Recov/ScoreGap bands exist in generated endgameZones.ts (SC-6) | VERIFIED | `PER_CLASS_TC_GAUGE_ZONES` exported at line 147 of `frontend/src/generated/endgameZones.ts`; 5 classes x 4 TCs confirmed in `app/services/endgame_zones.py` lines 538-618; drift gate exits 0 |
| 2 | The /stats endgame breakdown exposes per-(class x TC) rates + counts via `categories_by_tc` (SC-8) | VERIFIED | `_aggregate_endgame_stats_by_tc` defined at line 776 and called at line 3706 in `endgame_service.py`; optional field in `app/schemas/endgames.py` line 224; TS interface at `frontend/src/types/endgames.ts` line 74 |
| 3 | LLM insights path response shape unchanged — `categories` list and `assign_per_class_zone` unaffected (D-15/SC-8) | VERIFIED | `grep -v '^#' insights_service.py \| grep -c "categories_by_tc"` = 0; `assign_per_class_zone` still called at lines 1064 and 1100; `TestD15LlmPathInvariant` (2 tests) pass |
| 4 | The Endgame Type Breakdown renders full-width vertically-stacked collapsible cards, one per TC, replacing the 3-col grid (SC-1) | VERIFIED | `EndgameTypeBreakdownSection.tsx` contains no `grid-cols-3`; contains `<Accordion type="single" collapsible ...>`; test asserts `expect(section.innerHTML).not.toContain('lg:grid-cols-3')` |
| 5 | Primary TC card expanded by default; others collapsed; keyboard-accessible with data-testids (SC-2) | VERIFIED | `useState(() => computePrimaryTc(categoriesByTc, MIN_GAMES_PER_TC_CARD) ?? '')` at line 89-91; `data-testid="type-breakdown-tc-${tc}-trigger"` and `aria-label` on AccordionTrigger; 10-test `primaryTc.test.ts` suite passes |
| 6 | Each TC card shows 4-tile grid (rook/minor_piece/pawn/queen); Mixed absent; pawnless hidden (SC-3) | VERIFIED | `TILE_ORDER = ['rook', 'minor_piece', 'pawn', 'queen']` at line 40; `filter((cls) => !HIDDEN_ENDGAME_CLASSES.has(cls) && cls !== 'mixed')` at line 92-93 in `EndgameTypeTcCard.tsx`; test asserts no Mixed tile |
| 7 | Conv/Recov gauges restored, banded against PER_CLASS_TC_GAUGE_ZONES[class][tc]; Score Gap banded per-(class x TC) (SC-4/SC-5) | VERIFIED | `PER_CLASS_TC_GAUGE_ZONES[category.endgame_class]?.[tc]` at line 141-144; `convZones` and `recovZones` derived from `classBands.conversion` / `.recovery` at lines 146-161; `[sgNeutralMin, sgNeutralMax] = classBands?.achievable_score_gap ?? [-0.04, 0.04]` at line 164; `data-testid={...-conv-gauge}` and `...-recov-gauge` present |
| 8 | Accordion resets to recomputed primary TC on any filter change (D-12) | VERIFIED | `useEffect(..., [filterKey])` at lines 94-99; `Endgames.tsx` passes `filterKey={JSON.stringify(appliedFilters)}` at line 650; test `resets expanded TC to the recomputed primary when filterKey changes` passes |
| 9 | Frontend lint/test/knip gates pass; ruff format --check passes (SC-10) | FAILED | `uv run ruff format --check app/ tests/` exits 1 with 5 files needing reformatting (pure whitespace/line-length; no logic changes) |

**Score:** 8/9 truths verified

---

### Deferred Items

None.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/endgame_zones.py` | PER_CLASS_TC_GAUGE_ZONES dict (5 classes x 4 TCs) | VERIFIED | Lines 538-618; 2 occurrences of symbol; `PER_CLASS_GAUGE_ZONES` unchanged (9 occurrences) |
| `frontend/src/generated/endgameZones.ts` | PER_CLASS_TC_GAUGE_ZONES export | VERIFIED | Line 147; drift gate `git diff --exit-code` exits 0 |
| `app/services/endgame_service.py` | `_aggregate_endgame_stats_by_tc` single-pass aggregation | VERIFIED | Defined line 776, called line 3706 (2 occurrences) |
| `app/schemas/endgames.py` | `categories_by_tc` optional field on EndgameStatsResponse | VERIFIED | Line 224: `categories_by_tc: (dict[...] | None) = None` |
| `frontend/src/types/endgames.ts` | `categories_by_tc?` optional field | VERIFIED | Line 74: `categories_by_tc?: Record<...>` |
| `frontend/src/lib/primaryTc.ts` | `computePrimaryTc` + `NOMINAL_DURATION` constants | VERIFIED | Exports both; NOMINAL_DURATION = `{bullet:60, blitz:180, rapid:600, classical:900}` |
| `frontend/src/components/charts/EndgameTypeCard.tsx` | Restored 5-element tile with Conv/Recov gauges banded per-(class x TC) | VERIFIED | PER_CLASS_TC_GAUGE_ZONES referenced 10x; PER_TYPE_GAUGE_SIZE=130; `tc` prop on interface |
| `frontend/src/components/charts/EndgameTypeTcCard.tsx` | Per-TC accordion item: full-bleed header + 4-tile divider grid | VERIFIED | AccordionItem + AccordionTrigger + AccordionContent; `bg-black/20 border-b border-border/40`; no `divide-x`/`divide-y` |
| `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` | Controlled accordion orchestrator over per-TC cards, primary expanded | VERIFIED | Contains `computePrimaryTc`, `Accordion`, `value={expandedTc}`, `setExpandedTc`, `MIN_GAMES_PER_TC_CARD`; no `lg:grid-cols-3` |
| `CHANGELOG.md` | [Unreleased] entry for Phase 98 restructure + Conv/Recov re-introduction | VERIFIED | Lines 13 and 17: "Conversion and Recovery gauges back in Endgame Type Breakdown" + "Endgame Type Breakdown restructured into collapsible per-TC cards" |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/gen_endgame_zones_ts.py` | `frontend/src/generated/endgameZones.ts` | codegen drift gate | VERIFIED | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code` exits 0 |
| `app/services/endgame_service.py query_endgame_overview` | `EndgameStatsResponse.categories_by_tc` | `_aggregate_endgame_stats_by_tc(bucket_rows)` | VERIFIED | Line 3706: `categories_by_tc = _aggregate_endgame_stats_by_tc(bucket_rows)` |
| `EndgameTypeBreakdownSection.tsx` | `stats.categories_by_tc` | prop from `Endgames.tsx` parent response | VERIFIED | `Endgames.tsx` line 649: `categoriesByTc={statsData.categories_by_tc}` |
| `EndgameTypeCard.tsx` tile | `PER_CLASS_TC_GAUGE_ZONES[class][tc]` | `colorizeGaugeZones` for gauge zones + `achievable_score_gap` for ScoreGapRow | VERIFIED | Lines 141-164 in EndgameTypeCard.tsx |
| `EndgameTypeBreakdownSection.tsx` | `computePrimaryTc` | `useEffect` reset on filter change (D-12) | VERIFIED | Lines 94-99: `useEffect(() => { setExpandedTc(computePrimaryTc(...)) }, [filterKey])` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `EndgameTypeBreakdownSection.tsx` | `categoriesByTc` | `Endgames.tsx` → `statsData.categories_by_tc` → `EndgameStatsResponse` from `/api/endgames/overview` | `_aggregate_endgame_stats_by_tc` aggregates real `bucket_rows` from DB | FLOWING |
| `EndgameTypeCard.tsx` | `category.conversion.conversion_pct`, `category.conversion.recovery_pct` | `EndgameCategoryStats` from `categories_by_tc[tc]` | Populated by `_aggregate_endgame_stats_by_tc` per-TC real accumulation | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| PER_CLASS_TC_GAUGE_ZONES 5 classes x 4 TCs | `python -c "from app.services.endgame_zones import PER_CLASS_TC_GAUGE_ZONES as z; assert set(z)=={'rook','minor_piece','pawn','queen','mixed'}; assert all(set(v)=={'bullet','blitz','rapid','classical'} for v in z.values()); assert z['queen']['classical'].recovery==(0.00,0.09)"` | exit 0 | PASS |
| Drift gate | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | exit 0 | PASS |
| Backend tests (scoped) | `uv run pytest tests/ -k "endgame_zones or endgame_service or insights" -x` | 752 passed, 3 skipped | PASS |
| D-15 invariant | `uv run pytest tests/services/test_insights_service.py::TestD15LlmPathInvariant -v` | 2 passed | PASS |
| Frontend tests | `cd frontend && npm test -- --run` | 731 passed (62 files) | PASS |
| Frontend lint | `cd frontend && npm run lint` | no issues | PASS |
| Frontend knip | `cd frontend && npm run knip` | no dead exports | PASS |
| ruff lint | `uv run ruff check app/ tests/` | All checks passed | PASS |
| ty type check | `uv run ty check app/ tests/` | All checks passed | PASS |
| ruff format check | `uv run ruff format --check app/ tests/` | **FAILED**: 5 files would be reformatted | FAIL |

---

### Probe Execution

No phase-declared probes. Not a migration/tooling phase.

---

### Requirements Coverage

Plan 98-01 and 98-02 declare `requirements: [standalone]` — no external REQUIREMENTS.md IDs to cross-reference.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/services/endgame_service.py` | 889 | Line too long for ruff formatter (dict type annotation) | Warning | CI ruff format gate fails |
| `app/schemas/endgames.py` | 224-226 | Formatting style: `| None` on separate line | Warning | CI ruff format gate fails |
| `tests/test_endgame_service.py` | 4482 etc. | Trailing spaces after inline comments (double-space alignment) | Warning | CI ruff format gate fails |
| `tests/test_endgame_zones.py` | 67 | Short-form Literal list needs one-per-line split | Warning | CI ruff format gate fails |
| `tests/services/test_insights_service.py` | 1357 etc. | Ternary formatting style | Warning | CI ruff format gate fails |

No debt markers (TBD/FIXME/XXX), no placeholder returns, no hardcoded empty data, no stubs found in phase 98 files.

**Pre-existing unrelated test failure noted:** `tests/services/test_eval_drain.py::TestPartialIndexUsed::test_partial_index_used` fails when run as part of the full suite (test ordering/DB state interaction) but passes in isolation and when the file is run alone. This file was last modified by commits `1026aa0d` and `5fae39e6`, both predating Phase 98 by multiple releases. Phase 98 does not modify `test_eval_drain.py`. This failure should be tracked separately.

---

### Human Verification Required

#### 1. Responsive staircase + divider grammar

**Test:** Open the Endgames page with a user who has games in at least 2 TCs. On desktop view, verify the four type tiles show as a 4x1 row with 3 vertical dividers. Narrow the browser to tablet width (~768px) and confirm the tiles reflow to a 2x2 grid with 1 vertical + 1 horizontal divider (not bordered boxes). Narrow further to mobile and confirm a 1x4 stack with horizontal dividers between tiles.

**Expected:** Divider grammar matches EndgameMetricsByTcCard: thin `border-border/40` rules, not card outlines or box shadows. Two gauges per tile remain readable at all breakpoints.

**Why human:** CSS visual layout and cross-breakpoint divider rendering are not reliably asserted in jsdom.

#### 2. Primary-TC default-expand with real user data

**Test:** Use or create a test account with notably more bullet games (e.g. 600) but a meaningful rapid presence (e.g. 70 games). Load the Endgames page and observe which TC card is expanded by default without touching any filter.

**Expected:** Rapid expands by default (70 x 600 = 42 000 > 600 x 60 = 36 000), not bullet. The time-weighted heuristic neutralizes bullet's volume advantage.

**Why human:** Requires real imported game distribution to validate the argmax heuristic against human perception of "primary TC."

---

### Gaps Summary

One blocking gap: 5 backend files modified by Phase 98 are not formatted to ruff's standard. All diffs are pure whitespace/line-length changes — no logic is affected. The fix is a single `uv run ruff format app/ tests/` run followed by a style commit. CI will fail on this gate.

The pre-existing `test_eval_drain.py` test ordering failure is **not** a Phase 98 regression.

---

_Verified: 2026-05-30T13:22:10Z_
_Verifier: Claude (gsd-verifier)_
