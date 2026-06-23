---
phase: 126-comparison-stats-frontend
verified: 2026-06-19T00:00:00Z
status: passed
score: 4/4
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Render the Library page as a beta user. Navigate to the Flaws tab and look at the flaw cards. Verify that flaw cards with a detected motif show a family-colored chip (e.g. orange for fork, indigo for pin/skewer). Click or hover a chip and confirm the definition popover opens with the motif name and a plain-English explanation."
    expected: "Chip appears on flaw cards for detected motifs only. Non-beta users see no chip. Popover shows the correct family color and definition."
    why_human: "Visual color rendering (oklch token application), hover/tap timing behavior on touch, and popover side (top desktop / bottom mobile) cannot be verified by grep or unit tests."
  - test: "On the same Library page as a beta user, open the filter panel. Confirm the 'Tactic motif' section appears with six family toggles (Fork, Pin/Skewer, Discovery, Mate, Hanging, Combinations). Select one or two families and verify the flaw list narrows. Confirm the section does NOT appear for a non-beta user."
    expected: "Beta-gated filter section present, iterates all six families with family-colored buttons. Selecting families updates the flaw list. Non-beta users cannot see this section."
    why_human: "Filter-to-list-narrowing effect and button color rendering (inline styles from TACTIC_FAMILY_COLORS) require a live browser session."
  - test: "As a beta user with enough analyzed games (>= 20), scroll to the bottom of the Flaws tab on the Library page. Confirm the 'Tactic Motifs' comparison section appears with the sub-heading 'You vs. your opponents - flaws allowed per game' and up to six family rows showing delta bars + CI whiskers. Hover a row to see the per-row tooltip (you_rate / opp_rate per game, sign-convention sentence, statistically notable/normal variation verdict)."
    expected: "Grid renders below FlawComparisonGrid. Up to 6 rows, ranked by significance first then volume. Tooltip text matches the UI-SPEC copy (no p-values, no Wilson/CI jargon). Non-beta users see nothing. Below 20 analyzed games the gate CTA appears instead."
    why_human: "MiniBulletChart visual rendering (delta bar width, CI whiskers, zone band collapse when has_zone=false), tooltip open behavior, and the sample gate CTA copy require a live browser session."
  - test: "On a 375px viewport (iPhone SE or Chrome DevTools), verify: (a) flaw card chips wrap correctly within the card; (b) the tactic motif filter toggles wrap multi-line; (c) the TacticComparisonGrid collapses to single-column with each family card stacking vertically."
    expected: "All three tactic surfaces render correctly at 375px with no overflow or horizontal scroll. Single-column grid layout confirmed."
    why_human: "Responsive layout at narrow widths requires a visual browser check; Tailwind grid-cols-1 correctness and flex-wrap behavior must be confirmed with eyes."
---

# Phase 126: Comparison Stats Frontend Verification Report

