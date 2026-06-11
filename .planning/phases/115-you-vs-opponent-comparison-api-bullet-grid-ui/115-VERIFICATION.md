---
phase: 115-you-vs-opponent-comparison-api-bullet-grid-ui
verified: 2026-06-11T17:00:00Z
status: human_needed
score: 18/18 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Visual grid inspection on a running dev environment"
    expected: >
      With >= 20 analyzed games (users 28/44): 3-column desktop layout, 1-column mobile,
      6 family headers, ~15 bullet rows, inverted colors (negative delta = green/left zone),
      sign not negated in numeric labels; HelpCircle popovers show definition + sign convention
      + tempo caveat on clock tags + severity-basis caveat + generic filter line.
      Below 20 analyzed games: CTA replaces grid, Band + trend stay visible.
      Blunders-only severity filter: all 15 bullets still show zones.
      NormToggle is absent; Band reads "/ 100 moves".
      Zero-event bullets show "No events in current filter" placeholder, grid does not reflow.
    why_human: Visual layout rendering, color band display, responsive breakpoints, and
      popover prose correctness cannot be verified programmatically via grep.
  - test: "A2 data-basis pre-check (BLOCKING per plan Task 4)"
    expected: >
      Dev game_flaws is on the 2026-06-11 mate-ladder + recalibrated reversed/squandered
      threshold basis. Query dev DB for a known user's reversed/squandered distribution
      to confirm. If stale, run scripts/reclassify_positions.py before trusting visual deltas.
    why_human: Data-basis freshness cannot be verified without querying the dev database
      or running the reclassify script, and the plan marks this as a BLOCKING human pre-check.
---

# Phase 115: You-vs-Opponent Comparison API + Bullet-Grid UI Verification Report

**Phase Goal:** The Library flaw-stats panel's self-only tag-distribution zone is replaced by a you-vs-opponent comparison — an endpoint feeding a uniform bullet grid (measure + CI + benchmark "typical" zone), making flaw rates actionable by contrasting the user against their actual opponents.

**Verified:** 2026-06-11T17:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

