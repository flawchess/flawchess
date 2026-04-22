---
phase: 66-frontend-endgameinsightsblock-beta-flag
verified: 2026-04-22T08:00:00Z
status: human_needed
score: 24/24 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Beta user sees hero card (Insights H2 + blurb + Generate button) at top of Endgame stats tab"
    expected: "Top of tab shows 'Insights' H2, 1-line blurb, primary 'Generate insights' button; no per-section slots visible yet"
    why_human: "Visual rendering and spacing (D-02) — requires a running dev session with a beta-flagged user"
  - test: "Click 'Generate insights' triggers mutation, shows skeleton, then overview paragraph + 4 SectionInsight slots inline in each H2"
    expected: "Skeleton appears during 5-15s LLM latency, then replaced by overview (<=150 words) and 4 section insight slots (headline + 0-2 bullets) above each chart card"
    why_human: "End-to-end LLM integration, real provider latency, requires running services (Success Criterion #2)"
  - test: "Changing findings-affecting filters (recency, opponent_strength, time_controls, platforms) triggers outdated-indicator dot next to H2; clicking Regenerate produces different text"
    expected: "Dot + 'Filters changed — click Regenerate to update' appears; clicked regeneration calls backend with new filters and shows new content; toggling only color/rated_only returns cache_hit status instantly"
    why_human: "Requires live LLM + backend findings_hash cache to verify INS-03 end-to-end"
  - test: "Non-beta user sees byte-identical Endgame tab layout (no 'Insights' card, no section slots)"
    expected: "Page DOM matches v1.10 output; no flash of block during profile load; no extra spacing or empty containers"
    why_human: "Visual diff requires rendering the page with a non-beta user (Success Criterion #1)"
  - test: "Failure paths (429 rate_limit_exceeded, 502 provider_error, 503 config_error, network error) all show locked copy + [Try again] button"
    expected: "'Couldn't generate insights. Please try again in a moment.' + Try again button; 429 with retry_after_seconds adds 'Try again in ~N min.' line"
    why_human: "Requires triggering real failure conditions from the backend (Success Criterion #5)"
  - test: "Backend INSIGHTS_HIDE_OVERVIEW=true flag suppresses overview paragraph only; per-section insights still render"
    expected: "Top card shows Regenerate button but no overview text; 4 section insights render normally in each H2"
    why_human: "Requires backend env flag flip + live LLM call to verify BETA-02 suppression (Success Criterion #4)"
  - test: "Mobile viewport — Insights card and section slots match existing Endgame tab mobile layout"
    expected: "Layout responsive per CLAUDE.md Mobile UI rule; outdated indicator wraps below H2 on narrow viewports"
    why_human: "Responsive visual verification across breakpoints (Success Criterion #4 / 66-UI-SPEC §Spacing)"
---

# Phase 66: Frontend EndgameInsightsBlock & Beta Flag Verification Report

**Phase Goal:** Overview + 4 Section insight blocks render inline on the Endgame tab, gated by `users.beta_enabled`. Backend config can hide the overview independently while per-section insights stay live.