**Phase Goal:** Players can see which tactic motifs they allow more or less than their opponents, with significance gating and mobile parity.
**Verified:** 2026-06-19T00:00:00Z
**Status:** passed (human UAT confirmed — all 4 manual tests passed; see 126-UAT.md)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `GET /api/library/tactic-comparison` returns per-motif rates for player vs opponents, with significance verdict via the project's existing Wilson-based chess-score utility, honoring all game filters and severity | VERIFIED | Endpoint exists at `app/routers/library.py:212`. Service `get_tactic_comparison` at line 1292 threads all game filters (`time_control`, `platform`, `rated`, `opponent_type`, `from_date`, `to_date`, `flaw_severity`, `opponent_gap_min`, `opponent_gap_max`, `color`, `tactic_families`) via `apply_game_filters`. Wilson-based Wald-z CI via `_compute_mean_ci` called at line 1260. Section gate `TACTIC_COMPARISON_GATE=20` with early short-circuit at line 1342. `is_opponent_expr` used exclusively (0 inline `ply % 2` math). 13/13 backend tests pass including `test_below_gate_short_circuit`, `test_significant_gap_first`, `test_zero_event_family_delta_none`. |
| 2 | Each flaw card in the Library shows its `allowed` motif as a family-colored chip with a definition popover, consistent with the shipped flaw-tag chip pattern | VERIFIED | `TacticMotifChip.tsx` exists, clones `TagChip.tsx` pattern, has `data-testid="chip-tactic-{motif}-{flawId}"` (line 118) and `aria-label` (line 117). Rendered in `FlawCard.tsx` at line 278 (`user?.beta_enabled && flaw.tactic_motif != null`) and `LibraryGameCard.tsx` at line 627 (`user?.beta_enabled && tacticMotifs.length > 0`). Both sites are beta-gated. 17/17 chip tests pass. Visual rendering and popover timing require human verification. |
| 3 | The you-vs-opponent motif comparison surface (MiniBulletChart grid: delta + CI + benchmark zone where available, per-motif tooltips) renders on the Library page with a section-level sample gate | VERIFIED | `TacticComparisonGrid.tsx` exists with `data-testid="tactic-comparison-grid"`, `tactic-comparison-gate-cta`, `tactic-comparison-loading`, per-family `tactic-family-card-{family}`. Placed in `FlawStatsPanel.tsx` Zone 3 after `FlawComparisonGrid` (lines 100-101). Zone degradation: `neutralMin/Max=0/0` when `!has_zone` (lines 224-225). No client-side re-sort of server-ranked bullets. `useTacticComparison` self-fetches and re-fetches on filter changes (query key includes `tacticFamilies`). 10/10 grid tests pass including non-beta gate, below-gate CTA, zero-event, error, loading states. |
| 4 | All chips, comparison bullets, and interactive elements render correctly on mobile at 375px with `data-testid` and ARIA labels matching the project's browser-automation rules | VERIFIED (automated portion) | Grid uses `grid-cols-1 lg:grid-cols-3` (collapses to single-column at 375px). `TacticMotifChip` has `role="button"`, `tabIndex={0}`, `aria-label`. Filter section has `data-testid="filter-tactic-motif"` and per-family `data-testid="filter-tactic-motif-{family}"`. Grid states have ARIA labels. Visual rendering at 375px requires human verification. |