**Design note:** The ROADMAP's original Success Criteria described a "two-CI-method" design (mean paired delta CI for count families + Wilson difference-of-proportions for proportion families). The discuss/plan phase revised this to a uniform single-method design (D-01..D-16 in 115-CONTEXT.md). FLAWCMP-02 (Wilson method) was formally VOIDED. All divergences from ROADMAP wording are intentional, documented design changes; no gaps result from them.

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1 | GET /api/library/flaw-comparison returns 15 bullets (one per metric family member) with mean per-game delta + 95% CI when analyzed_n >= 20 | VERIFIED | Route at `app/routers/library.py:169`; `_compute_bullets` returns exactly 15 bullets in registry order; 8 backend tests pass including `test_all_15_bullets` |
| 2 | Each bullet's delta = mean per-game (player_count - opp_count) / user_moves * 100 | VERIFIED | `library_service.py:927` — `delta = (player_count - opp_count) / user_moves * 100.0`; `test_ci_formula` asserts the Wald-z math independently |
| 3 | Clean games (zero game_flaws rows) contribute a zero-delta row (LEFT JOIN anchor) | VERIFIED | `library_repository.py:986-1003` — anchor subquery LEFT JOIN game_flaws; `func.count(GameFlaw.ply)` (not `func.count()`) correctly counts zero for absent rows; `test_zero_event_bullet` asserts clean games increment analyzed_n |
| 4 | below_gate=True with empty bullets when analyzed_n < 20 (FLAW_COMPARISON_GATE) | VERIFIED | `library_service.py:877` — `FLAW_COMPARISON_GATE: int = 20`; `library_service.py:1012-1018` — early return; `test_sample_gate` asserts below_gate=True and bullets==[] |
| 5 | Zero-event bullets return delta=None / ci_low=None / ci_high=None, not 0.0 (D-11) | VERIFIED | `library_service.py:934-948` — `if p_total == 0 and o_total == 0: ... delta=None`; `test_zero_event_bullet` asserts delta is None not 0.0 |
| 6 | Each bullet embeds zone_lo / zone_hi (D-05 verbatim §5 Q1/Q3) and domain (D-04) from FLAW_DELTA_ZONES; API carries bounds (D-07) | VERIFIED | `flaw_delta_zones.py:34-56` — 15 entries with exact §5 Q1/Q3 values and p05/p95 domains; `_compute_bullets` reads spec per bullet; `FlawBullet` schema includes `zone_lo`, `zone_hi`, `domain` |
| 7 | Zones are pooled-global with no per-ELO/TC request-time lookup (D-06) | VERIFIED | `flaw_delta_zones.py` is a static pure-Python module with no DB/filter params; no ELO/TC lookup anywhere in the comparison pipeline |
| 8 | user_id comes from current_active_user only; never from a request parameter (IDOR) | VERIFIED | `library.py:192-194` — `user_id=user.id` from `Depends(current_active_user)` only; no user_id query param on the route |
| 9 | Both combo bullets (hasty_miss, low_clock_miss) are present via zero-event/CI fallback machinery (FLAWCMP-04, D-12) | VERIFIED | Both in `FLAW_DELTA_ZONES` registry; `test_combos` asserts both present with correct delta when events exist and both return delta=None with zero events |
| 10 | Zone 3 tag-distribution replaced by family-grouped MiniBulletChart grid (Severity/Tempo/Phase/Opportunity/Impact/Combos) (D-01, FLAWUI-01) | VERIFIED | `FlawTagDistribution.tsx` deleted (confirmed absent); `FlawStatsPanel.tsx:149` — `<FlawComparisonGrid filters={filters} flawFilter={flawFilter} />`; FAMILIES const groups 15 bullets into 6 families |
| 11 | Grid is 3 columns on desktop (lg) and 1 column on mobile (D-03) | VERIFIED | `FlawComparisonGrid.tsx:138` — `className="grid grid-cols-1 lg:grid-cols-3 gap-2"` |
| 12 | MiniBulletChart invertColors mode paints ZONE_SUCCESS LEFT, ZONE_DANGER RIGHT; sign not negated (D-08) | VERIFIED | `MiniBulletChart.tsx:135-136` — `positiveColor = invertColors ? ZONE_DANGER : ZONE_SUCCESS`; background zones inverted at lines 175/191; `FlawBulletRow` passes `invertColors` (not a negated delta); 39/39 MiniBulletChart tests pass including invertColors assertions |
| 13 | All 6 existing MiniBulletChart callers unchanged (invertColors defaults false) | VERIFIED | `MiniBulletChart.tsx:110` — `invertColors = false`; regression tests assert existing callers produce original colors |
| 14 | Each bullet has a HelpCircle popover with definition + sign convention + applicable caveats (FLAWUI-02/03, D-15) | VERIFIED | `FlawBulletPopover.tsx` implements BULLET_COPY registry for all 15 tags; `SIGN_CONVENTION` constant at line 91; `TEMPO_NOTE` for clock-conditioned tags; `SEVERITY_NOTE` (D-13) at line 101; generic filter line (D-14) at line 103 |
| 15 | Below 20 analyzed games: grid renders CTA with current count vs 20 + lichess guidance; FlawStatsBand + trend stay live (D-10) | VERIFIED | `FlawComparisonGrid.tsx:187-209` — GateCTA renders `{analyzedN} of {analyzedGate} analyzed games needed`; grid self-fetches so parent Band/trend remain unaffected; FlawComparisonGrid.test.tsx asserts CTA testid and shows "N of 20" |
| 16 | Zero-event bullets keep their row with muted placeholder, no reflow (D-11) | VERIFIED | `FlawBulletRow:83` — `min-h-[56px]` ensures stable height; `isZeroEvent` path renders "No events in current filter" placeholder; test asserts MiniBulletChart absent for zero-event bullet |
| 17 | NormToggle + per_game path deleted; FlawStatsBand fixed per-100 (D-02) | VERIFIED | `grep NormToggle/NormalizationMode frontend/src/` — empty (deleted); `FlawStatsBand.tsx:66-67` — `normDict = rates.per_100_moves`, `suffix = '/ 100 moves'` hardcoded; `FlawStatsPanel.tsx:137` — FlawStatsBand called without normalization prop |
| 18 | FlawTagDistribution.tsx deleted; knip clean (no dead exports) | VERIFIED | File absent; dead theme.ts exports (FAM_TEMPO_*, PHASE_*) removed; `npm run knip` passes clean |

