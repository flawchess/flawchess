# Phase 82: LLM prompt awareness of Endgame Start vs End metrics - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the two Phase 81 metrics through the Endgame Insights LLM pipeline so the narrated **Endgame Overall Performance** section can mention "Where you start" / "What you do with it" alongside Conversion / Parity / Recovery and the score-gap timeline.

Phase 81 was purely additive UI; the LLM narration path was deliberately deferred. Today the visible tiles are in production but `app/services/insights_service.py` emits no findings for either metric and `app/prompts/endgame_insights.md` has no glossary entry or subsection for them — the LLM cannot narrate ~⅓ of the visible Overall Performance section.

Phase 82 adds:

1. A new `endgame_start_vs_end` subsection in `insights_service.py` emitting two findings:
   - **Tile 1 — entry-eval**: `metric=entry_eval_pawns`, value = `entry_eval_mean_pawns`
   - **Tile 2 — endgame-score**: `metric=endgame_score`, value = (W + 0.5·D)/total over endgame games
2. A zone classifier for entry-eval (new `ENDGAME_ENTRY_EVAL_ZONES` ZoneSpec).
3. A `MetricId` rename: existing `endgame_score` → `endgame_score_timeline`, existing `non_endgame_score` → `non_endgame_score_timeline`. The clean `endgame_score` name moves to the new subsection.
4. Prompt update: glossary entries for the two new metrics, a new `### Subsection: endgame_start_vs_end` block under section_id `overall`, updated subsection→section_id mapping table, and a `_PROMPT_VERSION` bump (`endgame_v22` → `endgame_v23`).
5. Phase 81 D-09 tile-color amendment (in-phase): switch `EndgameStartVsEndSection` from "sig-only" coloring to `(value in green/red zone) AND p < 0.05`. Tile and LLM agree on what counts as narratable.
6. Tighten `ENDGAME_ENTRY_EVAL_NEUTRAL_*` from ±0.75 to **±0.50** for both display and LLM (single source of truth).

Phase 82 is **purely additive on the LLM side** — no UI changes beyond the Plan 6 tile-color rule amendment. Backend schema is untouched (Phase 81 already populated the four fields).

</domain>

<decisions>
## Implementation Decisions

### Metric Naming (LOCKED)

- **D-01:** Rename existing `MetricId = "endgame_score"` → **`endgame_score_timeline`**. Currently emitted by `_findings_score_timeline` in `app/services/insights_service.py`; carries no calibrated zone band (always `typical`). The rename signals it is the timeseries variant and frees the clean `endgame_score` name for the new subsection.
- **D-02:** For symmetry, rename existing `MetricId = "non_endgame_score"` → **`non_endgame_score_timeline`**. Same constraint (no band, score_timeline-only). Asymmetric naming would invite future confusion.
- **D-03:** New endgame_start_vs_end Tile-2 metric takes the clean name **`endgame_score`** (the renamed Literal slot). Glossary block in the prompt is freshly written for this — do not carry over the v22 wording for the timeline metric.
- **D-04:** Tile-1 metric is named **`entry_eval_pawns`**. New `MetricId` Literal entry; new glossary block.
- **D-05:** New `SubsectionId = "endgame_start_vs_end"`. Maps to `section_id = "overall"` in the prompt's subsection→section_id mapping table (alongside `overall` and `score_timeline`). The subsection ordering inside section `overall` is: `overall` → `endgame_start_vs_end` → `score_timeline` (chronological narrative: "what overall looks like → setup vs execution snapshot → trajectory over time"). Final ordering decision can iterate during execution; lead with whichever paragraph reads best.

### Verdict Field — REJECTED (LOCKED)

