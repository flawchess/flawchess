# Phase 118: Demand UX + Auto-Enqueue - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the *user-facing triggers and surfaces* on top of the Phase 117 priority queue so
full-game analysis happens automatically and visibly, without the user initiating or
babysitting it.

In scope:
- Automatic tier-2 window enqueue on import completion and on user activity (QUEUE-04).
- Explicit "analyze more" affordances: a per-game tier-1 button and a bulk tier-2 button,
  both with progress (EVUX-01).
- Coverage indicators ("N of M analyzed") + low-coverage CTA on the Library flaw surfaces
  (EVUX-02).
- In-flight (queued/analyzing) status without blind refresh (EVUX-03).
- Guest account-promotion as the unlock face of QUEUE-08 (ROADMAP criterion 5).

NOT in this phase:
- The engine, queue, lease/report contract, tiers, PV/best_move capture, and flaw
  flow-through — all built in Phases 116/117. 118 only adds triggers + UX.
- The engine-best-move step-through display / board-arrow viewer. D-117-01 mentions it as
  "Phase 118," but the ROADMAP-118 success criteria do **not** list it. Treated as out of
  scope here (ROADMAP is authoritative) — see Deferred. Flag if the planner disagrees.
- A separate PV/best_move coverage indicator (deferred to the SEED-039 PV-consuming surface).

Requirements: QUEUE-04, EVUX-01, EVUX-02, EVUX-03 (+ ROADMAP-118 criterion 5).

Terminology lock (confirmed with user): **bulk "Analyze more" = tier-2** (the ~200-game
batch lane, aggregate progress); **single per-game click = tier-1** (whole-pool fan-out,
~10s, localized progress).
</domain>

<decisions>
## Implementation Decisions

### Auto-enqueue triggers & window (QUEUE-04)
- **D-118-01 — Two triggers, both backend-only.** (a) Import completion enqueues the
  user's tier-2 window. (b) The window enqueue is **hooked into the existing
  `last_activity` middleware write** (`app/middleware/last_activity.py`), which is already
  throttled to ≤1 write/hour per authenticated user — a built-in debounce that fires on
  real activity with no new scheduler and no frontend coupling. Rejected: frontend
  "lazy on page load" trigger; standalone periodic sweep.
- **D-118-02 — Window = 200 most recent unanalyzed games**, matching the ROADMAP "~200"
  criterion (w200 ≈ 0.9-day catch-up at 6 workers, spike-003). Extract as a single named
  constant so prod soak can retune without an API/schema change.