**Score:** 18/18 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/flaw_delta_zones.py` | FlawDeltaZoneSpec frozen dataclass + FLAW_DELTA_ZONES Mapping (15 entries) | VERIFIED | 57 lines; `@dataclass(frozen=True)` FlawDeltaZoneSpec with zone_lo/zone_hi/domain; FLAW_DELTA_ZONES with all 15 entries in registry order, exact §5 values |
| `app/schemas/library.py` | FlawBullet + FlawComparisonResponse Pydantic models | VERIFIED | FlawBullet at line 271 (10 fields); FlawComparisonResponse at line 286 (4 fields including analyzed_gate=20 default) |
| `app/repositories/library_repository.py` | fetch_flaw_comparison per-game LEFT JOIN aggregation | VERIFIED | Async function at line 942; LEFT JOIN anchor with ply_count guard; 30 COUNT(GameFlaw.ply) FILTER columns via is_opponent_expr split; returns `list[Any]` |
| `app/services/library_service.py` | get_flaw_comparison, _compute_mean_ci, _compute_bullets, FLAW_COMPARISON_GATE=20 | VERIFIED | All 4 symbols present at lines 877, 880, 903, 967; Wald-z CI in _compute_mean_ci; zero-event detection in _compute_bullets; Sentry capture in get_flaw_comparison |
| `app/routers/library.py` | GET /flaw-comparison route | VERIFIED | `@router.get("/flaw-comparison", response_model=FlawComparisonResponse)` at line 169; same filter surface as /flaw-stats; from_date>to_date 422 guard |
| `tests/services/test_flaw_comparison.py` | 8 tests covering all FLAWCMP behaviors | VERIFIED | All 8 tests present, no skips; all 8 pass (3.61s) |
| `frontend/src/components/charts/MiniBulletChart.tsx` | invertColors?: boolean prop (default false) | VERIFIED | Prop at line 89, destructured at line 110 with `= false`; positiveColor/negativeColor pair; background zone order inverts |
| `frontend/src/types/library.ts` | FlawBullet + FlawComparisonResponse TS interfaces | VERIFIED | Both interfaces present at lines 238/261; snake_case fields matching JSON payload exactly; nullable delta/CI fields |
| `frontend/src/hooks/useLibrary.ts` | useLibraryFlawComparison hook | VERIFIED | At line 104; queryKey `['library-flaw-comparison', params]`; same LIBRARY_STALE_TIME + refetchOnWindowFocus:false as useLibraryFlawStats |
| `frontend/src/api/client.ts` | libraryApi.getFlawComparison | VERIFIED | At line 267; `apiClient.get<FlawComparisonResponse>('/library/flaw-comparison', { params })` |
| `frontend/src/components/popovers/FlawBulletPopover.tsx` | Per-bullet HelpCircle info popover | VERIFIED | 15-tag BULLET_COPY registry; HelpCircle trigger; sign convention line; tempo/exposure/severity-basis/filter caveats per D-15 |
| `frontend/src/components/library/FlawComparisonGrid.tsx` | Family-grouped bullet grid | VERIFIED | FAMILIES const with 6 families; FlawBulletRow sub-component with min-h guard; loading/error/below-gate/normal states; all data-testid + ARIA |
| `frontend/src/components/library/FlawStatsPanel.tsx` | Zone 3 = FlawComparisonGrid; NormToggle removed | VERIFIED | FlawComparisonGrid at line 149; no NormToggle/NormalizationMode/per_game references; filters + flawFilter props added |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/library.py` | `app/services/library_service.py::get_flaw_comparison` | `library_service.get_flaw_comparison(session, user_id=user.id, ...)` | WIRED | `library.py:192-205` — explicit call with user_id from auth |
| `app/services/library_service.py::get_flaw_comparison` | `app/repositories/library_repository.py::fetch_flaw_comparison` | `await library_repository.fetch_flaw_comparison(...)` | WIRED | `library_service.py:1021-1026` — await call with session + filter kwargs |
| `app/services/library_service.py::_compute_bullets` | `app/services/flaw_delta_zones.py::FLAW_DELTA_ZONES` | `for tag, spec in FLAW_DELTA_ZONES.items()` | WIRED | `library_service.py:931` — iterates registry to read zone_lo/zone_hi/domain per bullet |
| `FlawComparisonGrid.tsx` | `useLibraryFlawComparison` | `useLibraryFlawComparison(filters, flawFilter)` | WIRED | `FlawComparisonGrid.tsx:228` — hook called; data drives rendering |
| `useLibraryFlawComparison` | `/api/library/flaw-comparison` | `libraryApi.getFlawComparison(params)` | WIRED | `useLibrary.ts:111`; `client.ts:278` — `apiClient.get('/library/flaw-comparison')` |
| `FlawComparisonGrid.tsx` | `MiniBulletChart.tsx` | `<MiniBulletChart ... invertColors />` | WIRED | `FlawComparisonGrid.tsx:102-111` — FlawBulletRow renders MiniBulletChart with zone bounds from API payload + invertColors |
| `FlawStatsPanel.tsx` | `FlawComparisonGrid.tsx` | `<FlawComparisonGrid filters={filters} flawFilter={flawFilter} />` | WIRED | `FlawStatsPanel.tsx:149` — Zone 3 replaces FlawTagDistribution |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `FlawComparisonGrid.tsx` | `data` (FlawComparisonResponse) | `useLibraryFlawComparison` → `libraryApi.getFlawComparison` → `GET /api/library/flaw-comparison` | Yes — per-game LEFT JOIN DB query in `fetch_flaw_comparison` | FLOWING |
| `get_flaw_comparison` | `rows` | `fetch_flaw_comparison` → per-game GROUP BY SQL with 30 COUNT FILTER columns | Yes — SQLAlchemy query over `game_flaws` LEFT JOINed to analyzed+filtered games | FLOWING |
| `FlawBulletRow` | `bullet.delta`, `bullet.zone_lo/hi/domain` | API payload; zone bounds from `FLAW_DELTA_ZONES` embedded at service layer | Yes — delta is mean of real per-game computations; zones are static registry values | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 8 backend tests pass (all FLAWCMP truths) | `uv run pytest tests/services/test_flaw_comparison.py` | 8 passed in 3.61s | PASS |
| 48 frontend tests pass (invertColors + grid) | `npm test -- --run MiniBulletChart.test.tsx FlawComparisonGrid.test.tsx` | 48 passed | PASS |
| Backend ruff clean | `uv run ruff check app/services/flaw_delta_zones.py ... (5 files)` | All checks passed | PASS |
| Backend ty clean | `uv run ty check app/ tests/` | All checks passed | PASS |
| Frontend knip clean | `npm run knip` | No output (clean) | PASS |
| Frontend tsc clean | `npx tsc --noEmit` | No output (clean) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FLAWCMP-01 | 115-01 | Unified per-100-moves paired-delta for all 15 metrics + Wald-z CI (amended: unified estimator for all metric families, not two methods) | SATISFIED | `_compute_mean_ci` (Wald-z); delta = (player-opp)/user_moves*100 for all 15 metrics; `test_ci_formula` asserts math |
| FLAWCMP-02 | N/A | Wilson difference-of-proportions — **VOIDED** (114-CONTEXT D-04) | VOIDED | No Wilson implementation exists; voiding is documented in REQUIREMENTS.md and CONTEXT.md D-01/D-04 |
| FLAWCMP-03 | 115-01 | Full 15-bullet inventory with zone bounds + all game filters honored | SATISFIED | FLAW_DELTA_ZONES has 15 entries; route shares same filter surface as /flaw-stats; `test_filter_plumbing` verifies filter narrowing |
| FLAWCMP-04 | 115-01, 115-02 | hasty+miss and low-clock+miss combo bullets included and validated | SATISFIED | Both in registry; `test_combos` tests both zero-event and non-zero paths; both in FAMILIES Combos group in grid |
| FLAWCMP-05 | 115-01 | Section gate below floor N=20; zero-event bullets return blank/no-zone state (not zero) | SATISFIED | `FLAW_COMPARISON_GATE=20`; below-gate returns `bullets=[]`; zero-event returns `delta=None`; `test_sample_gate` + `test_zero_event_bullet` |
| FLAWUI-01 | 115-02 | Tag-distribution zone replaced by uniform bullet grid | SATISFIED | `FlawTagDistribution.tsx` deleted; `FlawComparisonGrid` at Zone 3 with 15 MiniBulletCharts |
| FLAWUI-02 | 115-02 | Per-bullet definition + sign convention + tempo-interaction caveat | SATISFIED | `FlawBulletPopover.tsx` — BULLET_COPY registry for 15 tags; `SIGN_CONVENTION` constant; `tempoNote` flags on low_clock/hasty/unrushed/hasty_miss/low_clock_miss |
| FLAWUI-03 | 115-02 | Filter×zone interaction tooltip disclosure | SATISFIED | Generic filter line in popover: "Filters change your point estimate; the typical zone may not follow your filters." (D-14 future-proof wording; no opponent-gap special-casing per D-16) |
| FLAWUI-04 | 115-02 | Bullet degrades gracefully — zone renders only when cohort stat exists | SATISFIED | `has_zone: bool = True` in schema/type (defaults True for all 15 current bullets); zero-event placeholder path ensures measure+CI path isn't blocked; forward-compat field for future zoneless bullets |
| FLAWUI-05 | 115-02 | Trend chart stays comparison-free | SATISFIED | `FlawTrendChart` unchanged; no comparison/opponent/delta props added |
| FLAWUI-06 | 115-02 | Mobile responsive + data-testid + ARIA + semantic HTML | SATISFIED | `grid-cols-1 lg:grid-cols-3`; `data-testid` on grid, gate-cta, loading, bullet-row, popover; `aria-label` on popover trigger; `aria-live` on gate CTA; `<h4>` family headers; `<Fragment key>` on map |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TBD/FIXME/XXX markers in any phase-115-modified files. No stub implementations, no hardcoded empty returns in production paths.

