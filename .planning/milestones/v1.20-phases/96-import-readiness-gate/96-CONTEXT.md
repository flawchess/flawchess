# Phase 96: Import Readiness Gate - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the `useEvalCoverage` → `window.location.reload()`-on-eval-complete hack
with a **two-tier per-page readiness gate**, and remove eval-progress UI from
non-import surfaces (per the canonical spec, `.planning/notes/import-readiness-gate.md`).

- **Tier 1 — hot lane done** (no import job `pending`/`in_progress`): Openings and
  Overview unlock.
- **Tier 2 — fully ready** (Tier 1 AND `pending_count == 0` AND Stage A/B
  percentiles persisted): Endgames unlocks; Openings eval-based metrics reveal.

Users are held on the import page until Tier 1 on a first import, then unlock via
user-initiated CTAs (Tier-1 in-page "Explore Openings", Tier-2 "Explore Endgames"
sonner action toast) plus reactive reveal via the readiness poll. No forced reload.

**Out of scope:** the LLM statistical-reasoning rework (Phase 97); any change to
the eval drain pipeline or Stage A/B percentile math itself (the wait is the
Stockfish drain at ~13–15 ev/s — not a target for optimization here).
</domain>

<decisions>
## Implementation Decisions

The canonical spec (`.planning/notes/import-readiness-gate.md`) already locks the
tier model, the 7 constraints, the CTA mechanics, and the rejected alternatives.
Those are NOT re-derived here — downstream agents MUST read that file. This
discussion resolved the one gray area the spec left open.

### Incremental-import Endgames lock
- **D-01: Endgames locks fully on incremental imports too**, identically to a
  first import — into the processing/locked state for the whole eval drain, until
  Tier 2. One gate behavior regardless of import type. Rationale: consistency and
  zero risk of ever surfacing a mid-drain endgame number; accepted that a
  returning user is pulled out of correct data they could otherwise see.
  - This confirms the spec's per-page table ("Endgames … **locked** until Tier 2
    (incremental too)") against the counter-argument that incremental drains are a
    small biased tail of a large evaluated corpus. User chose the simple, uniform
    rule over a threshold-based or keep-prior-data approach.
- **D-02: Same generic processing state for first-import and incremental.** Reuse
  one locked-state component with the same "Analyzing endgames (X/Y)" message and
  the eval X/Y counter as the only progress signal. No returning-user-specific
  copy ("re-analyzing with N new games"), no acknowledgment of prior data. One
  component, one message.

### Claude's Discretion (deferred to research/planning within Constraint 1 + the spec)
The user explicitly chose NOT to pre-decide these; planner/researcher resolve them
guided by the spec's locked constraints:
- **Tier-2 readiness signal** — HOW the backend authoritatively detects "Stage A/B
  percentiles persisted" without racing Stage B (Constraint 1 forbids reusing the
  eval-coverage 100% transition). Candidate approaches: explicit completion
  timestamp written when `compute_stage_b` finishes; existence of fresh
  `user_benchmark_percentiles` rows; `pending_count == 0` AND ≥1 percentile row.
  Correctness-critical — research should weigh the race exposure of each.
- **Readiness endpoint shape** — a single authoritative endpoint exposing both
  tiers (Constraint 1): new `GET /imports/readiness` returning `{tier1, tier2}`
  vs. extending `GET /imports/eval-coverage`. Note prior project preference (D-01
  in the eval-coverage endpoint docstring) for a dedicated endpoint over
  overloading an existing one. Also: poll cadence and whether it reuses or
  replaces the existing 3s eval-coverage poll.
