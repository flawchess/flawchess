# Phase 126: Comparison Stats + Frontend - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 126 turns the populated `tactic_motif` data (Phases 124/125) into user-facing
surfaces in the **Library**:

1. **Backend** `GET /api/library/tactic-comparison` — per-motif **rates** (player vs
   opponents) normalized per game, with a Wilson-based significance verdict (the
   project's existing chess-score utility), a section-level sample gate, honoring all
   existing game filters + severity. Player/opponent split derived at query time via
   `is_opponent_expr(ply, games.user_color)` (no `is_opponent` column).
2. **Flaw-card motif chip** — each flaw card shows its `allowed` motif as a
   family-colored chip with a definition popover (TACUI-01), consistent with the shipped
   `TagChip` flaw-tag taxonomy pattern.
3. **You-vs-opponent comparison grid** — reuse the v1.25 `MiniBulletChart` /
   `FlawComparisonGrid` pattern (measure + CI + benchmark zone where available, per-motif
   tooltips) (TACUI-02).
4. **Tactic-motif filter** (added scope — see D-05) — a beta-gated motif filter in the
   existing Library FilterPanel/drawer.
5. **Mobile parity** at 375px with `data-testid` + ARIA (TACUI-03).

**All new tactic UI is gated behind the `beta_enabled` user flag** — only beta users
see motif chips, the comparison grid, and the motif filter (D-01).

**Out of scope:** the detector/schema (done in 124), the prod backfill (done/deferred in
125), any new Stockfish work, benchmark-zone *computation* for tactic motifs (the grid
shows a benchmark zone only "where available" — no new benchmark pipeline this phase).
</domain>

<decisions>
## Implementation Decisions

### Beta gating
- **D-01:** All new tactic surfaces (motif chips, comparison grid, motif filter) are
  visible only to `beta_enabled` users. Enforcement is **frontend-only hide** — the
  frontend checks `beta_enabled` (from `/users/me`, already on the `User` type) and does
  not render any tactic UI for non-beta users. Backend endpoints are NOT hard-gated.
- **D-01a (trade-off, accepted):** Because the tactic-comparison endpoint and the
  existing flaw-card responses serve a user **their own** chess data, frontend-only
  gating is a reasonable feature-rollout flag, not a security boundary. Known limitation:
  tactic data (incl. the new aggregate endpoint) is reachable by a non-beta user who
  inspects the API directly. Acceptable for a beta gate.
- **D-01b:** `beta_enabled` is currently stored + returned in `/users/me` but gates
  **nothing** in the live app (the v1.11 "Endgame Insights" gating it references was
  removed). Phase 126 establishes the frontend beta-gate pattern. Guests / non-beta
  users (default `beta_enabled = false`) see no tactic UI.

### Comparison endpoint (TACCMP-01/02/03)
- **D-02:** New endpoint mirrors the existing `GET /library/flaw-comparison`
  (`app/routers/library.py:172`) + its service/repository. Reuse `apply_game_filters()`
  (`app/repositories/query_utils.py`) for all game filters + severity; reuse
  `is_opponent_expr` for the player/opponent split.
- **D-03:** Significance via the project's existing **Wilson-based chess-score**
  utility only (`compute_confidence_bucket` / the shared helper) — no parallel test
  invented. A **section-level sample gate** withholds the whole comparison below a
  minimum-sample threshold (mirror the v1.25 gate; exact threshold = Claude's discretion,
  align with `FlawComparisonGrid`).
- **D-04:** Headline rate normalization is **per game** (the intuitive metric). A
  "per 100 blunders" view may live in a tooltip but per-game is the displayed default.

### Motif filter (added scope — flagged & user-approved)
- **D-05:** Add a **new** "Tactic motif" filter control. This is a capability beyond the
  literal TACCMP/TACUI requirements (which only name the existing game filters); the user
  explicitly opted into adding it to this phase. It is **beta-gated** like the rest.
- **D-06:** The filter lives in the **existing Library FilterPanel / drawer** (alongside
  TC / platform / rated / recency / color), is **multi-select by family** (not individual
  motif), and flows through the same `apply_game_filters()` plumbing so it composes with
  every other filter. Applies to the Library flaw list.

### Comparison grid contents
- **D-07:** The you-vs-opponent grid shows **collapsed families**, up to **~6 rows**,
  ranked by the **largest *significant* (Wilson-gated) you-vs-opponent gap**, falling
  back to sample **volume** to fill remaining slots. Mobile-friendly, surfaces what's
  notable per user.
- **D-08 (provisional family taxonomy — tune in planning):** ~6 families collapsing the
  ~25 motifs. Proposed grouping (planner may refine, and must align the filter D-06 and
  the grid D-07 to the SAME taxonomy):
  1. **Fork**
  2. **Pin / Skewer** (pin, skewer, x-ray)
  3. **Discovered / Double-check** (discovered-attack, double-check)
  4. **Mate patterns** (all named-mates + back-rank-mate + generic `mate`)
  5. **Hanging piece**
  6. **Combinations** (sacrifice, deflection, attraction, intermezzo,
     interference/self-interference, clearance, capturing-defender)
  Family→color mapping must be added to `frontend/src/lib/theme.ts` (per the project's
  theme-constants rule); chips are "family-colored" (TACUI-01).

### Chip display
- **D-09:** **Hide low-confidence chips** — apply Phase 124's query-time
  `tactic_confidence` threshold (`AND tactic_confidence >= :t`) so uncertain tier-3
  motifs don't render a chip. Exact threshold = Claude's discretion, but it must be a
  named constant (no magic number), sweepable in SQL per D-11/124.
- **D-10:** Show the motif chip on **both** the Library flaw **list** rows and the
  **single-game** flaw card.

### Claude's Discretion
- Exact sample-gate threshold and low-confidence chip threshold (named constants;
  align with v1.25 `FlawComparisonGrid` precedent).
- Endpoint/service/repository file layout (follow the `flaw-comparison` analog).
- Final family taxonomy + int/key mapping (constrained to keep filter D-06 and grid D-07
  on the same families) and the family color palette in `theme.ts`.
- Popover copy for motif definitions (follow popover-copy minimalism: WHAT + sign
  convention; trust zone/family colors; no jargon).
- MiniBulletChart benchmark-zone handling when no tactic benchmark exists ("where
  available" — degrade gracefully, no new benchmark pipeline).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & prior phase decisions
- `.planning/REQUIREMENTS.md` (TACCMP-01/02/03, TACUI-01/02/03) — the locked requirements
  for this phase.
- `.planning/phases/124-schema-tactic-detector/124-CONTEXT.md` — schema (single
  `tactic_motif` enum, `tactic_piece`, `tactic_confidence`), the full motif list
  (D-03/D-04), priority order (D-07), and query-time confidence suppression (D-11). The
  family taxonomy (D-08 here) must be consistent with these motif names.
- `.planning/phases/125-backfill-tactic-motifs/125-CONTEXT.md` — coverage semantics
  (NULL = no-PV/low-confidence, not skipped); honest-coverage contract the comparison
  must respect.

### v1.25 comparison precedents (reuse, don't reinvent)
- `app/routers/library.py` §`/flaw-comparison` (line ~172) + `FlawComparisonResponse` —
  the endpoint/response shape to mirror for `/tactic-comparison`.
- `app/repositories/query_utils.py` — `apply_game_filters()` (single source for all game
  filters; the new motif filter D-06 extends this).
- `app/services/library_service.py`, `app/repositories/library_repository.py`,
  `app/repositories/game_flaws_repository.py` — service/repo layer for flaw stats; the
  `is_opponent_expr` split lives here.
- `frontend/src/components/library/FlawComparisonGrid.tsx`,
  `frontend/src/components/charts/MiniBulletChart.tsx`,
  `frontend/src/components/popovers/FlawBulletPopover.tsx`,
  `frontend/src/lib/flawComparisonMeta.ts`, `frontend/src/lib/scoreBulletConfig.ts` —
  the bullet-grid UI pattern to reuse for TACUI-02.
- `frontend/src/components/library/TagChip.tsx`, `frontend/src/lib/tagDefinitions.ts`,
  `frontend/src/lib/tagVisuals.ts` — the shipped flaw-tag chip + definition-popover
  pattern to follow for TACUI-01 (family-colored chips).

### Shared utilities & rules
- The Wilson-based chess-score significance helper (`compute_confidence_bucket` / shared
  util used by `OpeningInsightFinding` / flaw comparison) — D-03.
- `app/models/user.py:34` (`beta_enabled`), `frontend/src/types/users.ts:19`
  (`beta_enabled`), `frontend/src/hooks/useAuth.ts` — the flag + current-user source for
  the frontend gate (D-01).
- `frontend/src/lib/theme.ts` — family color constants must live here (project rule).
- CLAUDE.md "Frontend > Browser Automation Rules" — `data-testid` + ARIA + semantic HTML
  + mobile-375px parity (TACUI-03).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FlawComparisonGrid` + `MiniBulletChart` + `FlawBulletPopover`: the v1.25 you-vs-opponent
  bullet grid — clone its structure for the tactic-motif grid (TACUI-02).
- `TagChip` + `tagDefinitions` + `tagVisuals`: the flaw-tag chip/popover pattern —
  directly model the motif chip on this (TACUI-01).
- `apply_game_filters()`: the single filter implementation; the new motif filter (D-06)
  and the comparison endpoint (D-02) both go through it.
- `is_opponent_expr(ply, games.user_color)`: existing query-time player/opponent split —
  no new column.
- `/library/flaw-comparison` endpoint + response model: the exact analog for the new
  `/library/tactic-comparison` endpoint.

### Established Patterns
- Router stays thin (validate → service → response); branching/aggregation in the service
  layer.
- Theme color constants in `theme.ts` only; no hardcoded semantic colors.
- `beta_enabled` is read from the current user (`useAuth` / `/users/me`); gating is a
  render-time conditional in the frontend.

### Integration Points
- New endpoint in `app/routers/library.py` (prefix `/library`, relative path
  `/tactic-comparison`).
- New filter field threaded through `apply_game_filters()` + the Library filter
  state/FilterPanel (desktop drawer AND mobile drawer — apply to both per CLAUDE.md).
- Frontend beta gate wraps the Library tactic surfaces.

</code_context>

<specifics>
## Specific Ideas

- "Everything behind `beta_enabled` — only beta users see the new tactic tags, filters,
  and other related UI changes" (the originating constraint → D-01).
- Top-N grid surfaces *what's notable for that player* (significant gap first), not a
  fixed scoreboard → D-07.

</specifics>

<deferred>
## Deferred Ideas

- **Backend hard-gating of tactic data behind `beta_enabled`** (conditional serialization
  / 403 on the endpoint) — explicitly NOT done this phase (D-01 chose frontend-only). If
  beta later needs to be a true access boundary, revisit.
- **Per-100-blunders as a first-class displayed metric** — per-game is the headline
  (D-04); the alternate normalization is at most a tooltip detail this phase.
- **Tactic-motif benchmark zones** (population baselines for the bullet grid) — the grid
  shows a benchmark zone only "where available"; computing tactic benchmarks is a
  separate effort, not this phase.

### Reviewed Todos (not folded)
Matched by keyword overlap only ("score"/"frontend"/"bullet"/"backfill"); none relate to
tactic tagging:
- "Reframe Recovery Score Gap popover copy" — different surface (endgame recovery).
- "WR-01 pt-33 invalid Tailwind class on Score Y-axis label" — old score-chart bug.
- "Phase 94.4 / 94.2 / 99 prod-backfill UATs" — unrelated deploy/backfill items.

</deferred>

---

*Phase: 126-comparison-stats-frontend*
*Context gathered: 2026-06-18*
