# Phase 70: Backend opening insights service - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-26
**Phase:** 70-backend-opening-insights-service
**Areas discussed:** Ranking formula, Filter contract & route, Bookmarks & floors, Dedupe & attribution

---

## Ranking Formula

Initial proposal was a continuous `frequency × severity` score with three sub-options (excess-games-above-neutral, distance-from-threshold, severity-only-with-frequency-tiebreak). User redirected: align severity with the existing `frontend/src/lib/arrowColor.ts` two-tier (light/dark) coloring at ±5% / ±10% above neutral.

### Severity boundary at 55%

| Option | Description | Selected |
|--------|-------------|----------|
| Strict `>` | Matches arrowColor.ts behavior exactly (55.0% loss_rate is grey/neutral, not a finding). REQUIREMENTS-CORE-05 says ≥ 0.55 but arrows use strict >. Aligning to arrows is the whole point. | ✓ |
| Inclusive `≥` | Keeps REQUIREMENTS-CORE-05 literal; 55.0% qualifies as minor weakness even though the arrow is grey. Off-by-one with the visual cue. | |

**User's choice:** Strict `>` (Recommended).

### Ranking within a severity tier

| Option | Description | Selected |
|--------|-------------|----------|
| Tier-then-frequency | All majors before any minors; within tier sort by n_games desc. Predictable; matches "big problem before small problem" visual idiom. With caps of 5/3, mostly majors will surface, minors only fill remainder. | ✓ |
| Fold into one score | rank_score = n_games * (rate − 0.5). Continuous severity × frequency. Risk: a 50-game light-red outranks a 12-game dark-red, conflicting with major-before-minor visual idiom. | |

**User's choice:** Tier-then-frequency (Recommended). User note: "1."

**Notes:**
- Classification metric switched from REQUIREMENTS-CORE-05's `score = (W + D/2) / n` to `win_rate = W / n` for strengths, mirroring arrowColor.ts which uses raw win/loss percentages.
- This is a REQUIREMENTS amendment captured in CONTEXT.md D-15 / D-16 / D-17 — apply at Phase 70 commit time.
- No built-in recency weighting (the active recency filter handles it).

---

## Filter Contract & Route

### Filter request shape