- **D-118-03 — Tier-2 window targets only games that genuinely NEED evals:**
  `full_evals_completed_at IS NULL AND lichess_evals_at IS NULL` (chess.com + unanalyzed
  lichess). Lichess games with imported %evals are already `is_analyzed` (D-117-09) and
  would gain only PV/best_move — **no coverage value now**, so they are NOT enqueued in
  tier-2. (User directive, refines D-117-12's "auto-window re-touches recent games.")
- **D-118-04 — Tier-3 ordering refinements (in scope this phase):** add to
  `_claim_tier3_derived` ORDER BY (1) **active-users-first** via `users.last_activity DESC`
  (the D-4 intent 117 left as "best-effort global") and (2) **needs-eval before
  PV-backfill-only** — push `lichess_evals_at IS NOT NULL` games last, behind the existing
  TC-weight + recency terms. (User directive.)
- Enqueue is idempotent: skip games already pending/leased/completed (no duplicate
  `eval_jobs` rows).

### Analyze affordances (EVUX-01)
- **D-118-05 — Ship BOTH affordances.** Per-game tier-1 "Analyze this game" (whole-pool
  fan-out ~10s, lichess-review feel — the QUEUE-03 user trigger D-117-05 deferred to 118)
  AND a bulk "Analyze more" tier-2 button.
- **D-118-06 — Bulk "Analyze more" = next-chunk, disabled-until-drained.** Enqueues the
  next ~200 needs-eval games (D-118-03 predicate) into tier-2. **Disabled while the user
  has any tier-2 job in-flight** (pending/leased), showing "Analyzing your recent games…
  N of M"; re-enabled when the user's tier-2 window drains. Repeatable. Rationale: the
  pool is fixed-throughput — a button only reorders, never accelerates — so piling more
  into a still-draining tier-2 is meaningless and must be prevented. Rejected:
  always-on incremental; filter-scoped batch; "all remaining" one-shot.
- **D-118-07 — Lichess-eval games are excluded from tier-1 too; the per-game button is
  hidden for them.** (User decision, 2026-06-14 — reverses the earlier flagged assumption.)
  A game already analyzed via imported lichess %evals (`lichess_evals_at IS NOT NULL`,
  hence `is_analyzed`) shows **no "Analyze this game" button** — it is already analyzed, and
  the only thing re-analysis would add (best_move/PV) is not needed until the SEED-039
  surface ships. Those games get best_move/PV **backfilled in the background over time**,
  not on demand — concretely via the tier-3 idle drain, which D-118-04 already orders them
  last in. Net per-game button visibility rule: **guest → sign-up CTA (D-118-13); else
  not-`is_analyzed` → "Analyze this game" (tier-1); else (analyzed, incl. lichess-eval) →
  no affordance.** This reverses D-117-12's "re-touch on explicit request" path for
  lichess-eval games.
- Progress reuses the import-job mental model via polled `useEvalCoverage` — **no new
  analysis-job entity / table.**

### Coverage indicators (EVUX-02)
- **D-118-08 — Scope = Library flaw surfaces only.** Upgrade the existing badge family
  (FlawStatsPanel coverage badge / FlawDenominatorPill, FlawComparisonGrid, per-game
  NoAnalysisState pill, NoEngineAnalysisFlawsState empty state). **Replace the "partial /
  coming soon" copy** in `analysisCoverageCopy.tsx` with real "N of M analyzed" + CTA —
  chess.com games now genuinely get analyzed, so "coming soon" is stale. Endgames /
  Openings / GlobalStats keep their existing Phase-116 eval-coverage gates untouched.
- **D-118-09 — Low-coverage CTA threshold = named constant** (e.g. `LOW_COVERAGE_THRESHOLD`,
  default ~<80% analyzed → prominent CTA vs quiet badge), tunable in prod soak.
- **D-118-10 — Single coverage notion = `is_analyzed`** (has flaw counts, lichess OR
  engine — D-117-09). That's exactly what the flaw-comparison surfaces need. Defer a
  separate PV/best_move coverage number to the SEED-039 surface that consumes it. Planner
  must **verify `count_pending_evals` aligns with `is_analyzed`** (lichess-eval games count
  as analyzed, not pending) so the coverage % is honest.

### In-flight status (EVUX-03)
- **D-118-11 — Aggregate + per-game-tier-1 granularity.** Aggregate queued/analyzing
  counts on the coverage badge ("N of M analyzed · K in progress"), polled; plus a
  localized "Analyzing…" state only on the specific game the user tier-1-clicked (~10s).
  No per-card spinners across the archive.
- **D-118-12 — Extend `/imports/eval-coverage`** with in-flight (queued/leased) counts so a
  single polled call drives coverage %, the bulk-button disabled-state (D-118-06), and
  in-flight status. One source of truth; no separate status endpoint.

### Guest experience (ROADMAP criterion 5 / QUEUE-08)
- **D-118-13 — Swap CTA for sign-up prompt.** In the same slots where users see
  "Analyze more" / per-game "Analyze this game," guests see "Sign up to unlock full-game
  analysis," mirroring the existing Endgames upsell copy and gated via `useAuth`. Buttons
  never silently no-op. Rejected: disabled buttons + tooltip (reads as broken, not locked).

### Claude's Discretion
- Exact `LOW_COVERAGE_THRESHOLD` and tier-2 window-size constant values (start ~80% / 200).
- Polling cadence for `useEvalCoverage` (reuse the import-status interval pattern).
- The user-facing tier-1 endpoint shape (D-117-05 built only an internal/admin trigger):
  auth, guest-exclusion, optional rate-limit. Router stays thin; logic in
  `eval_queue_service`.
- Exact SQL for the "user has tier-2 in-flight" check (count over `eval_jobs` by user+tier,
  pending|leased) and any supporting index.
- Whether the bulk-button "N of M" label reuses the aggregate coverage numbers verbatim or
  a tier-2-window-scoped subset.
- New reusable analyze-upsell component vs inlining the Endgames pattern.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source of truth for this milestone
- `.planning/seeds/SEED-012-client-side-stockfish-tactics.md` §"Amendment (2026-06-12)" —
  locked D-1..D-8. Phase 118 implements the demand-UX face of **D-2** (coverage indicators),
  **D-3** (hybrid auto-window + explicit analyze-more), and the QUEUE-08 guest exclusion's
  UX.
- `.planning/ROADMAP.md` §"Phase 118: Demand UX + Auto-Enqueue" — goal + 5 success criteria
  (criterion 5 = guest promotion). Authoritative scope anchor.
- `.planning/REQUIREMENTS.md` — QUEUE-04, EVUX-01, EVUX-02, EVUX-03 + traceability table.

### Prior phase context (locked invariants 118 must respect)
- `.planning/phases/117-priority-queue-flaw-integration/117-CONTEXT.md` — critical:
  **D-117-05** (117 built the queue + an internal tier-1 trigger; 118 adds the user-facing
  triggers), **D-117-09** (`is_analyzed` = has flaw counts, lichess OR engine — the coverage
  denominator), **D-117-11** (per-user debounced flaw-cache invalidation — the coverage poll
  must reflect freshly-classified games), **D-117-12** (PV-vs-eval coverage; re-touch-on-
  explicit-request policy that D-118-03/07 refine).
- `.planning/phases/116-all-ply-engine-core/116-CONTEXT.md` — the `/imports/eval-coverage`
  endpoint origin (D-01 dedicated endpoint, D-04 response keys `pending_count`,
  `total_count`, `pct_complete`); D-118-12 extends this contract.

### Future consumer (why PV-coverage is deferred, not dropped)
- `.planning/seeds/SEED-039-*.md` — the tactic-motif classifier that consumes flaw-adjacent
  PV/best_move. The separate PV-coverage indicator lands when this surface ships, not in 118.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/eval_queue_service.py` — `enqueue_tier1_game(game_id, user_id)` already
  exists (guest no-op built in). 118 ADDS `enqueue_tier2_window(user_id)` + refines
  `_claim_tier3_derived` ORDER BY (D-118-04). Tier/lease/SKIP-LOCKED machinery is done.
- `app/routers/imports.py` `GET /imports/eval-coverage` + `EvalCoverageResponse` — extend
  with in-flight counts (D-118-12). `count_games_for_user` / `count_pending_evals` in
  `game_repository` — verify `is_analyzed` alignment (D-118-10).
- `app/middleware/last_activity.py` — throttled (≤1/hr) write path; the tier-2 enqueue hook
  point (D-118-01). D-07 already skips impersonated requests.
- `frontend/src/hooks/useEvalCoverage.ts` + `frontend/src/types/api.ts` — add poll interval
  + in-flight fields. Already consumed by Endgames/Openings/GlobalStats/Import.
- `frontend/src/components/library/analysisCoverageCopy.tsx` — the "partial / coming soon"
  copy to replace (D-118-08). Imported by `NoAnalysisState`, `NoEngineAnalysisFlawsState`,
  and the FlawStatsPanel coverage badge.
- `frontend/src/components/library/` — `FlawStatsPanel.tsx` (open in IDE),
  `FlawComparisonGrid.tsx`, `FlawCard.tsx`, `NoAnalysisState.tsx`,
  `NoEngineAnalysisFlawsState.tsx` — coverage badge + CTA + in-flight + analyze buttons.
- `frontend/src/hooks/useAuth.ts` + `pages/Endgames.tsx` upsell copy — guest gating /
  promotion pattern to mirror (D-118-13).
- Phase-112 single-game modal — natural home for the per-game tier-1 "Analyze this game"
  button + "Analyzing…" state.

### Established Patterns
- Routers thin (validation → service → response shaping); queue/coverage logic in services.
- Import-job mental model = start + poll a climbing counter (`useImport` / `/imports/{job}`)
  — reuse for analysis progress via `useEvalCoverage` polling, NOT a new job entity.
- `is_guest` exclusion enforced in `eval_queue_service` (QUEUE-08); frontend mirrors with a
  promotion CTA, never a silent no-op.
- Named constants for thresholds/limits (CLAUDE.md — no magic numbers).
- `data-testid` + ARIA on every new interactive element (CLAUDE.md browser-automation).

### Integration Points
- `last_activity` middleware write → tier-2 enqueue hook (the new automatic trigger).
- Import-completion path (`import_service`) → tier-2 enqueue.
- `/imports/eval-coverage` response shape → frontend coverage badge, bulk-button
  disabled-state, and in-flight status (one polled call).
- New user-facing tier-1 endpoint → `enqueue_tier1_game` (auth + guest-excluded).
- Coverage poll must observe D-117-11 cache-invalidation so newly-classified games surface.
</code_context>

<specifics>
## Specific Ideas

- Tier-1 per-game fan-out is the lichess "Request a computer analysis" ~10–30s game-review
  experience (measured ~10s, same 1M-node budget, so users can cross-check against lichess).
- "Analyze more" must read as honest about a shared fixed-throughput pool: it reorders
  priority, it does not buy more speed — hence the disabled-until-drained state rather than
  a button that appears to "do more."
- Guest promotion copy should read as "unlock," not "disabled/broken."
</specifics>

<deferred>
## Deferred Ideas

- **Engine-best-move step-through display / board-arrow viewer** — D-117-01 tags it "Phase
  118," but ROADMAP-118 success criteria don't include it. Out of scope here; revisit as its
  own slice (or confirm with user if they want it folded in).
- **Separate PV/best_move coverage indicator** — lands with the SEED-039 motif-tag surface
  that actually consumes PV. 118 coverage = `is_analyzed` only.
- **Filter-scoped analysis batch** ("analyze my last X rapid games") — original SEED
  decision #3; rejected for 118 in favor of next-chunk simplicity.
- **Endgames/Openings/GlobalStats coverage-messaging redo** — those gates already work;
  not re-touched to keep 118 focused on flaw surfaces.
- **Per-card in-flight spinners across the whole archive** — rejected for poll/render cost;
  aggregate + tier-1-local only.

### Reviewed Todos (not folded)
- `todo.match-phase 118` returned 10 keyword false-positives (recovery-popover copy,
  bitboard storage, benchmark rebuilds, prod backfills, a Tailwind class fix). None touch
  enqueue / coverage / in-flight / guest UX. Not folded.
</deferred>

---

*Phase: 118-Demand UX + Auto-Enqueue*
*Context gathered: 2026-06-14*
