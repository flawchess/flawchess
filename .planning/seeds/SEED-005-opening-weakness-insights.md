---
id: SEED-005
status: dormant
planted: 2026-04-26
planted_during: v1.12 Benchmark DB & Population Baselines (executing, Phase 69 mid-ingest)
trigger_when: milestone v1.13 opens (after v1.12 ships)
scope: milestone
---

# SEED-005: Opening weakness and strength insights

## Why This Matters

The Move Explorer already lets users navigate any reached position and see WDL rates per candidate move. That signal exists today but is **passive** — the user has to know where to look. A 1500 player with 3000 games across 15 different openings has dozens of weak spots they will never discover by random browsing.

The Endgame Insights block in v1.11 set the precedent: surface findings *where the data lives*, not in a dedicated nav tab. v1.13 mirrors that for openings — auto-scan the user's most-played and bookmarked openings, identify candidate moves where the user is materially under-performing (or over-performing), and present them as a templated bullet list with deep-links straight into the Move Explorer at the implicated position.

**Why self-referential is sufficient — and why v1.13 does NOT depend on v1.12's benchmark DB.** Opening insights live in book-move territory. By construction, theory considers these positions roughly equal for both sides (engine eval ≈ 0.0). If a player loses ≥55% in an objectively-equal position over n≥10 games, that is a problem for *that player* regardless of population behavior. Adding "vs. population mean X%" doesn't change the actionable signal — the player still needs to fix their preparation. This collapses what would otherwise be a v1.12-dependent feature into a self-contained one.

This is in deliberate contrast to v1.11/v1.12 endgame work, which is *not* self-referential-sufficient: endgame positions span a wide eval range, so absolute Conversion / Recovery rates only become meaningful relative to opponent or population baselines.

## When to Surface

**Trigger:** Milestone v1.13 opens (after v1.12 ships).

This seed should be presented during `/gsd-new-milestone` when:
- The user starts planning v1.13.
- OR the milestone scope mentions "opening insights", "weakness detection", "repertoire analysis", "automatic scan of openings", "preparation gaps".
- OR the roadmap references extending the v1.11 insights pattern from endgames to openings.

Do NOT surface during v1.12. v1.12 is the population-baseline milestone; opening insights deliberately do not consume its outputs (see rationale above), so parallel-developing them would just confuse scope. v1.13 also has no implementation dependency on v1.12 — it could ship before v1.12 in principle, but the milestone-ordering convention keeps it after.

## Prior Work (Do Not Re-Derive)

- **v1.11 LLM Endgame Insights pattern.** Pre-computed structured findings → optional LLM narration layer → `llm_logs` cache → in-tab block. v1.13 reuses the *placement* and *deep-link* idiom but starts as **pure templated/rule-based** (no LLM in v1 of v1.13). LLM wrap-up is a stretch goal, see Open Questions.
- **Move Explorer WDL-per-candidate-move query.** The aggregation v1.13 needs is structurally the same query the Move Explorer already runs, filtered by player + opening entry position + min-games threshold. No new index work expected; Zobrist hashes already cover position lookup.
- **Openings → Stats tab top-10 list.** v1.13 reuses the **exact algorithm** that produces this list — top-10 most-played openings for white + top-10 for black. Whatever convention Stats uses (named-opening grouping, min-games floor, ECO depth treatment) is what the insight scan iterates over. Confirm the algorithm is exposed as a service-layer call before planning, not duplicated.
- **Bookmarked positions** are an explicit, finite set; concatenated with the top-20 named-opening entry positions to form the scan input.

## Scope Estimate

**Milestone** — likely 3-5 phases. Rough decomposition (subject to `/gsd-discuss-phase` per phase):

### Phase A: Backend insight-generation service

- New service `app/services/opening_insights_service.py` (or extension of existing openings service).
- Inputs: user_id + active filters (color, time control, recency, etc. — same filters as Stats tab).
- Algorithm:
  1. Fetch top-10 most-played openings per color (reuse Stats tab service) + all bookmarked positions for the user. Apply min-games floor per entry (e.g. ≥50 games; align with Stats tab convention).
  2. For each entry position, scan **only the immediate next ply** of candidate moves the user has played (no deep recursion — deeper named openings appear as their own top-10 entries; recursion would thin samples).
  3. For each (entry_position, candidate_move) pair with n ≥ 10 games, compute loss_rate = losses / n and score = (wins + draws/2) / n.
  4. Classify: weakness if loss_rate ≥ 0.55, strength if score ≥ 0.60. Otherwise neutral, drop.
  5. Deduplicate findings by Zobrist hash of the resulting position. When the same finding hash surfaces under multiple openings (e.g. Scandinavian generic vs Scandinavian Main Line), attribute to the **deepest matching opening** only.
  6. Rank findings by importance (frequency × severity — exact formula TBD, see Open Questions).
  7. Cap displayed findings (e.g. top 5 weaknesses + top 3 strengths). Configurable.