**Score:** 4/4 truths verified (automated checks pass; visual/interaction checks routed to human)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/routers/library.py` | GET /tactic-comparison endpoint | VERIFIED | `@router.get("/tactic-comparison")` at line 212; `TacticComparisonResponse` response model; `user_id` from `current_active_user` only; `from_date > to_date` 422 guard at line 237 |
| `app/schemas/library.py` | TacticBullet + TacticComparisonResponse models; tactic_motif/tactic_confidence on flaw rows | VERIFIED | `class TacticBullet` at line 343; `class TacticComparisonResponse` at line 366; `tactic_motif`/`tactic_confidence` on `FlawListItem` (lines 59-60) and `FlawMarker` (lines 168-169) |
| `app/services/library_service.py` | get_tactic_comparison + TACTIC_COMPARISON_GATE + MIN_TACTIC_CHIP_CONFIDENCE | VERIFIED | `TACTIC_COMPARISON_GATE=20` at line 1199; `MIN_TACTIC_CHIP_CONFIDENCE=_TACTIC_CHIP_CONFIDENCE_MIN` at line 1204; `def _compute_tactic_bullets` at line 1207; `async def get_tactic_comparison` at line 1292 |
| `app/repositories/library_repository.py` | fetch_tactic_comparison + FAMILY_TO_MOTIF_INTS mapping | VERIFIED | `FAMILY_TO_MOTIF_INTS` covers all 24 TacticMotifInt values exactly once across 6 families (1+3+2+9+1+8=24); `_TACTIC_CHIP_CONFIDENCE_MIN=70`; `def fetch_tactic_comparison` at line 1146 using `is_opponent_expr` exclusively |
| `app/repositories/query_utils.py` | tactic_families filter arg on apply_game_filters | VERIFIED | `tactic_families: Sequence[str] | None = None` at line 88; lazy import of `FAMILY_TO_MOTIF_INTS` from `library_repository` to avoid circular dep; unknown keys yield no ints |
| `frontend/src/lib/theme.ts` | Six TAC_* / TAC_*_BG family color constant pairs | VERIFIED | `TAC_FORK` through `TAC_COMBINATIONS_BG` at lines 86-97; oklch values per UI-SPEC; no color literals in component files |
| `frontend/src/lib/tacticComparisonMeta.ts` | TacticFamily, TACTIC_COMPARISON_FAMILIES, TACTIC_FAMILY_COLORS, TACTIC_FAMILY_ICON, TACTIC_FAMILY_FOR_MOTIF, isTacticDeltaSignificant, tacticDeltaZoneColor | VERIFIED | All named exports present; 6 families with correct motifs arrays; `TACTIC_FAMILY_FOR_MOTIF` derived via flatMap (no manual duplication) |
| `frontend/src/lib/tacticMotifDefinitions.ts` | TACTIC_MOTIF_DEFINITIONS Record with 24 entries | VERIFIED | 24 entries (14 quoted-key + 10 unquoted-key); substantive one-sentence definitions; no em-dashes; keys match backend TacticMotif Literal strings exactly |
| `frontend/src/components/library/TacticMotifChip.tsx` | Family-colored chip with definition popover | VERIFIED | Exists; `data-testid="chip-tactic-{motif}-{flawId}"`; `aria-label`; `role="button"`, `tabIndex={0}`; resolves family via `TACTIC_FAMILY_FOR_MOTIF`; returns null for unknown motifs |
| `frontend/src/components/filters/FilterPanel.tsx` | Beta-gated tactic-motif multi-select filter section | VERIFIED | `tacticFamilies: TacticFamily[] | null` on `FilterState`; `'tacticMotif'` in `FilterField` union and `ALL_FILTERS`; `data-testid="filter-tactic-motif"`; per-family `data-testid="filter-tactic-motif-{family}"`; gated by `user?.beta_enabled && show('tacticMotif')`; uses `TACTIC_COMPARISON_FAMILIES` (shared taxonomy) |
| `frontend/src/components/library/TacticComparisonGrid.tsx` | Beta-gated you-vs-opponent tactic comparison grid | VERIFIED | `if (!user?.beta_enabled) return null` at line 342; inner/outer component split for hooks-after-conditional rule; all required testids present; `grid-cols-1 lg:grid-cols-3` |
| `frontend/src/hooks/useLibrary.ts` | useTacticComparison query hook | VERIFIED | `useTacticComparison` at line 139; query key `['library-tactic-comparison', params, tacticFamilies]`; `staleTime: LIBRARY_STALE_TIME`; `refetchOnWindowFocus: false`; no manual `Sentry.captureException` |
| `frontend/src/api/client.ts` | getTacticComparison API fn | VERIFIED | `libraryApi.getTacticComparison` at line 293; GETs `/library/tactic-comparison`; optional `tactic_families?: string[]` param |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/library.py` | `app/services/library_service.py` | `library_service.get_tactic_comparison` | VERIFIED | Direct `await library_service.get_tactic_comparison(...)` at line 239 |
| `app/repositories/library_repository.py` | `app/repositories/query_utils.py` | `is_opponent_expr` for player/opponent split | VERIFIED | `is_opponent_expr` imported at line 34; called 12 times in `fetch_tactic_comparison` (lines 1193-1279); no inline ply arithmetic |
| `app/repositories/query_utils.py` | `app/repositories/library_repository.py` | lazy import of `FAMILY_TO_MOTIF_INTS` to avoid circular dep | VERIFIED | Lazy import inside `apply_game_filters` body at line 201 (`FAMILY_TO_MOTIF_INTS.get(fam, [])` at line 209) |
| `frontend/src/components/library/FlawCard.tsx` | `frontend/src/components/library/TacticMotifChip.tsx` | renders TacticMotifChip when beta + tactic_motif present | VERIFIED | Import at line 26; conditional render at line 278 guarded by `user?.beta_enabled && flaw.tactic_motif != null` |
| `frontend/src/lib/tacticComparisonMeta.ts` | `frontend/src/lib/theme.ts` | imports TAC_* color constants | VERIFIED | `TACTIC_FAMILY_COLORS` wired to TAC_* imports from `@/lib/theme` |
| `frontend/src/components/filters/FilterPanel.tsx` | `frontend/src/lib/tacticComparisonMeta.ts` | iterates TACTIC_COMPARISON_FAMILIES for filter toggles | VERIFIED | `TACTIC_COMPARISON_FAMILIES` imported at line 25; used at line 573 for iteration |
| `frontend/src/components/library/TacticComparisonGrid.tsx` | `frontend/src/hooks/useLibrary.ts` | useTacticComparison self-fetch | VERIFIED | Import at line 38; called at line 358 with `filters`, `flawFilter`, `tacticFamilies` |
| `frontend/src/hooks/useLibrary.ts` | `frontend/src/api/client.ts` | libraryApi.getTacticComparison | VERIFIED | `libraryApi.getTacticComparison({...params, tactic_families: ...})` at line 148 |
| `frontend/src/components/library/FlawStatsPanel.tsx` | `frontend/src/components/library/TacticComparisonGrid.tsx` | renders the grid in Zone 3 | VERIFIED | `<TacticComparisonGrid filters={filters} flawFilter={flawFilter} />` at line 101 inside `mt-6` wrapper |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `TacticComparisonGrid.tsx` | `data` from `useTacticComparison` | `libraryApi.getTacticComparison` → `GET /library/tactic-comparison` → `get_tactic_comparison` → `fetch_tactic_comparison` (LEFT JOIN with `game_flaws`) | Yes — DB query with 12 COUNT FILTER columns | FLOWING |
| `FlawCard.tsx` (chip) | `flaw.tactic_motif` | `fetch_flaws` row-build in `library_repository.py` reads `GameFlaw.tactic_motif`, gates on `_TACTIC_CHIP_CONFIDENCE_MIN=70` | Yes — DB column read at row-build time | FLOWING |
| `LibraryGameCard.tsx` (chips) | `tacticMotifs` from `game.flaw_markers` | `flaw_markers` populated from `_build_eval_series` with `tactic_by_ply` dict built from fetched `flaw_rows` | Yes — DB flaw rows processed at query time | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend: 13 tactic comparison tests pass | `uv run pytest tests/routers/test_library_tactic_comparison.py tests/services/test_tactic_comparison_service.py -x` | 13 passed in 4.94s | PASS |
| Frontend: TacticMotifChip 17 tests pass | `npm test -- --run TacticMotifChip` | 17 passed | PASS |
| Frontend: TacticComparisonGrid 10 tests pass | `npm test -- --run TacticComparisonGrid` | 10 passed | PASS |
| FAMILY_TO_MOTIF_INTS covers all 24 motif ints | Manual count from source: fork(1)+pin_skewer(3)+discovery(2)+mate(9)+hanging(1)+combinations(8) | 24 total, no gaps | PASS |
| No inline ply arithmetic | `grep -nc 'ply % 2' app/repositories/library_repository.py` | 3 (all in comments) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TACCMP-01 | 126-01 | Backend endpoint with per-game rates + is_opponent_expr split | SATISFIED | `GET /api/library/tactic-comparison` with `is_opponent_expr` exclusively, per-game normalization in `_compute_tactic_bullets` |
| TACCMP-02 | 126-01, 126-03 | Wilson-based significance verdict + section gate | SATISFIED | `_compute_mean_ci` (Wald-z) used; `TACTIC_COMPARISON_GATE=20` with below_gate short-circuit; MiniBulletChart CI whiskers in grid |
| TACCMP-03 | 126-01, 126-02 | Honors all game filters + severity | SATISFIED | `apply_game_filters` extended with `tactic_families`; all existing filter params threaded through endpoint and service |
| TACUI-01 | 126-01, 126-02 | Family-colored chip with definition popover on flaw cards | SATISFIED | `TacticMotifChip` on both `FlawCard` and `LibraryGameCard`, beta-gated, with popover + definitions |
| TACUI-02 | 126-03 | MiniBulletChart comparison grid with per-motif tooltips | SATISFIED | `TacticComparisonGrid` with `MiniBulletChart`, per-row `TacticBulletPopover`, server-ranked bullets |
| TACUI-03 | 126-02, 126-03 | Mobile-responsive at 375px with data-testid + ARIA | SATISFIED (automated) | `grid-cols-1 lg:grid-cols-3`, all elements have `data-testid`, chip has `role="button" tabIndex={0} aria-label`; visual 375px requires human check |