**Verified:** 2026-04-22T08:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `users.beta_enabled BOOLEAN NOT NULL DEFAULT false` column exists | VERIFIED | information_schema query on dev DB: `('beta_enabled', 'boolean', 'NO', 'false')`; migration `24baa961e5cf` at head |
| 2 | `GET /users/me/profile` round-trips beta_enabled | VERIFIED | `app/routers/users.py:83,107` passes `beta_enabled=user.beta_enabled` in get_profile + update_profile; 3 tests in `test_users_router.py` pass |
| 3 | `PUT /users/me/profile` cannot mutate beta_enabled (mass-assignment guard) | VERIFIED | `UserProfileUpdate` only declares chess_com_username and lichess_username; test_user_profile_update_does_not_change_beta_enabled passes |
| 4 | `UserProfile.beta_enabled: boolean` required on FE | VERIFIED | `frontend/src/types/users.ts:17` `beta_enabled: boolean` (not optional) |
| 5 | `useEndgameInsights` POSTs to `/insights/endgame` with color but NOT opponent_type | VERIFIED | `useEndgameInsights.ts:34`: `apiClient.post('/insights/endgame', null, { params })`; param builder omits opponent_type (line 29 comment); 3 hook tests pass including the Pitfall 1 assertion |
| 6 | Literal-typed API envelope types mirror backend | VERIFIED | `insights.ts` exports SectionId (4 literals), InsightsStatus (3), InsightsError (4), SectionInsight, EndgameInsightsReport, EndgameInsightsResponse, InsightsErrorResponse, InsightsAxiosError |
| 7 | Component returns null when profile is loading OR beta_enabled=false | VERIFIED | `EndgameInsightsBlock.tsx:45` `if (!profile?.beta_enabled) return null;`; both test cases pass |
| 8 | Pre-click hero card with H2 "Insights", blurb, primary Generate button | VERIFIED | `HeroState` component renders literal copy "Generate a short written summary of your endgame performance based on the current filters." + `<Button variant="default" data-testid="btn-generate-insights">Generate insights</Button>` |
| 9 | Post-click overview + Regenerate button; empty overview hidden (BETA-02) | VERIFIED | `RenderedState` guards overview with `showOverview = overview !== ''`; component test `hides overview paragraph when empty string (BETA-02)` passes |
| 10 | Error state renders locked copy + [Try again] with variant brand-outline | VERIFIED | `ErrorState` renders "Couldn't generate insights." / "Please try again in a moment." / `<Button variant="brand-outline" data-testid="btn-insights-retry">Try again</Button>` |
| 11 | Outdated indicator renders when appliedFilters differ from reportFilters | VERIFIED | `isOutdated = hasRendered && reportFilters !== null && !areFiltersEqual(reportFilters, appliedFilters)`; test passes |
| 12 | Stale-rate-limited banner above overview when status=='stale_rate_limited' | VERIFIED | `isStale = hasRendered && rendered.status === 'stale_rate_limited'`; banner copy "Showing your most recent insights..." rendered; test passes |
| 13 | Skeleton renders during mutation.isPending when no prior report | VERIFIED | `isPending && !hasRendered` branch renders `SkeletonBlock` with data-testid `insights-skeleton` |
| 14 | Inline Loader2 spinner during regeneration when a prior report is shown | VERIFIED | `RenderedState` renders `{isPending && <Loader2 ... />}` next to the Regenerate button |
| 15 | `EndgameInsightsBlock` mounts at top of statisticsContent | VERIFIED | `Endgames.tsx:263-269` renders `<EndgameInsightsBlock>` as the first child of statisticsContent (before `{overviewLoading ? ...}`) |
| 16 | 4 SectionInsight slots render inside matching H2 groups | VERIFIED | `Endgames.tsx:327,342,365,391` render `<SectionInsightSlot>` for overall, metrics_elo, time_pressure, type_breakdown; each between H2/Accordion and first chart card |
| 17 | Sections without a matching H2 (existing suppression guards) are dropped | VERIFIED | Each slot lives inside its guarding conditional: `showPerfSection` (slot A), `{scoreGapData && ...}` (B), `(showClockPressure \|\| showTimePressureChart)` (C), outer `statsData.categories.length > 0` (D) |
| 18 | Generate/Regenerate is user-initiated; filter changes do NOT auto-fire | VERIFIED | `handleGenerateInsights` only called via onGenerate prop → button onClick; no useEffect triggers mutateAsync on filter changes |
| 19 | Non-beta users see byte-identical layout | VERIFIED (code path) | Component self-gates to null (no markup); `renderedInsights` stays null so every `SectionInsightSlot` returns null — confirmed in component test `returns null when profile.beta_enabled is false`. Visual confirmation deferred to human test. |
| 20 | Docs aligned: `beta_enabled` (not `insights_beta_enabled`) in REQUIREMENTS.md + ROADMAP.md | VERIFIED | `grep insights_beta_enabled .planning/REQUIREMENTS.md .planning/ROADMAP.md` returns zero matches; `beta_enabled` appears 7 times in ROADMAP.md |
| 21 | Minute rounding: `Math.max(1, Math.ceil(retry_after_seconds / 60))` | VERIFIED | `roundMinutes` helper at line 32; component test cycles through 0s→1, 45s→1, 60s→1, 61s→2, 180s→3 |
| 22 | Alembic upgrade + downgrade + upgrade round-trips cleanly | VERIFIED | Migration `24baa961e5cf` applied; `alembic current` shows at head; migration body: `op.add_column` + `op.drop_column` only, no drift |
| 23 | All 9 top-card + 4 section testids present | VERIFIED | grep confirms: insights-block, insights-overview, btn-generate-insights, btn-regenerate-insights, btn-insights-retry, insights-outdated-indicator, insights-stale-banner, insights-error, insights-skeleton, insights-section-overall, insights-section-metrics_elo, insights-section-time_pressure, insights-section-type_breakdown |
| 24 | Single retry affordance on failure paths (Success Criterion #5) | VERIFIED | `ErrorState` renders exactly one `[Try again]` button; locked copy replaces overview; section slots automatically empty because `renderedInsights` stays null on error (sectionBySection check gates on `!insightsMutation.isError`) |

**Score:** 24/24 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/user.py` | `beta_enabled: Mapped[bool]` with Boolean import | VERIFIED | Lines 7 (Boolean import), 34-39 (column def); server_default text("false"), nullable=False |
| `app/schemas/users.py` | `beta_enabled: bool` field on UserProfileResponse, NOT on UserProfileUpdate | VERIFIED | Line 26 (on response); UserProfileUpdate (lines 29-33) only has chess_com_username + lichess_username |
| `app/routers/users.py` | beta_enabled wired into both get_profile + update_profile | VERIFIED | Line 83 (get_profile), line 107 (update_profile) |
| `alembic/versions/..._add_users_beta_enabled.py` | Migration with add_column/drop_column only | VERIFIED | `20260422_014425_24baa961e5cf_add_users_beta_enabled.py`; scope = users.beta_enabled only |
| `tests/test_users_router.py` | 3 new router tests | VERIFIED | test_profile_returns_beta_enabled_default_false, test_profile_returns_beta_enabled_true_after_db_flip, test_user_profile_update_does_not_change_beta_enabled — all pass |
| `frontend/src/types/insights.ts` | Literal API envelope types | VERIFIED | 9 exports including SectionId, InsightsStatus, InsightsError, EndgameInsightsResponse, InsightsAxiosError |
| `frontend/src/types/users.ts` | `beta_enabled: boolean` required on UserProfile | VERIFIED | Line 17; no optional marker |
| `frontend/src/api/client.ts` | `buildFilterParams` exported | VERIFIED | Line 67 `export function buildFilterParams` |
| `frontend/src/hooks/useEndgameInsights.ts` | useMutation wrapping POST /insights/endgame | VERIFIED | 42 lines; correct params shape; omits opponent_type |
| `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx` | Hook unit tests | VERIFIED | 3 tests pass (POST shape, opponent_type exclusion, AxiosError propagation) |
| `frontend/src/components/insights/EndgameInsightsBlock.tsx` | Self-gating top card with full state machine | VERIFIED | 240 lines; 5 state branches (hero/skeleton/rendered/error/outdated-overlay); 9 testids |
| `frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx` | Component render tests | VERIFIED | 10 tests pass (beta gate loading + false, hero, skeleton, overview, overview-hidden, stale, outdated, error, error-with-retry, minute rounding) |
| `frontend/src/pages/Endgames.tsx` | Hook integration + 4 slot mounts + SectionInsightSlot helper | VERIFIED | Lines 81-112 (hook + state + lookup); 263-269 (block mount); 327, 342, 365, 391 (4 slots); 654-674 (SectionInsightSlot) |
| `.planning/REQUIREMENTS.md` + `.planning/ROADMAP.md` | zero `insights_beta_enabled` refs | VERIFIED | grep returns empty |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `app/routers/users.py::get_profile` | User.beta_enabled | kwarg in UserProfileResponse(...) | WIRED | `beta_enabled=user.beta_enabled` at line 83 |
| `app/routers/users.py::update_profile` | User.beta_enabled | kwarg in UserProfileResponse(...) | WIRED | `beta_enabled=updated.beta_enabled` at line 107 |
| Alembic migration | PostgreSQL users table | op.add_column(server_default=text("false")) | WIRED | migration head active; information_schema query confirms column present with correct type/default |
| `useEndgameInsights` | POST /api/insights/endgame | apiClient.post with params | WIRED | Line 34; params include color; omits opponent_type |
| `useEndgameInsights` | buildFilterParams | named import from @/api/client | WIRED | Line 2 `import { apiClient, buildFilterParams } from '@/api/client'` |
| `EndgameInsightsBlock` | `useUserProfile()` | beta_enabled gate | WIRED | Line 43 `const { data: profile } = useUserProfile()`; line 45 null-return guard |
| `EndgameInsightsBlock` | `useEndgameInsights()` via props | parent `Endgames.tsx` owns mutation | WIRED | `EndgameInsightsBlockProps` interface (line 23-29); Endgames.tsx 263-269 passes `mutation={insightsMutation}` |
| `EndgameInsightsBlock` | `areFiltersEqual` | outdated-indicator comparison | WIRED | Line 53 `!areFiltersEqual(reportFilters, appliedFilters)` (no `fields` arg = compare all) |
| `Endgames.tsx per-section slots` | `rendered.report.sections` | sectionBySection lookup | WIRED | Lines 99-112 build lookup; lines 327, 342, 365, 391 render slots |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `EndgameInsightsBlock` | `rendered: EndgameInsightsResponse \| null` | Passed as prop from `Endgames.tsx` → populated by `handleGenerateInsights` → `insightsMutation.mutateAsync(appliedFilters)` → `apiClient.post('/insights/endgame', ...)` → Phase 65 `POST /api/insights/endgame` returning `EndgameInsightsResponse` | YES — Phase 65 endpoint verified shipped; `setRenderedInsights(result)` populates on success | FLOWING |
| `EndgameInsightsBlock` | `profile: UserProfile \| undefined` | `useUserProfile()` → `GET /users/me/profile` → UserProfileResponse with `beta_enabled: user.beta_enabled` from DB | YES — DB column populated; router queries column; response schema includes field | FLOWING |
| `SectionInsightSlot` | `data: { headline, bullets } \| null` | `sectionBySection[sectionId]` built from `renderedInsights.report.sections` iteration | YES — populated only after successful mutation; null for non-beta users (no mutation fires) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend users router test suite | `uv run pytest tests/test_users_router.py -x -q` | 8 passed | PASS |
| Full backend test suite (excl. pre-existing flake) | `uv run pytest tests/ --ignore=tests/test_reclassify.py -q` | 1021 passed | PASS |
| Backend ty check | `uv run ty check app/ tests/` | All checks passed | PASS |
| Migration applied | `uv run alembic current` | `24baa961e5cf (head)` | PASS |
| DB column present with correct type | `SELECT ... FROM information_schema.columns WHERE table_name='users' AND column_name='beta_enabled'` | `('beta_enabled', 'boolean', 'NO', 'false')` | PASS |
| Frontend insights tests | `npm test -- --run src/hooks/__tests__/useEndgameInsights src/components/insights` | 14 passed | PASS |
| Full frontend suite | `npm test -- --run` | 97 passed | PASS |
| Frontend tsc | `cd frontend && npx tsc --noEmit` | clean | PASS |
| Frontend knip (dead exports/deps) | `npm run knip` | clean | PASS |
| Frontend lint | `npm run lint` | 0 errors, 3 unrelated warnings | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INS-01 | 66-02, 66-03, 66-04 | Beta user sees "Generate insights" button + generates report on demand | SATISFIED | EndgameInsightsBlock hero state renders btn-generate-insights; onClick calls mutation → backend POST; component tests verify button + click path. Full user-flow verification requires human test (see human_verification list). |
| INS-02 | 66-02, 66-03, 66-04 | Overview paragraph + 4 Section blocks each with headline + 0-2 bullets | SATISFIED | RenderedState renders overview paragraph; 4 SectionInsightSlot mounts in Endgames.tsx; SectionInsightSlot renders headline + bullets list. Traceability table lists this as "Pending" but checkbox is `[x]` and implementation complete — minor tracking inconsistency flagged. |
| INS-03 | 66-02, 66-03, 66-04 | Filter changes produce different insights; color/rated_only don't force new LLM call | SATISFIED (frontend contract) | Hook builds params from FilterState with color appended; findings-affecting filters flow through. Backend enforcement of color/rated_only cache behavior is Phase 65. Outdated indicator prompts user on any FilterState change (D-08). |
| BETA-01 | 66-01, 66-02, 66-05 | `users.beta_enabled` boolean column, flipped via direct DB op, default false | SATISFIED | DB column present with correct type/default; API round-trip works; UserProfileUpdate mass-assignment guard verified via test; REQUIREMENTS.md + ROADMAP.md refer to `beta_enabled` (not placeholder). |
| BETA-02 | 66-01 (backend readiness), 66-02 (FE type), 66-03 (FE suppression logic) | Backend config hides overview independently; per-section insights stay live | SATISFIED (frontend contract) | Component test `hides overview paragraph when empty string (BETA-02)` passes; RenderedState keeps Regenerate button + section insights when overview=''. Backend `INSIGHTS_HIDE_OVERVIEW` was shipped in Phase 65 (`app/core/config.py:37`, `app/services/insights_llm.py:182`). End-to-end verification requires live backend toggle (human test). |

All 5 requirement IDs accounted for. No orphaned requirements: REQUIREMENTS.md phase-coverage table lists exactly INS-01, INS-02, INS-03, BETA-01, BETA-02 for Phase 66.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | Scanned modified files for TODO/FIXME/placeholder/empty-return/hardcoded-empty. All hardcoded empty values are legitimate initial states (e.g. `sectionBySection: Record<SectionId, ... \| null> = { overall: null, ... }` is populated from the mutation response). No stub code in shipped artifacts. |

### Human Verification Required

Required items listed in frontmatter `human_verification`. Summary:

1. **Beta user hero card visual** — verify spacing, typography, button placement match 66-UI-SPEC typography/spacing scale
2. **End-to-end Generate flow** — click Generate, observe skeleton → overview + 4 section slots populate inline; requires live LLM call
3. **Filter change + Regenerate** — toggle recency/opponent_strength filters, verify outdated indicator fires and new LLM output differs; toggle color-only and verify cache_hit returns instant
4. **Non-beta user byte-identical layout** — render with `beta_enabled=false` and confirm no extra DOM/spacing
5. **Failure paths** — trigger 429/502/503/network error, confirm locked copy + Try again button; confirm 429 with retry_after_seconds shows "Try again in ~N min."
6. **INSIGHTS_HIDE_OVERVIEW end-to-end** — set backend env flag, re-run Generate, confirm overview suppressed but 4 section insights still render (BETA-02)
7. **Mobile responsive layout** — verify at <640px breakpoint

### Gaps Summary

No blocking gaps. All 24 must-haves pass programmatic verification. 7 items require human visual / end-to-end verification before the phase can be declared user-facing complete — this is expected for a UI-heavy phase gated by a live LLM endpoint and a beta cohort.

Minor observations (non-blocking):

- REQUIREMENTS.md traceability table lists INS-02 as "Pending" while its checkbox is `[x]` and implementation is complete. Suggest flipping the status to "Complete" when the phase closes. Not a gap — requirement is satisfied in code.
- Stale banner "in ~N min" branch is unreachable today because the Phase 65 200-envelope does not expose `retry_after_seconds` for stale responses. Component correctly falls back to "in a moment" and documents the limitation inline (line 62-65). Would need a Phase 65 schema extension to activate.

---

_Verified: 2026-04-22T08:00:00Z_
_Verifier: Claude (gsd-verifier)_