| Option | Description | Selected |
|--------|-------------|----------|
| New OpeningInsightsRequest | Mirrors /openings/* and /stats/most-played-openings query-param surface 1:1. Lives in new app/schemas/opening_insights.py. v1.11 FilterContext untouched. | ✓ |
| Reuse v1.11 FilterContext | Extend it (rated_only → rated, add opponent_type, elo_threshold). Couples openings + endgame schemas. | |

**User's choice:** New OpeningInsightsRequest (Recommended).

### Route placement

| Option | Description | Selected |
|--------|-------------|----------|
| POST /api/insights/openings | Symmetric with POST /api/insights/endgame. Establishes /insights as canonical insights namespace. POST + JSON body fits existing /openings/* POST endpoints. | ✓ |
| GET /api/openings/insights | Co-located with other openings endpoints. GET fits read-only nature; query params match /openings/most-played-openings exactly. Breaks /insights namespace symmetry. | |
| POST /api/openings/insights | Co-located but POST + JSON body. Mixes namespaces — worst of both. | |

**User's choice:** POST /api/insights/openings (Recommended).

**Notes:**
- The v1.11 router's `_validate_full_history_filters` gate (full-history-only) is endgame-LLM-specific and MUST NOT be applied to the new opening-insights route — for openings, every filter must reshape findings (INSIGHT-CORE-01).

---

## Bookmarks & Floors

User redirected the discussion at this point with a major contract change: instead of one flat findings list shaped by an active color filter, the response should be **four named sections** — White Opening Weaknesses, Black Opening Weaknesses, White Opening Strengths, Black Opening Strengths — each drawing from top-20 most-played + bookmarks for that color. This reframed the rest of the bookmark / floor discussion under that 4-section structure.

Top-20 (vs original top-10) is a REQUIREMENTS-CORE-02 amendment captured in CONTEXT.md D-15.

### Bookmark color matching

| Option | Description | Selected |
|--------|-------------|----------|
| Match active color or color=null | Include bookmarks where bookmark.color matches the section color OR is NULL. Color=null bookmarks get scanned in BOTH white and black sections. | |
| Color-tagged only; null bookmarks dropped | Strict: only bookmarks with explicit color land in their matching section. Null-color bookmarks excluded. Cleanest semantics. | ✓ |
| Null bookmarks scanned per-color (clarification of option 1) | Same outcome as option 1 — included for clarity. | |

**User's choice:** Color-tagged only; null bookmarks dropped.

### Bookmark entry-floor bypass

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — bypass entry floor | User explicitly opted in by bookmarking; respect that signal. Per-candidate n≥10 floor still applies, so thinly-played bookmarks surface 0 findings naturally. | ✓ |
| No — 50-game floor applies uniformly | Bookmarks must clear the same bar. Simpler, less generous. | |

**User's choice:** Yes — bypass (Recommended).

### Per-user total-game floor

| Option | Description | Selected |
|--------|-------------|----------|
| No per-user floor | Let the per-entry 50-game and per-candidate n≥10 floors do all the gating. With 4 always-present sections, "mostly empty" is normal; one consistent empty-state message. | ✓ |
| Yes — per-user floor + status flag | Endpoint returns "insufficient_history" status when total games < threshold. Cleaner UX for new users, extra knob and status path. | |

**User's choice:** No per-user floor (Recommended).

**Notes:**
- The 4-section response shape is the load-bearing change here. CONTEXT.md D-01 / D-02 / D-03 capture it.
- INSIGHT-CORE-07 caps (top-5 weakness + top-3 strength) become per-section, so the visible ceiling on screen is up to 16 findings (5 + 5 + 3 + 3).

---

## Dedupe & Attribution

Single confirmation question covering five proposed rules together:
1. Dedupe scope: within a single color section (not cross-color).
2. Attribution lookup: `MAX(ply_count)` over `openings` table rows matching the resulting hash.
3. Fallback: when no openings row matches, attribute to entry's opening; for bookmarks with no entry match, use bookmark.label.
4. Cross-entry dedupe: deeper-entry wins (higher ply_count on the entry's opening).
5. Deep-link target: entry FEN + candidate-move SAN.

| Option | Description | Selected |
|--------|-------------|----------|
| Looks right — lock as proposed | All five rules as drafted. | ✓ |
| Adjust one or more rules | User would explain what to change. | |

**User's choice:** Looks right — lock as proposed.

**Notes:**
- Implementation: one batched `SELECT ... WHERE full_hash IN (...)` for the deepest-opening lookup over surviving findings (~16 max after caps).
- Cross-color collisions are preserved as two distinct findings — repertoire issues differ even if positions transpose.

---

## Claude's Discretion

- File layout: `app/schemas/opening_insights.py`, `app/services/opening_insights_service.py`. Planner finalizes paths.
- Configuration constants: module-level in the service file (no env vars, no DB-stored settings, no separate registry like endgame_zones.py). Tunable via PR.
- Whether the openings-table attribution lookup is a single batched IN(...) query or joined into the main aggregation.
- Final type-tightening on `recency` field in OpeningInsightsRequest — match `app/services/stats_service.recency_cutoff` accepted values.
- 4-section response can equivalently be modeled as a flat findings list with frontend binning. The 4-named-lists shape is preferred for explicitness; planner may revisit if it simplifies the executor's task without hurting Phase 71.
- If during planning the backend benefits from honoring `color` filter to skip computing the unused color (~50% latency savings), revisit — but the response shape stays four-keyed.

## Deferred Ideas

- LLM narration of opening insights — v1.13.x or v1.14 (REQUIREMENTS Future Requirements).
- Service-layer caching for heavy users (10k+ games) — defer per INSIGHT-CORE-09; revisit after Phase 71 production telemetry.
- Continuous severity × frequency ranking — discussed and rejected; revisit only if real-world data shows bad top-3/top-5 surfacings.
- Recency-weighted ranking — discussed and rejected; recency is already a user-controllable filter.
- Per-user total-game floor — discussed and rejected; revisit if Phase 71 new-user feedback shows the empty-state is confusing.
- Phase 73 (meta-recommendation aggregate) and Phase 74 (bookmark badge) — both consume the Phase 70 response unchanged. The `entry_full_hash` and `source: Literal["top_openings", "bookmark"]` fields on each finding (CONTEXT.md Specifics) make Phase 74's bookmark→finding mapping a simple Python filter without a second backend call.
- Frontend `OpeningInsightsBlock` UI / styling / mobile-drawer behavior — Phase 71 concern.

## REQUIREMENTS Amendments to Apply at Phase 70 Commit Time

(Captured here for the executor in addition to CONTEXT.md D-15 / D-16 / D-17.)

1. `.planning/REQUIREMENTS.md` INSIGHT-CORE-02: top-10 → top-20.
2. `.planning/REQUIREMENTS.md` INSIGHT-CORE-05: classifier shifts from `score ≥ 0.60` for strength to `win_rate > 0.55` (matching arrowColor.ts) with severity tier at `≥ 0.60`. Weakness boundary tightens to strict `>`.
3. `.planning/milestones/v1.13-ROADMAP.md` Phase 70 success-criteria 2 (top-10 → top-20) and success-criterion 4 (ranking formula resolved).
4. `CHANGELOG.md` § Unreleased / Changed: one-line note describing the classifier alignment with the board arrow coloring.