- Output: structured `OpeningInsightFinding` payload — `{opening_name, opening_eco, entry_fen, candidate_move_san, n_games, w, d, l, loss_rate, score, classification: "weakness" | "strength", deep_link_target}`.
- Performance: structurally one aggregate query per entry position. For 20 entries × 5-10 candidate moves each, well within on-the-fly latency budget. Cache at the service layer if heavy users (10k+ games) push past acceptable latency; do **not** add a precompute pipeline preemptively.

### Phase B: Frontend — Stats subtab integration

- Add `OpeningInsightsBlock` component to Openings → Stats subtab (primary surface).
- Renders templated bullets: "You lose 62% as Black after 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 (n=18) → [open in Move Explorer]".
- Strengths styled distinctly from weaknesses (existing red/green semantic colors from `theme.ts`).
- Deep-link click → navigate to Openings → Moves tab pre-loaded at the entry FEN with the candidate move highlighted.
- Empty state when no findings clear thresholds.

### Phase C: Frontend — Moves tab integration

- Inline bullet next to existing red/green candidate-move arrows on the board.
- Bullets are scoped to the *currently displayed* position (i.e. arrow + bullet for any candidate from the position the user is looking at, not the full scan).
- Reuse the same `OpeningInsightFinding` payload from Phase A.

### Phase D (stretch): Meta-recommendation layer

- Aggregate-level finding: "You have weaknesses across 8 different openings — consider narrowing your repertoire" or "Your Caro-Kann shows 5 weak responses — focus revision here".
- Could be templated (rule-based threshold on count of weaknesses across openings) or LLM-narrated (handed the full findings list).
- Decide LLM-vs-templated in Phase D's discuss step. v1.11 endgame insights are LLM; v1.13 starts templated, so an LLM addition here is a deliberate scope expansion.

### Phase E (stretch): Bookmark-driven badge

- Visual indicator on bookmark cards when a bookmarked opening surfaces a weakness — small red dot badge or count chip — so users notice issues without opening the bookmark.

## Open Questions

These should be resolved during `/gsd-discuss-phase` for the relevant phase, NOT pre-committed in the milestone roadmap:

1. **Importance ranking formula.** Frequency × severity? Severity-only with frequency as a tiebreak? Recency-weighted (last 6 months > older)? Affects which 5 findings get surfaced when the scan returns 30+. Probably worth sweeping a few formulas during Phase A and eyeballing the output on real users.
2. **Min-games thresholds.** Entry-position floor (50 games to even consider an opening for the scan?) and candidate-move floor (n ≥ 10? higher?) — confirm against Stats tab conventions before planning.
3. **Stats-tab top-10 algorithm.** How exactly does the existing tab compute its top-10? Named opening grouping (ECO-tree-rolled-up?) or position-frequency? One-time investigation in Phase A. If the algorithm isn't already a clean service-layer call, refactor it first so v1.13 reuses rather than duplicates.
4. **Filter awareness.** Stats tab filters reshape the underlying data; insights must reflect the active filter set or they're misleading (this lesson is already encoded in v1.11 endgame insights). Confirm the insight service accepts the same filter object the rest of the openings stats use.
5. **Color symmetry.** Top-10 for white and top-10 for black are scanned independently — but if the same opening shows up on both lists (rare, but the Sicilian as both colors might happen for symmetric repertoires), the dedupe should handle it. Verify during Phase A.
6. **LLM wrap-up timing.** Phase D scope creeps if the LLM layer is bundled in. Cleaner to ship templated-only as v1.13 and revisit LLM as v1.13.x or v1.14 once the templated findings are in real users' hands and we know which findings are worth narrating.
7. **Frequency floor for entries.** A user with only 30 games in an opening can still be in the top-10 for an inactive player. Does the 50-games floor apply per-entry or per-user (i.e. drop the user from the feature entirely below some total game count)?
8. **Strength inclusion in v1.13 vs deferral.** Strengths are algorithmically free (same query, opposite threshold) but UX-wise they may dilute the actionable signal. Could ship weaknesses-only initially, add strengths in a polish phase.

## Out of Scope for v1.13

- **Population-relative weakness signals.** Argued above. Stays out unless a future user-research finding contradicts the book-move-equality argument.
- **Engine-eval-based weakness detection.** "Engine says +1.5 here but you played a move that drops it to -0.3" requires per-position engine analysis that FlawChess does not import for every game. Could be revisited if the v2+ "human-like engine analysis" todo lands.
- **Time-pressure-as-weakness.** "You lose 70% in this opening when under 30s on the clock" mixes opening prep with time-management skill. Belongs in time-pressure analytics, not opening insights.
- **Opponent-rating-conditioned thresholds.** "55% loss rate vs lower-rated opponents only" is interesting but expands scope into opponent-strength-aware analysis already covered by global filters.