- **D-06:** The seed proposed adding a `verdict: Literal["above_null", "null", "below_null"]` field on `SubsectionFinding` to surface "cohort-typical but high-confidence non-null" cases (the user-28 pattern: `entry_eval=+0.46 inside typical, p<0.001`). **Rejected during /gsd-discuss-phase 82.** Reasoning: significance independent of cohort licenses the LLM to narrate small-but-significant findings, which is exactly the over-emphasis we want to avoid. The `zone` field combined with `sample_quality`/`sample_size` already encodes "is this user different from peers and is the sample big enough to trust." Keep the LLM's narration logic single-axis.
- **D-07:** Sig-test still happens on the backend (Phase 81 D-11 `entry_eval_p_value` and `endgame_score_p_value` are populated and consumed by the tile color logic — see D-15 below). The sig-test outcome is **not** propagated to the LLM payload. The LLM narrates strictly from `zone` + the existing `[near edge]` suffix for borderline cases.

### Zone Bands (LOCKED)

- **D-08 (Tile 1 — entry-eval):** New `ENDGAME_ENTRY_EVAL_ZONES = ZoneSpec(typical_lower=-0.50, typical_upper=+0.50, direction="higher_is_better")` in `app/services/endgame_zones.py`. **Tightened from cohort IQR (±0.75)** on editorial grounds — half-a-pawn average swing at endgame entry is a relevant pattern for narration, even though half the cohort lands inside the IQR. Single global zone (TC max d=0.22, ELO max d=0.28 per benchmark §3 — both "review", single global justified). See `feedback_zone_band_judgement.md` in user memory for the principle.
- **D-09 (Tile 1 — display):** Frontend `frontend/src/lib/endgameEntryEvalZones.ts` `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` constants migrate from ±0.75 to **±0.50**. Tile axis domain stays at ±2.0 (Phase 81 D-15 — outlier headroom is separate from the neutral band). This **amends** Phase 81 D-15's neutral-band choice; Phase 81 is already shipped, so the amendment lands in Phase 82.
- **D-10 (Tile 2 — endgame-score zone):** **Reuse the live shared band** `SCORE_BULLET_NEUTRAL_MIN/MAX = ±0.05` (i.e. `[0.45, 0.55]` around `SCORE_BULLET_CENTER = 0.5`). No per-ELO `ENDGAME_SCORE_ZONES` registry is added in this phase, despite benchmark §0 verdicts saying "keep separate" on ELO (max d=0.84, 800 vs 2400 cohort). Trade-off accepted: pooled IQR `[0.46, 0.56]` overlaps the live band within rounding, and a 2400 user with `score=0.51` reads as `typical` against pooled even though it is below the 2400 cohort p25. Acceptable simplification — the verdict-rejection (D-06) reduces the cost of imprecision. Zone classification dispatches via the existing `assign_zone` path with a one-off `ZoneSpec` registered for `endgame_score` mapped to these bounds (`direction="higher_is_better"`).
- **D-11 (deferred decision):** Per-ELO `ENDGAME_SCORE_ZONES` mirroring `ENDGAME_SKILL_ZONES` is **deferred** to a future phase. Open if a later iteration shows pooled-band false-typical readings that hurt narration. Tracked in Deferred Ideas.

### Tile Color Rule Amendment — Plan 6 IN-PHASE (LOCKED)

- **D-12:** Phase 81 D-09 set tile coloring to `sig positive → green / sig negative → red / not sig → neutral` (sig-only). With the new cohort-band zones (D-08, D-10), the cleaner rule is `(value in green/red zone) AND p < 0.05`. Tile and LLM agree on what is narratable.
- **D-13:** This amendment ships **in-phase** (not as a separate `/gsd-quick`). Reasoning: the LLM finding `zone` and the tile color must agree from day one — shipping the LLM update first leaves users seeing a colored tile with a non-narrating LLM (or vice versa). Frontend changes are small (~30 lines in `EndgameStartVsEndSection.tsx` once `endgameZones.ts` carries the bands).
- **D-14:** Borderline cases handled correctly: a value `+0.46` (inside typical, p<0.001) reads as **neutral on the tile** (D-12: not in green/red band) **and** is not narrated separately (D-06: no verdict field). Consistency between tile and narration replaces the seed's `verdict`-based dual signal.
- **D-15:** Tile-color logic source: `EndgameStartVsEndSection.tsx` (or wherever the per-tile color computation currently lives). Theme constants pulled from `frontend/src/lib/theme.ts` (`ZONE_SUCCESS`, `ZONE_DANGER`, `ZONE_NEUTRAL`) — no new constants.

