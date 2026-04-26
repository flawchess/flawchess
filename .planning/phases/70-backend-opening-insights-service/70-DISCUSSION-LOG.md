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

> **2026-04-26 update — superseded by the algorithm redesign below.** The amendments listed here (top-10 → top-20, classifier shift) are still partially valid but are subsumed by a much larger rewrite. Use the "Post-Discussion Redesign" section below as the authoritative list.

1. ~~`.planning/REQUIREMENTS.md` INSIGHT-CORE-02: top-10 → top-20.~~ → REPLACED: top-N concept dropped entirely (see redesign).
2. `.planning/REQUIREMENTS.md` INSIGHT-CORE-05: classifier shifts from `score ≥ 0.60` for strength to `win_rate > 0.55` (matching arrowColor.ts) with severity tier at `≥ 0.60`. Weakness boundary tightens to strict `>`. **Still valid.**
3. ~~`.planning/milestones/v1.13-ROADMAP.md` Phase 70 success-criteria 2 (top-10 → top-20)~~ → REPLACED: success-criterion 2 needs full rewrite.
4. `CHANGELOG.md` § Unreleased / Changed: classifier alignment with the board arrow coloring. **Still valid; expand to also note the algorithm redesign.**

---

## Post-Discussion Redesign (2026-04-26, same-day)

**Trigger:** A `/gsd-explore` follow-up examined whether the originally-spec'd algorithm would discover real findings. Walked through the Caro-Kann Hillbilly Attack as a worked example: position `1. e4 c6 2. Bc4 d5 3. exd5 cxd5 4. Bb5+` shows 29 games at 55% loss rate for the user, but is 4 plies deeper than where the original "top-N entry scan" would look. The Hillbilly entry in `openings.tsv` is at ply 4 (`1. e4 c6 2. Bc4`), so the original algorithm would scan only depth-1 candidates from there (Black's reply 2...d5, dominated by ~91/91 games — no useful WDL split). **The original algorithm structurally cannot reach the actual signal.**

### Algorithm: top-N entry scan vs. first-principles transition aggregation

| Option | Description | Selected |
|--------|-------------|----------|
| Top-N entry scan (original) | Scan top-20 most-played openings per color × `query_next_moves` per entry. ~40 sequential repository calls. Fails to surface deep-line weaknesses inside a single named opening (Hillbilly Bb5+ unreachable). | |
| First-principles transition aggregation | Single SQL aggregation per color over `(entry_hash, candidate_san)` transitions in entry_ply ∈ [3, 16]. Surfaces deep findings naturally; top-played openings emerge as a side-effect of the n_games tiebreak. | ✓ |
| Recursive walk down dominant lines | Hybrid: from each named entry, follow the most-played continuation forward as long as `n ≥ floor`. Cleaner than depth-1 but more complex than the single-SQL approach. | |

**User's choice:** First-principles transition aggregation. "We should rethink the algo from first principles. The algo should surface weaknesses based on evidence (how many games there are) and how extreme the strengths and weaknesses are."

### Bookmarks as algorithmic input

| Option | Description | Selected |
|--------|-------------|----------|
| Keep bookmarks as auxiliary entry source (original D-18/19) | Bookmarks bypass the entry-floor; user-explicit deep-line interest. | |
| Drop bookmarks from algorithm | Under transition aggregation, every position the user played is implicitly scanned. Bookmarks add no algorithmic value. They remain a UI tracking feature; Phase 74 (stretch) maps insights → bookmarks at visualization layer only. | ✓ |

**User's choice:** Drop entirely. "I think we should ignore bookmarks and most played openings completely."

### Ply window

| Option | Description | Selected |
|--------|-------------|----------|
| entry_ply [3, 8] | Conservative; covers move 1.5–4.5; tight search space. Misses any deep main-line theory beyond move 4. | |
| entry_ply [3, 12] | Wider; covers move 1.5–6.5; ~25% more search cost. | |
| entry_ply [3, 16] | "Go big"; covers move 1.5–8.5; comfortable for serious-theory users. With the new index, completes in <1 s for the heaviest user (Hikaru, 65k games). | ✓ |

**User's choice:** [3, 16]. "Yeah, let's go big."

### Evidence floor

| Option | Description | Selected |
|--------|-------------|----------|
| n ≥ 10 (original) | Surfaces noisy findings; CI on a 60% rate is roughly ±31%. | |
| n ≥ 20 | Surfaces the user's own Hillbilly example (29 games, with some excluded by entry_ply ≤ 16 so the effective count was 25 in the verification query); CI on 60% is ~±22%. | ✓ |
| n ≥ 30 | Tighter signal but explicitly excludes the user's own motivating Hillbilly example. | |

**User's choice:** n ≥ 20. (Originally proposed 30, then accepted Claude's pushback that 30 would exclude the very example that motivated the redesign.)

### Index strategy (key perf finding)

| Option | Description | Selected |
|--------|-------------|----------|
| No new index, accept 1–2 s for heavy users | Smallest schema change. | |
| `(user_id, ply)` partial index | Targets the WHERE clause but doesn't help the LAG window's PARTITION BY game_id — Postgres still does a disk-spilled re-sort. **Verified: didn't help.** | |
| `(user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ply BETWEEN 1 AND 17` | Column order matches the LAG window's stream order; rows arrive pre-sorted, no re-sort needed. INCLUDE columns make it index-only. **Verified: 2.0 s → 816 ms for Hikaru, 65 ms for median user.** | ✓ |

**User's choice:** Composite partial index with the LAG-aware column order. New Alembic migration in Phase 70.

### Performance Verification (against dev DB, 2026-04-26)

| User | Games | Positions | Without index | With `ix_gp_user_game_ply` |
|------|-------|-----------|---------------|----------------------------|
| 28 (median) | 5,045 | 336k | 109 ms (max_ply=8) | **65 ms (max_ply=16)** |
| 14 (p90) | 22,426 | 1.6M | 1.16 s (max_ply=8) | not retested (extrapolated <300 ms) |
| 7 (Hikaru, p99) | 65,440 | 5.7M | 2.0 s (max_ply=16) | **816 ms (max_ply=16)** |

Plan with the index uses **Index Only Scan with Heap Fetches: 0** — no table touch, no re-sort.

## Updated REQUIREMENTS Amendments to Apply at Phase 70 Commit Time

(Authoritative list, supersedes the four-item list above.)

1. `.planning/REQUIREMENTS.md` INSIGHT-CORE-02: rewrite end-to-end. Replace "top-N most-played openings entry scan" with "single SQL transition aggregation in entry_ply ∈ [3, 16]". Bookmarks explicitly out of scope as algorithmic input.
2. `.planning/REQUIREMENTS.md` INSIGHT-CORE-04: floor moves from `n ≥ 10` to `n ≥ 20`.
3. `.planning/REQUIREMENTS.md` INSIGHT-CORE-05: classifier shifts from `score ≥ 0.60` to `win_rate > 0.55` / `loss_rate > 0.55` with severity tier at `≥ 0.60`.
4. `.planning/milestones/v1.13-ROADMAP.md` Phase 70 success-criteria 2 (top-N entry scan → transition aggregation), 4 (ranking formula). Bookmarks no longer mentioned as input.
5. `CHANGELOG.md` § Unreleased / Changed: one entry covering both the algorithm redesign (first-principles transition aggregation) and the classifier alignment with arrow coloring.
6. New Alembic migration adds `ix_gp_user_game_ply` partial composite index per CONTEXT.md D-31. Update `app/models/game_position.py::GamePosition.__table_args__` to declare it.