**Code review findings resolved (from 115-REVIEW.md):**

- WR-02 (React Fragment key): FIXED — `<Fragment key={family.name}>` confirmed at `FlawComparisonGrid.tsx:142`
- WR-03 (Sequence[str] compliance): FIXED — `get_flaw_comparison` parameters use `Sequence[str] | None` at `library_service.py:971-977`
- WR-01 (`analyzed_n` over-counts ply_count=null games in CTA gate message): DEFERRED — accepted risk per 115-REVIEW.md; imported games carry non-null ply_count in practice; pathological case is theoretical

---

### Human Verification Required

#### 1. Visual grid inspection

**Test:** With dev backend + frontend running (`bin/run_local.sh`) and logged in as a user with >= 20 analyzed games (users 28/44 per RESEARCH):
1. Open Library → Stats tab. Confirm the new grid replaces the old tag-distribution zone.
2. Desktop (lg viewport): confirm 3 columns, six family headers, ~5 rows of bullets. Mobile (375px): confirm 1 column, same families, no horizontal overflow.
3. Confirm inverted colors: a bullet where you have FEWER flaws than opponents (negative delta) sits in the green/left zone; more flaws → red/right. Numbers keep the you−opponent sign (negative = good).
4. Hover a few bullet HelpCircle popovers: confirm definition + "Negative = fewer flaws than opponents = better." + tempo caveat on clock tags + severity-basis caveat + filter line.
5. Confirm a zero-event bullet (if any) shows "No events in current filter" placeholder, not a bar, and the grid does not reflow when filters change.
6. Switch filters so analyzed games < 20: confirm the CTA ("N of 20 analyzed games needed") replaces the grid while the Band + trend chart above stay visible.
7. Confirm the per-game/per-100 toggle is gone and the Band reads "/ 100 moves".
8. Apply a blunders-only severity filter: confirm all 15 bullets still show zones (D-13), with the severity-basis caveat in the tooltip.