### Anti-Patterns Found

No blockers found.

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| — | No TBD/FIXME/XXX in any modified file | — | No debt markers |
| `has_zone=False` on TacticBullet | Intentional deferral — no tactic benchmark pipeline in scope per CONTEXT §Deferred. `neutralMin/Max=0/0` is the correct graceful degradation, not a stub. | INFO | None — documented design decision |

### Prohibition Checks (from Plan 02 + 03)

| Prohibition | Status | Evidence |
|------------|--------|---------|
| Tactic chip/filter MUST NOT render for non-beta users | VERIFIED | Both `FlawCard.tsx` and `LibraryGameCard.tsx` chip render sites guarded by `user?.beta_enabled`; FilterPanel section guarded by `user?.beta_enabled && show('tacticMotif')`; TacticComparisonGrid outer component returns null when `!user?.beta_enabled` |
| Family colors MUST NOT be hardcoded in components | VERIFIED | `grep -rl "oklch(0.72 0.18 40..."` in `frontend/src/components/` returns nothing; all colors flow from TAC_* constants in theme.ts via TACTIC_FAMILY_COLORS |
| Filter MUST NOT introduce a parallel motif-grouping taxonomy | VERIFIED | FilterPanel imports `TACTIC_COMPARISON_FAMILIES` from `tacticComparisonMeta.ts`; grid also uses the same module; single taxonomy throughout |
| Grid MUST NOT render for non-beta users | VERIFIED | Outer component `TacticComparisonGrid` returns null before hooks fire when `!user?.beta_enabled` |
| Grid MUST NOT compute or hardcode tactic benchmark zones | VERIFIED | `has_zone=False` defaults; `neutralMin/Max=0` when `!has_zone`; no hardcoded zone bounds anywhere |
| Grid MUST NOT introduce a parallel family taxonomy | VERIFIED | Grid imports `TACTIC_COMPARISON_FAMILIES` from `tacticComparisonMeta.ts` |