- **Locked-route UX** — how a not-yet-ready route behaves (redirect to `/import`,
  in-place locked/processing state on the page, or disabled-nav-can't-click),
  replacing the current `profileHasCompletedImport()` all-or-nothing lock.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec (authoritative)
- `.planning/notes/import-readiness-gate.md` — THE design contract. Two-tier
  model, per-page behavior table, 7 locked constraints (readiness signal vs raw
  poll, informative holding page, "import complete" semantics, user-initiated
  unlock + the two CTAs, Stockfish bar on all pages, Openings Cpu-placeholder bar,
  tooltip-counter removal), and the rejected alternatives. **Read first.**

### Frontend — current gating & eval UI (to be replaced/edited)
- `frontend/src/App.tsx` — `profileHasCompletedImport()` (line 40) and the
  per-nav `locked` logic; current all-routes-on-first-sync gate this phase replaces.
- `frontend/src/hooks/useEvalCoverage.ts` — the `window.location.reload()`
  auto-reload + `evalCompletionReloadFired` module guard to retire (Constraint 4).
- `frontend/src/components/EvalCoverageHeader.tsx` — the Stockfish progress header
  that must stay on ALL pages (Constraint 5).
- `frontend/src/components/insights/EvalConfidenceTooltip.tsx` — remove the live
  eval counter from this tooltip (Constraint 7).
- `frontend/src/pages/Import.tsx` — the import holding page to drive as a state
  machine off the readiness endpoint (Constraint 2); houses the Tier-1
  "Explore Openings" in-page CTA.

### Backend — readiness inputs
- `app/routers/imports.py` — `GET /imports/eval-coverage` (line 129) and the
  imports router; site of the new/extended readiness endpoint.
- `app/services/eval_drain.py` — Stage B trigger via `asyncio.create_task(compute_stage_b(uid))`
  (~line 568) when pending hits zero; the source of the Constraint-1 race.
- `app/services/user_benchmark_percentiles_service.py` — `compute_stage_a` (line
  325), `compute_stage_b` (line 393); the percentile compute whose completion
  Tier 2 must observe.
- `app/models/user_benchmark_percentile.py` — `UserBenchmarkPercentile` table; row
  existence implies above-floor, no explicit "stage done" flag exists today.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **sonner `toast`** — already imported and used (`App.tsx`, `Openings.tsx`,
  `Home.tsx`); use its `action` API for the Tier-2 "Explore Endgames" toast.
- **`EvalCoverageHeader` style** — the existing progress-bar styling is the visual
  template for both the persistent global bar (Constraint 5) and the Openings
  pulsating-Cpu placeholder bar (Constraint 6).
- **`useUserFlag` / `setUserFlag`** (`App.tsx`) — existing per-user client flag
  pattern; analogous to the fire-once dedupe the Tier-2 toast needs (Constraint 4
  references the `evalCompletionReloadFired` guard as the model).
- **TanStack Query shared-key dedupe** — `useEvalCoverage` already shares one
  in-flight request via `['imports','eval-coverage']`; the readiness hook should
  follow the same shared-key + `refetchInterval` pattern.

### Established Patterns
- **Eval-coverage endpoint docstring (D-01/D-04)** records a project preference for
  a *dedicated* endpoint over extending `GET /imports/active`, and fixed response
  keys (`pending_count`, `total_count`, `pct_complete`). Weigh this when deciding
  the readiness endpoint shape.
- **Stage B fires off an active-import guard** (Phase 94.1 D-01) so it doesn't fire
  on every mid-import eval batch — the readiness "Tier 2" condition must align with
  that same "no active import AND zero pending" gate, plus percentile persistence.

### Integration Points
- The new readiness signal replaces `profileHasCompletedImport()` as the route-gate
  source in `App.tsx` (desktop nav + mobile bottom nav + drawer all read it).
- Endgames page gains a whole-page locked/processing state (D-01/D-02) keyed off
  Tier 2; Openings subtabs gain the repeating Cpu-placeholder treatment keyed off
  Tier 2 (Constraint 6).

</code_context>

<specifics>
## Specific Ideas

The user deferred the technical wiring decisions (readiness signal, endpoint
shape, locked-route UX) to research/planning rather than pre-deciding them — the
spec's locked constraints are sufficient guidance. The only explicit asks this
session were the two Endgames-lock decisions (D-01, D-02), both favoring the
simplest uniform rule over nuance.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Scope-adjacent items like
threshold-based incremental locking and returning-user-specific lock copy were
considered and explicitly rejected in favor of the uniform rule; see D-01/D-02.)

</deferred>

---

*Phase: 96-import-readiness-gate*
*Context gathered: 2026-05-28*