### Findings Emission (LOCKED)

- **D-16:** New `_findings_endgame_start_vs_end(response, window)` helper in `app/services/insights_service.py`. Returns two `SubsectionFinding` items per window with `subsection_id="endgame_start_vs_end"`, `parent_subsection_id=None`. Wired into `_compute_section_findings` between `_findings_overall_score_gap` and `_findings_score_timeline` so the prompt-rendering order matches D-05.
- **D-17:** Sample-size gate: `entry_eval_n >= 10` for Tile 1, total endgame-game count `>= 10` for Tile 2. Matches Phase 81 D-05 (the project-wide compute/render gate). Below 10 → emit empty finding (`value=NaN`, `zone="typical"`, `sample_quality="thin"`, `is_headline_eligible=False`) per the existing empty-window convention in `SubsectionFinding`.
- **D-18:** Headline eligibility: `is_headline_eligible = sample_quality != "thin"`, mirroring all existing emitters.
- **D-19:** `dimension=None` for both findings (single-aggregate metrics, no per-bucket fan-out).
- **D-20:** `series=None` (these are not timeline metrics — Phase 65 D-02 reserves `series` for `score_timeline`, `clock_diff_timeline`, `endgame_elo_timeline`).
- **D-21:** `findings_hash` recompute is expected — append-only-safe field ordering preserved (D-06 dropped `verdict` so no new fields are introduced; the rename in D-01/D-02/D-03/D-04 changes `metric` Literal values but field declaration order is unchanged). Cache invalidation via `_PROMPT_VERSION` bump (D-23) is automatic.

### Prompt Update (LOCKED)