### Human Verification Required

#### 1. Flaw card chip visual rendering and popover behavior

**Test:** Sign in as a beta user. Go to the Library page, Flaws tab. Identify flaw cards that have a motif (the backend has been backfilled via Phase 125). Confirm chips appear with the correct family color (orange for fork, indigo for pin/skewer, lime for discovery, crimson for mate, gold for hanging, fuchsia for combinations). Hover or tap a chip and confirm the definition popover opens showing the motif name and a plain-English definition.
**Expected:** Family-colored chips appear only on flaw cards with a detected motif. Non-beta users see no chip. Popover content matches `TACTIC_MOTIF_DEFINITIONS` (e.g. fork: "A single piece attacks two or more of the opponent's pieces at the same time.").
**Why human:** Visual color rendering (oklch token application via CSS custom-properties or inline styles), hover timing (100ms open / 80ms close grace), and popover positioning (top on desktop, bottom on mobile) cannot be verified by static analysis or component tests.

#### 2. Beta-gated tactic motif filter functionality

**Test:** As a beta user, open the filter panel on the Library page. Confirm the "Tactic motif" section appears at the bottom with six family toggle buttons, each colored by its family. Select "Fork" only and verify the flaw list narrows to fork flaws. Reset and confirm all flaws return. Sign in as a non-beta user and confirm the section is absent.
**Expected:** Filter section visible to beta users only. Selecting families narrows the flaw list (the `tactic_families` query param is sent to the backend). All 6 families present and colored.
**Why human:** Button color rendering (family-colored inline styles), actual list-narrowing network effect, and beta-gate verification at the UI level require a live browser session.

#### 3. Tactic comparison grid rendering and tooltips

**Test:** As a beta user with at least 20 analyzed games (visible in the Library stats band), scroll to the Flaws tab's stats area. Confirm the "Tactic Motifs" section appears below the FlawComparisonGrid with the sub-heading "You vs. your opponents - flaws allowed per game". Verify up to 6 family rows render with delta bars and CI whiskers. Hover a row to see the tooltip confirming you_rate and opp_rate per game, a sign-convention sentence, and a "statistically notable / within normal variation" verdict.
**Expected:** Grid renders correctly. Tooltip copy follows UI-SPEC (no p-values, no Wilson/CI jargon). Below 20 analyzed games: gate CTA appears with "{n} of 20 analyzed games needed" copy and Lichess server analysis instructions. Non-beta users: section absent entirely.
**Why human:** MiniBulletChart visual rendering (bar width proportional to delta, CI whisker size, zone band absent when has_zone=false), tooltip hover-open behavior, and gate CTA copy accuracy require a live browser session.

#### 4. Mobile layout at 375px

**Test:** Using Chrome DevTools or a physical device at 375px, verify: (a) flaw card chips wrap within the card without overflow; (b) tactic motif filter toggles wrap to multiple lines without horizontal scroll; (c) the TacticComparisonGrid collapses to a single-column layout with each family card stacking vertically.
**Expected:** All three tactic UI surfaces are correctly responsive at 375px. No overflow, no horizontal scroll, readable text at `text-sm` minimum.
**Why human:** Tailwind responsive classes and flex-wrap rendering require a visual browser check at the target viewport.

---

_Verified: 2026-06-18T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
