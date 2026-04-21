# Phase 66: Frontend EndgameInsightsBlock & Beta Flag - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Requirements:** INS-01, INS-02, INS-03, BETA-01, BETA-02

<domain>
## Phase Boundary

Frontend rendering of the insights block inline on the Endgame tab for beta-flagged users, plus one Alembic migration adding a generic `users.beta_enabled` boolean column and one `UserProfileResponse` extension that surfaces the flag. Ships with:

- `frontend/src/hooks/useEndgameInsights.ts` — `useMutation` hook wrapping `POST /api/insights/endgame`; shares `buildFilterParams` with `useEndgames`.
- `frontend/src/components/insights/EndgameInsightsBlock.tsx` — self-gating top-of-tab card. Before click: hero card with "Insights" H2 + blurb + "Generate insights" button. After successful generation: overview paragraph + Regenerate button in the same slot; outdated indicator on filter changes; stale-rate-limited banner above overview; locked failure copy + Try again button on error states.
- Per-section insight slots inside the existing Endgame H2 blocks (`overall`, `metrics_elo`, `time_pressure`, `type_breakdown`) — each `SectionInsight` (headline + 0–2 bullets) renders above the existing charts in its matching H2.
- Alembic migration adding `users.beta_enabled BOOLEAN NOT NULL DEFAULT false`, no index.
- Backend schema changes: `UserProfileResponse.beta_enabled: bool` added to `app/schemas/users.py`; `/users/me/profile` handler in `app/routers/users.py` returns it; `User` SQLAlchemy model gains the column.
- Frontend type changes: `UserProfile` TS interface in `frontend/src/types/users.ts` gains `beta_enabled: boolean`.
- Requirements-doc alignment: `REQUIREMENTS.md` BETA-01 example text and `ROADMAP.md` Phase 66/67 language referencing `users.insights_beta_enabled` must be updated to `users.beta_enabled`. Phase 67 success criterion #3 is the load-bearing one.

Out of scope: the insights endpoint itself (Phase 65 — already shipped), beta flag flipping for the real cohort (Phase 67), ground-truth regression tests (Phase 67), admin-impersonation eyeball validation (Phase 67), any admin UI to manage `beta_enabled` (BETA-01 locks this as a direct DB operation).

</domain>

<decisions>
## Implementation Decisions

### Block Placement & Entry UX

- **D-01:** Interleaved per-section architecture — the insights block is NOT a single monolithic card. The overview paragraph lives in a dedicated top card at the head of the Endgame stats tab; each `SectionInsight` is slotted into its matching existing H2 section block (by `section_id → H2 heading`): `overall → Endgame Overall Performance`, `metrics_elo → Endgame Metrics and ELO`, `time_pressure → Time Pressure`, `type_breakdown → Endgame Type Breakdown`. Single API call, single Regenerate button, one findings-hash cache entry — but multiple render sites.
- **D-02:** Pre-click state: a hero card at the very top of `Endgames.tsx` statisticsContent (using the existing `charcoal-texture rounded-md p-4` pattern) contains an "Insights" H2, a 1-line blurb explaining what the feature does, and a primary "Generate insights" button. No section-level slots render anything before first click.
- **D-03:** Post-click state: the same top card renders the overview paragraph (replacing the blurb) plus a "Regenerate" button below it (still under the "Insights" H2). Each SectionInsight renders in its matching H2 *above* the existing chart cards — headline + 0–2 bullets, styled lightly (no charcoal card wrapper around the insight itself; the H2 already owns the visual grouping). Planner/UI-phase picks the exact typography and spacing.
- **D-04:** Always expanded — no per-section collapse, no whole-block dismiss. Success criterion #2 reads "renders overview paragraph ... above exactly up to 4 Section blocks"; there is no affordance to hide sections once generated. Users who don't want insights simply don't click Generate.
- **D-05:** If the LLM returns fewer than 4 sections (valid per Phase 65 D-19, `min_length=1, max_length=4`), the H2s without a matching `section_id` render exactly as today — no placeholder, no "not enough data" note, no empty shell. Conversely, if an existing H2 is suppressed today (e.g., Time Pressure when `showClockPressure && showTimePressureChart` are both false), the FE drops any matching SectionInsight for that section_id client-side — we never render a SectionInsight where its host H2 doesn't exist.
- **D-06:** Heading label: "Insights" (not "AI Insights", not "Endgame Insights"). Context is implied by the tab.