- **D-22:** Add two glossary entries to `app/prompts/endgame_insights.md` `## Metric glossary`:
  - **`entry_eval_pawns`**: definition (signed Stockfish eval at endgame entry, in pawns, user-POV — positive = user better), units, sign convention, the cohort `±0.50` typical band, mate-row exclusion, the sig-test framing the tile uses (and that the LLM does NOT receive the sig-test outcome — it narrates strictly by zone). Reference the `[near edge]` suffix for borderline cases.
  - **`endgame_score`**: definition (user's Score in endgame-reaching games, on the 0–100% scale, equal-footing baseline = 50%), units, the live shared `[45, 55]` typical band (matches the Openings score bullet for visual parity per Phase 81 D-16), Wilson-test-vs-50% framing on the tile (LLM does NOT receive the sig-test outcome), idle-combo / scoping-caveat applicability.
  - Both entries use the existing whole-number-percentage / per-pawn rendering conventions in the glossary header.
- **D-23:** Add a new `### Subsection: endgame_start_vs_end` block in `app/prompts/endgame_insights.md` (mirroring the existing per-subsection blocks). Crucially:
  - Frame the two metrics as a **"setup → execution"** pair: entry_eval = where the user starts the endgame, endgame_score = what they do with it.
  - Tell the LLM that **both findings together** are interesting (one without the other is half a story). Example narrations: "+0.4 pawns at endgame entry but ends up at 47% — squanders typical advantages" / "−0.3 pawns at entry but lands at 54% — defends well from worse positions".
  - Repeat the within-noise / `[near edge]` rules — narrate borderline cases as "small but real" rather than glossing as "within typical range".
  - Cross-link to the Time Pressure subsection: when entry-eval is strong but endgame-score is weak, check `avg_clock_diff_pct` and `[low-time-gap]` for the time-pressure causal story (the seed flagged this as the user-28 pattern).
- **D-24:** Update the `## Subsection → section_id mapping` table to insert a row `endgame_start_vs_end | overall` between `overall` and `score_timeline`. The order reflects D-05.
- **D-25:** Bump `_PROMPT_VERSION` from `endgame_v22` → **`endgame_v23`** with a one-line changelog entry following the existing format. Changelog text: "v23 (260510 endgame_start_vs_end): wire Phase 81 entry-eval and endgame-score metrics into the LLM payload via a new `endgame_start_vs_end` subsection under section_id `overall`. Renamed score_timeline `endgame_score` → `endgame_score_timeline` and `non_endgame_score` → `non_endgame_score_timeline` to free the clean `endgame_score` name for the new subsection. Tile color rule amended from sig-only to `zone × p<0.05` (Phase 81 D-09 amendment). EG-entry-eval neutral band tightened from ±0.75 to ±0.50 for both tile and LLM."

### Plan Shape (Claude's discretion — refine during /gsd-plan-phase)

Provisional plan breakdown (4 plans):
- **Plan 1 — Backend:** MetricId / SubsectionId rename + ZoneSpec registration + `_findings_endgame_start_vs_end` emitter + insights_service tests.
- **Plan 2 — Prompt:** glossary entries + subsection block + mapping-table update + `_PROMPT_VERSION` bump + prompt fixture updates.
- **Plan 3 — Frontend:** `endgameEntryEvalZones.ts` constants tightened to ±0.50 + tile-color rule amendment in `EndgameStartVsEndSection.tsx` + component tests.
- **Plan 4 — UAT + CHANGELOG:** manual UAT (run a live insights request against the dev DB, verify the LLM narrates both findings; visual check that user-28-style borderline-but-sig values now read as neutral on the tile and are not narrated; check no regression on the Conv/Parity/Recovery section), CHANGELOG entry under `## [Unreleased]`.

Planner refines wave dependencies during /gsd-plan-phase 82.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and design history
- `.planning/seeds/SEED-013-llm-prompt-awareness-of-endgame-start-vs-end.md` — original seed (2026-05-10). **Partly amended:** the `verdict` field design (seed Plan 4) is rejected (D-06); per-ELO `ENDGAME_SCORE_ZONES` (seed Plan 3) is deferred (D-11); Plan 6 lands in-phase (D-13). Other plan content still applies.
- `.planning/phases/81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table/81-CONTEXT.md` — Phase 81 decisions D-01..D-22. Phase 82 amends D-09 (tile color rule) and D-15 (entry-eval neutral band). All other Phase 81 decisions stand.
- `.planning/ROADMAP.md` lines 103–112 — Phase 82 entry under v1.16 milestone.

### Population reference data
- `reports/benchmarks-2026-05-10.md` §0 (Endgame score, per-user) — pooled `[p25, p75] = [0.4627, 0.5581]`; ELO max d=0.84 ("keep separate"); per-ELO `[p25, p75]` ramp 800: `[0.42, 0.52]` → 2400: `[0.50, 0.58]`. **Used to justify D-10 trade-off and D-11 deferral.**
- `reports/benchmarks-2026-05-10.md` §3 EG entry — pooled (uncentered, matches live tile) `[p25, p75] = [-0.56, +0.75]` cp; TC d=0.22, ELO d=0.28 ("review" both). **Used to justify D-08 single-global zone; tightening from IQR ±0.75 to ±0.50 is editorial (D-08 reasoning).**
- `.claude/skills/benchmarks/SKILL.md` — canonical benchmark methodology. Already updated in Phase 78+.

### Backend integration points
- `app/services/insights_service.py` — finding emitters. Add `_findings_endgame_start_vs_end` here; wire into `_compute_section_findings`. Reference `_findings_score_timeline` (lines 432–567) for the canonical empty-window pattern.
- `app/services/endgame_zones.py` — `MetricId` Literal (line 30), `SubsectionId` Literal (line 51), `ZoneSpec` dataclass (line 75), `assign_zone` dispatch. **Renames in D-01/D-02 land here.** New `ENDGAME_ENTRY_EVAL_ZONES` ZoneSpec registered for `entry_eval_pawns` MetricId.
- `app/schemas/insights.py` — `SubsectionFinding` (line 150). **No new fields** (D-06). The `metric: MetricId` field accepts the renamed Literal values automatically.
- `app/services/insights_llm.py` line 66 — `_PROMPT_VERSION` bump (D-25).
- Phase 81 D-22 entry-eval aggregation source: `_get_endgame_performance_from_rows` consumes `query_endgame_bucket_rows` for chronologically-first-eval-per-game. **No backend aggregation changes in Phase 82.**

### Frontend integration points
- `frontend/src/lib/endgameEntryEvalZones.ts` — `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` constants migrate from ±0.75 to ±0.50 (D-09).
- `frontend/src/components/charts/EndgameStartVsEndSection.tsx` (or wherever Phase 81 placed the per-tile color logic — planner: locate exact filename) — tile color amendment (D-12, D-13).
- `frontend/src/lib/scoreBulletConfig.ts` — `SCORE_BULLET_NEUTRAL_MIN/MAX/CENTER` constants. **Untouched.** Phase 82 reuses these for endgame_score zone bounds (D-10) but the constants are owned by the openings page.
- `frontend/src/lib/theme.ts` — `ZONE_SUCCESS`, `ZONE_DANGER`, `ZONE_NEUTRAL`. **Untouched.** Tile color amendment uses existing constants.
- `frontend/src/generated/endgameZones.ts` — auto-generated. After updating `app/services/endgame_zones.py`, run `uv run python scripts/gen_endgame_zones_ts.py` (CI fails on drift — see CLAUDE.md "Scripts" section).

### Prompt
- `app/prompts/endgame_insights.md` — glossary section (line 268), subsection→section_id mapping (line 330). New glossary blocks added; new `### Subsection: endgame_start_vs_end` block added; mapping table updated (D-22, D-23, D-24).

### Test fixtures
- `tests/services/test_insights_service.py` — existing tests for finding emitters. Renames in D-01/D-02 will churn assertions matching the old metric names. New tests for `_findings_endgame_start_vs_end`.
- Prompt fixtures (planner: locate exact path — likely `tests/services/test_insights_llm.py` or `tests/fixtures/insights/`) carry the v22 baseline; the v23 bump invalidates them.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`SubsectionFinding`** schema (`app/schemas/insights.py:150`): drop-in. No new fields needed (D-06).
- **`assign_zone`** dispatch in `app/services/endgame_zones.py`: new `entry_eval_pawns` MetricId registers a `ZoneSpec`; classification works automatically. `endgame_score` shares the existing `assign_zone` path.
- **`_findings_score_timeline`** pattern (`insights_service.py:432–567`): canonical reference for non-bucketed, single-aggregate finding emitters with empty-window handling. New `_findings_endgame_start_vs_end` mirrors this shape.
- **Phase 81 D-22 bucket-rows aggregation** (`_get_endgame_performance_from_rows`): the four entry-eval / endgame-score-p-value fields are already populated on `EndgamePerformanceResponse`. Phase 82 only consumes them — no backend aggregation changes.
- **`[near edge]` suffix logic** (existing in the prompt): the LLM already knows how to narrate borderline cases. The new subsection block reuses this convention rather than introducing a new vocabulary.
- **Phase 81 popovers** (`BulletConfidencePopover`, `ScoreConfidencePopover`): unchanged. Tile-color amendment doesn't touch popover content (n / p-value still surfaced inside).

### Established Patterns
- **MetricId rename across services + tests + prompt + fixtures**: precedent in v18 (`260501-s0u`) when `type_win_rate_timeline` was deprecated. Same shape — find/replace in services + targeted tests + prompt glossary + bump version.
- **Single-aggregate findings (no series, no dimension)**: established by `endgame_metrics`'s `endgame_skill` finding (`insights_service.py:599–614`). Mirror that shape for both new findings.
- **Tile color rule amendment (sig-only → zone × sig)**: precedent in the Openings score bullet (already uses `(value in band) AND confidence>=medium`). Phase 82 brings the Endgames page in line.
- **`ZoneSpec` for non-percentage metrics**: the existing `MetricId = "score_gap"` registers a ZoneSpec in pp units. `entry_eval_pawns` follows the same shape but in pawn units. Document the unit explicitly in the docstring.
- **`_PROMPT_VERSION` bump on every prompt-affecting change**: every preceding version bump (v17–v22) is tagged with date + a one-line changelog. v23 follows that template.

### Integration Points
- **Insights pipeline**: `_compute_section_findings` aggregates per-window finding lists. Add the new emitter call between `_findings_overall_score_gap` and `_findings_score_timeline` (D-16).
- **Findings hash**: deterministic over the metric Literal values + field ordering. Renames + new emitter both invalidate v22 caches; the prompt_version bump invalidates LLM-side caches. Aligns automatically.
- **Frontend zone re-generation**: after `endgame_zones.py` edits, run `scripts/gen_endgame_zones_ts.py` and commit the regenerated `frontend/src/generated/endgameZones.ts`. CI enforces non-drift.

</code_context>

<specifics>
## Specific Ideas

- **The "setup → execution" framing is the LLM hook.** The two metrics are individually nuanced but together tell a clean story (entry-eval = setup; endgame-score = execution). The subsection block should explicitly cue this pairing — without it, the LLM will treat them as two unrelated bullets.
- **Cross-link to Time Pressure in the prompt.** The seed flagged the user-28 pattern: strong entry-eval + weak endgame-score → look at clock-diff and `[low-time-gap]`. The prompt should license this cross-section reading, not duplicate the work.
- **Tile color = LLM zone is non-negotiable.** When a value sits inside the tightened ±0.50 band, the tile is neutral AND the LLM is silent (or narrates only via `[near edge]`). When a value is outside the band AND p<0.05, the tile is colored AND the LLM narrates. No "tile says X, LLM says Y" mismatches.
- **Borderline narration uses the existing `[near edge]` suffix.** Don't invent new vocabulary. The user explicitly endorsed band-edge + sig as narratable.
- **Don't add per-ELO score zones now.** D-10 trades precision for simplicity. If a future user shows a clearly-mis-classified pattern (a 2400 user reading typical against pooled but weak against same-ELO peers), revisit.

</specifics>

<deferred>
## Deferred Ideas

- **Per-ELO `ENDGAME_SCORE_ZONES` mirroring `ENDGAME_SKILL_ZONES`.** Benchmark §0 says "keep separate" on ELO (max d=0.84). Open if the pooled `[0.45, 0.55]` band shows mis-classification on real users. Mechanical to add (mirrors `ENDGAME_SKILL_ZONES` registry pattern). Tracked as a future seed if needed.
- **`verdict` / sig-test field on `SubsectionFinding`.** Considered and rejected (D-06). Open only if a future use case genuinely requires the LLM to narrate cohort-typical findings — and even then, prefer band tightening first.
- **Per-TC entry-eval bands.** Benchmark §3 verdict is "review" on TC, not "keep separate." Single global band stands. Revisit if a TC-specific pattern emerges.
- **Distribution / histogram view of per-game evals on the Endgame page.** Already deferred from Phase 81 (Phase 81 deferred ideas section). Phase 82 doesn't change this.
- **Pre-endgame eval over time chart** (analog of `EndgameScoreOverTimeChart` for entry eval). Phase 81 deferred. Phase 82 doesn't change this.
- **LLM cross-section "composure-under-pressure" flag combining entry_eval × low-time-gap.** A precomputed cross-section signal would replace the cross-link prose in D-23. Out of scope — the prompt can derive the cross-section story from the raw findings.

</deferred>

---

*Phase: 82-LLM prompt awareness of Endgame Start vs End metrics*
*Context gathered: 2026-05-10*