**Expected:** All layout, color, and copy checks described above pass.

**Why human:** Visual color rendering, responsive layout at real viewport sizes, popover prose accuracy, and filter interaction behavior cannot be verified by static code analysis.

#### 2. A2 data-basis pre-check (BLOCKING per plan Task 4)

**Test:** Query dev DB for a known user's `reversed` / `squandered` distribution to confirm the `game_flaws` table is on the 2026-06-11 mate-ladder + recalibrated `reversed`/`squandered` threshold basis. If dev `game_flaws` is stale, run `scripts/reclassify_positions.py` before trusting visual deltas.

**Expected:** Dev `game_flaws` rows for `reversed`/`squandered` reflect the updated thresholds (ES >= 68% → <= 32% for reversed; ES >= 75% → <= 59% for squandered), matching the §5 zone constants.

**Why human:** Data-basis freshness requires a live DB query and comparison against the expected threshold values from the 2026-06-09 impact recalibration.

---

### Gaps Summary

No gaps. All must-haves verified. Both code review warnings (WR-02 Fragment key, WR-03 Sequence type) were fixed before this verification. WR-01 (analyzed_n over-count) is a deferred accepted risk per the code review.

Phase goal is fully achieved in the codebase. Awaiting human visual verification (Task 4 UAT, deferred by user).

---

_Verified: 2026-06-11T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