### Regenerate & Filter Invalidation (INS-03)

- **D-07:** When `appliedFilters` changes after a report is rendered, the rendered insights STAY VISIBLE. A subtle "outdated" indicator (pill/icon/text — UI phase decides exact treatment) renders near the top card to signal "filters changed; click Regenerate to update". The existing section insights remain in place until the user clicks Regenerate. Rationale: LLM latency (5–15s) and rate-limit cost (3 misses/hr) make auto-regenerate user-hostile. INS-03 says "Changing filters ... **and regenerating** produces a visibly different insight" — user-initiated by design.
- **D-08:** FE does NOT distinguish findings-affecting filters (recency, opponent_strength, time_controls, platforms) from non-affecting ones (color, rated_only). Any `appliedFilters` change (from `useFilterStore`) lights the outdated indicator. On Regenerate click, FE POSTs with the full filter context; the backend's `findings_hash`-keyed cache handles the "color/rated_only toggled but findings unchanged" case by returning `status: "cache_hit"` instantly. INS-03's "no new LLM call for color/rated_only" is a backend-enforced property (Phase 65 D-31), not a frontend property — one code path stays simpler.
- **D-09:** Hook shape = `useMutation + local component state`, mirroring `useImportTrigger` (`frontend/src/hooks/useImport.ts:24`). `mutationFn` POSTs to `/api/insights/endgame` with query-string filter params. Result stored in `EndgameInsightsBlock` component state (or lifted one level if Endgames.tsx needs access to the per-section insights — planner picks). No TanStack cache persistence keyed on filter state; navigating away and back loses the rendered report, but a re-click hits the backend cache for instant re-render. Acceptable.
- **D-10:** Button copy: "Generate insights" pre-click → "Regenerate" post-click. Clear state transition, scannable.

### Failure / Rate-Limit / Stale UI

- **D-11:** Locked failure copy (HTTP 429 `rate_limit_exceeded` with no fallback / HTTP 502 `provider_error` / HTTP 502 `validation_failure` / HTTP 503 `config_error` / network error): **"Couldn't generate insights. Please try again in a moment."** followed by a `[Try again]` Button. Replaces the overview paragraph area (section insight slots also empty — "single retry affordance ... rather than empty state or partial content" per success criterion #5). Matches the project-standard error voice used at `frontend/src/pages/Endgames.tsx:360` and `:433`.
- **D-12:** `status: "stale_rate_limited"` (HTTP 200 with a prior report served because rate-limit exhausted but tier-2 soft-fail fired): the overview renders normally inside the top card, preceded by a **muted banner** ("Showing your most recent insights. You've hit the hourly limit; try again in ~{N} min." — exact wording locked during planning). Section insights render normally too. Rationale: the user has real content to read; the banner is informational, not a failure.
- **D-13:** `stale_filters` field (returned when the prior-report filters differ from the current request) is NOT visualised on the frontend. Generic stale banner only, no filter-diff pills / no list of changed filters. The `stale_filters` field stays in the envelope for debugging / future use but FE ignores it for MVP. Low-traffic UX case; not worth the copy complexity.
- **D-14:** For HTTP 429 with `retry_after_seconds` populated, render a **static** "Try again in ~{N} min" line below the locked copy (minutes rounded from seconds, never "in a moment" when we have a number). No ticking countdown component. The `[Try again]` button remains enabled — if the user clicks it before the window elapses, the server 429s again and the same UI re-renders (cheap). Planner confirms rounding rule (suggested: `ceil(retry_after_seconds / 60)`, minimum 1).

### Beta Flag

- **D-15:** Column name is `users.beta_enabled` (feature-agnostic), NOT `users.insights_beta_enabled`. This diverges deliberately from the REQUIREMENTS.md BETA-01 example text and ROADMAP.md Phase 66/67 language, which use `insights_beta_enabled` as a placeholder. **Trade-off acknowledged:** future beta features share this single flag, so the hand-picked cohort sees all beta work together — cannot enable user A for feature X without also enabling feature Y. Acceptable for the MVP cohort model; if we ever ship per-feature beta cohorts, we'd add per-feature columns or a separate `user_beta_features` table. Planner updates REQUIREMENTS.md BETA-01 wording and ROADMAP.md Phase 66/67 references as part of the migration commit. Phase 67 success criterion #3 ("The `users.insights_beta_enabled` flag has been flipped ...") must also be rewritten.
- **D-16:** Surface to the frontend via the existing `/users/me/profile` endpoint. Extend `UserProfileResponse` (`app/schemas/users.py`) and the `UserProfile` TS interface (`frontend/src/types/users.ts`) with `beta_enabled: bool`. No new endpoint, no feature-flags dict. Single flag, single field.
- **D-17:** FE gating lives **inside** `EndgameInsightsBlock` — the component reads `useUserProfile()` and returns `null` when `profile?.beta_enabled !== true`. Also returns `null` when profile is loading (avoids flash-of-block during initial query). Endgames.tsx imports the component and slots it at the top of statisticsContent without any conditional wrapper. Keeps the feature's gating colocated with the feature's implementation; Endgames.tsx stays uncluttered. The per-section insight slots each do the same beta check (simplest way to share the condition without a context provider).
- **D-18:** Alembic migration: add column `beta_enabled BOOLEAN NOT NULL DEFAULT false` (PostgreSQL `server_default=sa.text('false')` so existing prod rows backfill to `false` on upgrade). No index — this column is only read as part of a single-row user fetch in `/users/me/profile`, never used as a WHERE filter on a scanning query. Rollback: drop column.
- **D-19:** Admin impersonation (Phase 62) naturally respects the impersonated user's flag: `ClaimAwareJWTStrategy` flips `current_active_user` to the target user, so `/users/me/profile` returns the impersonated user's `beta_enabled`. No special handling in EndgameInsightsBlock — the gating condition already reads the right value. This is the mechanism Phase 67 will use for its "5+ real user profiles eyeball validation".

### Claude's Discretion

- Exact visual treatment of the "outdated" indicator from D-07 — pill, icon, caption text, colour — UI phase or planner picks.
- Exact 1-line blurb on the pre-click hero card (D-02) and exact stale banner copy (D-12) — planner drafts; user reviews in PR.
- Exact styling of SectionInsight in-H2 slot (D-03) — typography, margin, whether to use a subtle horizontal rule above the existing charts — UI phase or planner picks.
- Loading skeleton shape while the mutation is in-flight — LLM calls take 5–15s, skeleton should be substantial (shimmer blocks sized like the expected overview + section slots). Planner picks.
- `data-testid` values for the new elements — follow CLAUDE.md §Frontend naming convention (`btn-generate-insights`, `btn-regenerate-insights`, `btn-insights-retry`, `insights-block`, `insights-overview`, `insights-section-{section_id}`, etc.). Planner finalises.
- Whether `EndgameInsightsBlock` exposes the per-section insights to Endgames.tsx via a render-prop / context / separate hook, or Endgames.tsx simply calls the mutation hook at the top level and passes each section insight to the existing chart components. Planner picks the cleanest integration.
- Whether to lift the mutation state to Endgames.tsx (if the per-section slots need read access) or keep it inside EndgameInsightsBlock and use a React context. Planner picks based on where the sections actually need to read.
- Minute-rounding rule for D-14 (`ceil(retry_after_seconds / 60)` with min 1) vs `round()` — planner picks.
- Whether the pre-click hero card is responsive to mobile differently (e.g., smaller H2, stacked button) — mobile just needs to match the existing Endgame tab mobile layout per success criterion #4.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Source Documents
- `.planning/REQUIREMENTS.md` §INS-01..INS-03, §BETA-01..BETA-02 — locked requirements for this phase. BETA-01's "e.g., `insights_beta_enabled`" example phrasing becomes `beta_enabled` per D-15; update the requirement text as part of this phase.
- `.planning/ROADMAP.md` Phase 66 entry + Phase 67 entry — Phase 66 goal and success criteria; Phase 67 success criterion #3 references `users.insights_beta_enabled` and must be rewritten to `users.beta_enabled` per D-15.
- `.planning/PROJECT.md` §"Current Milestone: v1.11 LLM-first Endgame Insights" — milestone goal. Mentions `users.insights_beta_enabled` in the feature description; language will naturally realign when Phase 66 ships.
- `.planning/seeds/SEED-003-llm-based-insights.md` §"Response schema", §"Overview design", §"Sections in Scope", §"Naming convention" (Section vs Subsection), §"Open Questions for v1.11 Discuss Phase" — resolved open questions about "rendering of null overview" (D-04: hide cleanly), "fewer than 4 sections" (D-05: render what we have), "beta flag surface" (D-17: one global flag on user row, self-gating component).
- `.planning/phases/65-llm-endpoint-with-pydantic-ai-agent/65-CONTEXT.md` — Phase 65's endpoint contract. D-14 (success envelope with `status` discriminator), D-15 (error envelope), D-16 (HTTP status mapping), D-17 (`model_used` / `prompt_version` in report — FE hides these from users by default), D-18 (overview-hide semantics: empty string = hide), D-19 (sections list 1–4), D-31 (query-param filter convention — FE reuses `buildFilterParams`), D-32 (`POST /api/insights/endgame` path).
- `.planning/phases/65-llm-endpoint-with-pydantic-ai-agent/65-VERIFICATION.md` — what actually shipped from Phase 65; confirms the envelope shapes FE consumes.

### Existing Backend (read before implementing)
- `app/schemas/users.py` — `UserProfileResponse` and `UserProfileUpdate`; extend the former with `beta_enabled: bool` per D-16.
- `app/routers/users.py:56-72` — `/users/me/profile` GET handler; add `beta_enabled=user.beta_enabled` to the returned `UserProfileResponse(...)`.
- `app/models/user.py` — `User` SQLAlchemy model; add `beta_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.text("false"), default=False)`.
- `alembic/versions/` — migration directory; new migration revision adds `users.beta_enabled`.
- `app/core/jwt_strategy.py` (Phase 62 `ClaimAwareJWTStrategy`) — reference only. No changes needed; impersonation naturally returns the impersonated user's `beta_enabled` per D-19.
- `tests/seed_fixtures.py` + `seeded_user` fixture — may need a `beta_enabled=True` variant for any beta-gated integration tests (e.g., asserting the block renders in a test that visits Endgames). Planner decides whether integration tests are in scope for Phase 66 or deferred to Phase 67.

### Existing Frontend (read before implementing)
- `frontend/src/pages/Endgames.tsx:219-383` — `statisticsContent` block and its 4 H2 groupings (`Endgame Overall Performance`, `Endgame Metrics and ELO`, `Time Pressure`, `Endgame Type Breakdown`). D-01/D-03's interleave points are these H2s. D-05's "suppressed H2" rule observes the existing `showPerfSection` / `(showClockPressure || showTimePressureChart)` / empty-categories guards.
- `frontend/src/hooks/useImport.ts:23-31` — `useImportTrigger` is the `useMutation` template for D-09.
- `frontend/src/hooks/useUserProfile.ts` — the profile query the new gating logic consumes; extend usage in `EndgameInsightsBlock`.
- `frontend/src/types/users.ts` — `UserProfile` interface; extend with `beta_enabled: boolean` per D-16.
- `frontend/src/hooks/useEndgames.ts` + its `buildFilterParams` pattern — Phase 65 D-31 says the insights endpoint shares this convention; `useEndgameInsights` reuses the same filter serialization.
- `frontend/src/hooks/useFilterStore.ts` — source of `appliedFilters` that the outdated indicator listens to (D-07).
- `frontend/src/lib/queryClient.ts` — global `MutationCache.onError` already captures mutation failures to Sentry per CLAUDE.md §Error Handling. D-11's `useMutation` inherits this behaviour; do NOT add duplicate `Sentry.captureException()` in the component.
- `frontend/src/components/ui/button.tsx` — Button component. `variant="default"` for the primary "Generate insights" and "Regenerate" (primary action per CLAUDE.md §Frontend "Primary vs secondary buttons"). `variant="brand-outline"` for the [Try again] button on failure (secondary action on an error state).
- `frontend/src/components/charts/EndgamePerformanceSection.tsx`, `EndgameScoreGapSection.tsx`, `EndgameEloTimelineSection.tsx`, `EndgameClockPressureSection.tsx`, `EndgameTimePressureSection.tsx`, `EndgameWDLChart.tsx`, `EndgameConvRecovChart.tsx`, `EndgameTimelineChart.tsx` — reference only. The per-section insight slots sit ABOVE these cards in each H2; these components themselves don't change.

### Project Conventions
- `CLAUDE.md` §Frontend — `data-testid` on every interactive element (kebab-case, component-prefixed), semantic HTML (`<button>`), ARIA labels on icon-only controls, major layout containers testid-tagged. Mobile-friendly responsive design; same changes on desktop and mobile variants.
- `CLAUDE.md` §Frontend "Primary vs secondary buttons" — `variant="default"` for Generate/Regenerate; `variant="brand-outline"` for Try again on failure.
- `CLAUDE.md` §Frontend "Theme constants in theme.ts" — any colours for the outdated indicator / stale banner / error state must import from `frontend/src/lib/theme.ts`, never inline colour hex / tailwind colour classes with semantic meaning.
- `CLAUDE.md` §Error Handling & Sentry (Frontend Rules) — TanStack global handler already captures `useMutation` failures; the FE block must NOT double-capture. Always handle `isError` in data-loading ternaries (the failure state D-11 is the `isError` branch; never fall through to "empty state").
- `CLAUDE.md` §Coding Guidelines — `Literal[...]` types on status / error fields (`status: "fresh" | "cache_hit" | "stale_rate_limited"`, `error: "rate_limit_exceeded" | ...`) in the TS API types; no magic numbers (button disabled thresholds, minute rounding, etc.); `noUncheckedIndexedAccess` compliance.
- `CLAUDE.md` §"Critical Constraints" — N/A for Phase 66 (no `asyncio.gather`, no httpx concerns — pure frontend + tiny backend migration).
- `CLAUDE.md` §"Version Control" — Phase 66 ships on a feature branch + PR.

### External References
- Phase 65 API surface: `POST /api/insights/endgame?<filter_context>` returning `EndgameInsightsResponse` (200) or `InsightsErrorResponse` (429/502/503). Already shipped — FE consumes without further backend work.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`useMutation` template** — `frontend/src/hooks/useImport.ts:24-31` (`useImportTrigger`) is the exact pattern D-09 specifies: `useMutation<ResponseShape, Error, RequestShape>` with `mutationFn` calling `apiClient.post`. Clone structure for `useEndgameInsights`.
- **`buildFilterParams` + `useEndgames`** — `frontend/src/hooks/useEndgames.ts` already serializes `FilterState` to query-string params that the `/endgames/overview` endpoint expects; Phase 65 D-31 aligned `/insights/endgame` to the same convention, so the insights hook reuses the same serializer.
- **`useUserProfile` + `/users/me/profile`** — existing 5-minute staleTime query. D-16/D-17 surface `beta_enabled` on the same response; no new query needed.
- **Existing H2 visual pattern** — `frontend/src/pages/Endgames.tsx:230,291,313,338` use `<h2 className="text-lg font-semibold text-foreground mt-2">` immediately followed by `<div className="charcoal-texture rounded-md p-4">`. The "Insights" top card reuses this pattern; the per-section SectionInsight slot sits inside the existing H2 visual group (above the first charcoal card for that H2).
- **Existing error-state copy** — `Endgames.tsx:357-362` and `:430-435` are the reference for D-11 ("Something went wrong. Please try again in a moment."). Phase 66 follows this voice with its slightly more specific "Couldn't generate insights. Please try again in a moment.".
- **`Button` component + variants** — `frontend/src/components/ui/button.tsx`. `variant="default"` for Generate/Regenerate; `variant="brand-outline"` for Try again per the primary/secondary convention.
- **`useFilterStore` + `appliedFilters`** — the source the outdated indicator (D-07) listens to. Changes to `appliedFilters` (not `pendingFilters`) signal a real commit.
- **`seeded_user` fixture + TRUNCATE session start** — Phase 61 test infrastructure; if Phase 66 adds integration tests, `beta_enabled=True` variants of `seeded_user` are the path.

### Established Patterns
- **Thin router + fat schema** (`app/routers/users.py:56-72`) — the `/users/me/profile` extension is a one-line addition to the existing `UserProfileResponse(...)` constructor.
- **FE gating by profile flag** — no precedent in this codebase; `beta_enabled` establishes the first one. D-17 keeps the check colocated in the feature component rather than introducing a generic gate abstraction.
- **`data-testid` kebab-case naming** (CLAUDE.md §Frontend) — `btn-generate-insights`, `btn-regenerate-insights`, `btn-insights-retry`, `insights-block`, `insights-overview`, `insights-section-{section_id}`. Planner finalises.
- **Deferred-apply filter flow** (`useFilterStore` + drawer close commits) — already in place; D-07 observes `appliedFilters`, not `pendingFilters`, so the outdated indicator only lights after a commit.
- **Literal types on API status/error codes** — `EndgameInsightsResponse["status"]` and `InsightsErrorResponse["error"]` become TS `Literal` unions matching Phase 65 D-14/D-15.
- **Global TanStack error capture** (`frontend/src/lib/queryClient.ts`) — all `useMutation` errors reach Sentry via the shared `MutationCache.onError`. No per-feature duplication (CLAUDE.md §Error Handling).

### Integration Points
- **`Endgames.tsx` statisticsContent** (lines 219–383): `EndgameInsightsBlock` slots at the very top of the JSX (before the first H2), and each existing H2 group gains a per-section insight slot above its first charcoal card. The exact JSX shape (whether the mutation state lives in `EndgameInsightsBlock` or is lifted to `Endgames.tsx`) is a planner call per "Claude's Discretion".
- **`UserProfileResponse` in `app/schemas/users.py`** and **`UserProfile` in `frontend/src/types/users.ts`** — both get `beta_enabled` added in lockstep. If FE and BE are PR'd separately, the FE must handle `beta_enabled` optionally (`profile?.beta_enabled === true`) during the transition.
- **Admin impersonation (Phase 62)** — `ClaimAwareJWTStrategy` already flips `current_active_user`; Phase 66 does nothing special. Phase 67 will consume this for its 5+ real-user eyeball validation.
- **Requirements-doc rename** — `REQUIREMENTS.md` BETA-01 and `ROADMAP.md` Phase 66 / Phase 67 references to `insights_beta_enabled` → `beta_enabled` are edited in the same commit as the Alembic migration, so prose and schema stay in sync.

</code_context>

<specifics>
## Specific Ideas

- **`useEndgameInsights` hook sketch** (planner finalises):
  ```typescript
  // frontend/src/hooks/useEndgameInsights.ts
  import { useMutation } from '@tanstack/react-query';
  import { apiClient } from '@/api/client';
  import { buildFilterParams } from './useEndgames';
  import type { FilterState } from '@/components/filters/FilterPanel';
  import type { EndgameInsightsResponse, InsightsErrorResponse } from '@/types/insights';

  export function useEndgameInsights() {
    return useMutation<EndgameInsightsResponse, AxiosError<InsightsErrorResponse>, FilterState>({
      mutationFn: async (filters) => {
        const params = buildFilterParams(filters);
        const res = await apiClient.post<EndgameInsightsResponse>(
          '/insights/endgame',
          null,
          { params }
        );
        return res.data;
      },
    });
  }
  ```

- **`EndgameInsightsBlock` self-gating sketch** (planner finalises):
  ```tsx
  // frontend/src/components/insights/EndgameInsightsBlock.tsx
  export function EndgameInsightsBlock({ appliedFilters, onReportChange }: Props) {
    const { data: profile } = useUserProfile();
    if (!profile?.beta_enabled) return null;

    const mutation = useEndgameInsights();
    const [rendered, setRendered] = useState<EndgameInsightsResponse | null>(null);
    const [reportFilters, setReportFilters] = useState<FilterState | null>(null);
    const isOutdated = rendered && reportFilters && !areFiltersEqual(reportFilters, appliedFilters, FILTER_FIELDS);

    const handleGenerate = async () => {
      const result = await mutation.mutateAsync(appliedFilters);
      setRendered(result);
      setReportFilters(appliedFilters);
      onReportChange?.(result.report);  // lift section insights up if needed
    };

    // Render hero card (pre-click) | overview + Regenerate + outdated pill (post-click) | locked failure copy + [Try again] (error)
  }
  ```

- **`UserProfileResponse` extension**:
  ```python
  # app/schemas/users.py
  class UserProfileResponse(BaseModel):
      # ... existing fields ...
      beta_enabled: bool
  ```

- **`User` model extension**:
  ```python
  # app/models/user.py
  class User(SQLAlchemyBaseUserTable[int], Base):
      # ... existing fields ...
      beta_enabled: Mapped[bool] = mapped_column(
          Boolean,
          nullable=False,
          server_default=sa.text("false"),
          default=False,
      )
  ```

- **Alembic migration body** (planner finalises):
  ```python
  def upgrade() -> None:
      op.add_column(
          "users",
          sa.Column("beta_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
      )

  def downgrade() -> None:
      op.drop_column("users", "beta_enabled")
  ```

- **Locked failure copy string** (render exactly, no interpolation):
  ```
  Couldn't generate insights. Please try again in a moment.
  ```
  With `[Try again]` Button below. For HTTP 429 specifically, append a second line:
  ```
  Try again in ~{N} min.
  ```
  where `N = max(1, Math.ceil(retry_after_seconds / 60))`.

- **Stale-rate-limited banner copy** (muted style, above the overview):
  ```
  Showing your most recent insights. You've hit the hourly limit; try again in ~{N} min.
  ```
  Planner/UI-phase picks exact muted styling; `N` rounded the same way as the failure case.

</specifics>

<deferred>
## Deferred Ideas

- **LocalStorage / sessionStorage persistence** of the last rendered insights report across page reloads — not in MVP. Backend cache-hit on re-POST is fast enough that reloading feels free. Revisit if users report losing context too often.
- **Admin UI for flipping `beta_enabled`** — BETA-01 explicitly locks this as direct DB ops only ("the whole point is a small, hand-picked validation cohort"). If a self-serve or admin surface is ever needed, that's a separate phase.
- **Per-feature beta columns / `user_beta_features` table** — D-15's generic `beta_enabled` couples all beta features. If/when per-feature cohorts become necessary, revisit. Not an MVP concern.
- **Live ticking countdown on 429** — D-14 uses static rounded minutes. Live countdown is a UX polish if users report confusion; adds a timer component.
- **Filter-diff visualization on `stale_rate_limited`** (D-13) — shipping as generic banner only. Revisit if the stale state is hit frequently enough that users want to know what changed.
- **Display of `model_used` / `prompt_version`** to regular users — hidden from UI per Phase 65 D-17 (debug-only). Accessible via DevTools response inspection. If a dev-toggle is ever added, it's a separate `/gsd-quick`.
- **Per-section streaming responses** — Phase 65 D-40's deferred idea; Phase 66 doesn't preempt. MVP renders the single response when the mutation resolves.
- **Info-popover on the insights block** explaining how the feature works / privacy implications — default no. Can add during UI phase if desired.
- **Scroll-into-view anchor** after Generate click — probably unnecessary since the block is already at the top of the tab. If the user scrolled past it and clicked Regenerate, no scroll hijack. Planner decides.
- **Typed TS discriminated union helpers** for `EndgameInsightsResponse.status` — planner picks level of type narrowing ceremony in the hook's return shape.
- **Integration-test coverage** with `beta_enabled=True` `seeded_user` variant — scope unclear; planner decides whether Phase 66 ships with tests or defers to Phase 67's ground-truth and eyeball validation. Likely: a small FE render test + one backend router test for `/users/me/profile` returning `beta_enabled`.

</deferred>

---

*Phase: 66-frontend-endgameinsightsblock-beta-flag*
*Context gathered: 2026-04-21*
