# Phase 76: Frontend — score-based coloring, confidence badges, label reframe - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning
**Requirements:** INSIGHT-UI-01, INSIGHT-UI-02, INSIGHT-UI-03, INSIGHT-UI-05, INSIGHT-UI-06, INSIGHT-UI-07 (INSIGHT-UI-04 descopes — see D-04).

<domain>
## Phase Boundary

Frontend rewire of Move Explorer (arrow color, row tint, new confidence column) and Opening Insights cards/section titles to consume Phase 75's score + confidence + p_value contract. Plus one targeted backend extension: the moves explorer payload (`NextMoveEntry`) gains `confidence` and `p_value` fields so the new "Conf" column can render without re-implementing the trinomial Wald formula in TypeScript.

Concretely, the phase delivers four coupled changes:

1. **Score-based arrow color and row tint.** `arrowColor.ts:getArrowColor()` body migrates from win/loss-rate thresholds to score-based effect-size thresholds (the Phase 75 additive exports `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE` already exist). Move Explorer moves-list row tint follows the same encoding. WDL bars on each row stay unchanged — they remain the literal-data display.

2. **Confidence indicator on moves-list rows.** Backend extends `query_top_openings_sql_wdl` to compute `confidence` and `p_value` per surviving move, via a new shared helper module `app/services/score_confidence.py` (Phase 75's `_compute_confidence` migrates here). `NextMoveEntry` schema gains `confidence: Literal["low","medium","high"]` and `p_value: float`. Frontend renders a new "Conf" column between Games and Results, plain small grey text labels `low / med / high`, both desktop and mobile.

3. **Confidence on Opening Insights cards + sort.** `OpeningFindingCard` adds a "Confidence: low/medium/high" line under the score prose with a level-specific hover tooltip. Card prose migrates from `You lose/win X%` to `You score X%` (same form both sections; X% = `round(score * 100)`). `compute_insights` re-sorts each section by `confidence DESC, then |score - 0.50| DESC`. Section titles stay verbatim ("White Opening Weaknesses", etc.) — the badge + sort carry the calibration that SEED-008 wanted from softened labels.

4. **Mute rule + explainer popovers.** Rows AND cards apply existing `UNRELIABLE_OPACITY = 0.5` (theme.ts) when `n_games < 10` OR `confidence === "low"`. Four `InfoPopover` icons, one per section title in `OpeningInsightsBlock`, all showing the same score+effect-size+confidence framing copy (single constant, DRY).

Stale-code cleanup folded into scope: `OpeningFindingCard.tsx:26` reads removed `loss_rate`/`win_rate` (currently broken vs Phase 75 backend); `MIN_GAMES_FOR_INSIGHT = 20` and `INSIGHT_THRESHOLD_COPY` in `openingInsights.ts` are stale (backend dropped to 10).

</domain>

<decisions>
## Implementation Decisions

### Section titles, card copy, sort order

- **D-01:** Section titles unchanged — keep "White Opening Weaknesses" / "Black Opening Weaknesses" / "White Opening Strengths" / "Black Opening Strengths". The roadmap proposed soft labels per SEED-008 ("Worth a closer look", "Played confidently"). Rejected during discuss-phase: once we add a confidence indicator AND sort high-confidence cards on top, the existing "Weakness/Strength" framing is justified — confidence + sort carry the calibration.
- **D-02:** Card prose migrates to score: `You score X% as White after <san>` for both weakness and strength sections. X% = `round(finding.score * 100)`. Same form regardless of section because score is a symmetric metric around 0.50; the section title tells the user which side they're reading. The score color (red below 50, green above) renders via the existing `getSeverityBorderColor` border-tint, unchanged.
- **D-03:** Sort within each section: `confidence DESC, then |score − 0.50| DESC`. `high → medium → low`, ties broken by effect size. Implemented in `compute_insights` in `opening_insights_service.py` (backend already orders findings before returning the four-section payload — backend tests would break if frontend re-sorted).
- **D-04 (descopes INSIGHT-UI-04):** "Soften severity copy per SEED-008" descopes to a no-op. Severity word ("major"/"minor") never appears as user-facing text today (only drives border color); it stays that way. INSIGHT-UI-04 is satisfied by the badge + sort calibration in D-01..D-03.

### Confidence on moves-list rows (INSIGHT-UI-03)

- **D-05:** Backend extends the moves explorer payload — `NextMoveEntry` gains `confidence: Literal["low","medium","high"]` and `p_value: float`, mirroring the `OpeningInsightFinding` contract from Phase 75 D-09. Single source of truth for the trinomial Wald formula; the frontend doesn't re-implement it.
- **D-06:** Phase 75's `_compute_confidence` helper migrates to a new module `app/services/score_confidence.py`. Both `opening_insights_service.compute_insights` AND the moves explorer query path import from it. Pure helper, no dependencies; matches the project's `query_utils.py` pattern (one shared utility module per cross-cutting concern). Phase 75's anti-pattern lock against duplicating the formula stays satisfied.
- **D-07:** Confidence is computed Python-side, post-aggregation, after `query_top_openings_sql_wdl` returns. No SQL push — consistent with Phase 75 D-07 (single language for the formula).
- **D-08:** New "Conf" column added to the Move Explorer table, positioned between the Games column and the Results (WDL bar) column. Visible on both desktop and mobile. Labels: `low` / `med` / `high`, plain small grey text, no parens, no pill, no level-specific color. Header text: "Conf" (matches the abbreviated label form for narrow viewports).

### Confidence on Opening Insights cards (INSIGHT-UI-05)

- **D-09:** `OpeningFindingCard` adds a new line under the score prose: `Confidence: low/medium/high` (full words, not abbreviated). Same plain grey style — no pill, no level-specific color tied to the badge.
- **D-10:** Hover tooltip on the "Confidence: …" indicator with level-specific short copy:
  - `low` → "small sample, treat as a hint"
  - `medium` → "enough games to trust the direction"
  - `high` → "sample is large enough to trust the magnitude"

  Reuses the existing tap-friendly tooltip pattern (matches the FilterPanel/charts InfoPopover and the MoveExplorer TranspositionInfo popover styling). Renders the level-specific string at runtime keyed off `finding.confidence`.

### Mute rule

- **D-11:** Apply the existing `UNRELIABLE_OPACITY = 0.5` (already in `theme.ts`) to a row OR card when `n_games < 10` OR `confidence === "low"`. Reuses the existing mute mechanism — no new theme constants. Net effect: low-confidence findings still surface (discovery framing per Phase 75 D-04) but are visually de-emphasised. The opacity merge with `tintColor` and the deep-link pulse stays as today (`MoveExplorer.tsx:238-253`).

### Score-based coloring (INSIGHT-UI-01, INSIGHT-UI-02)

- **D-12:** `getArrowColor()` body in `arrowColor.ts` migrates to score-based effect-size buckets, using the additive exports from Phase 75 D-12:
  - `score >= SCORE_PIVOT + MAJOR_EFFECT_SCORE` (≥ 0.60) → `DARK_GREEN`
  - `score >= SCORE_PIVOT + MINOR_EFFECT_SCORE` (≥ 0.55) → `LIGHT_GREEN`
  - `score <= SCORE_PIVOT - MAJOR_EFFECT_SCORE` (≤ 0.40) → `DARK_RED`
  - `score <= SCORE_PIVOT - MINOR_EFFECT_SCORE` (≤ 0.45) → `LIGHT_RED`
  - else → `GREY`

  Strict `≥` / `≤` boundaries (matches Phase 75 D-03 / D-11 backend behavior). The `MIN_GAMES_FOR_COLOR < gameCount` guard stays. Hover blue stays.
- **D-13:** Function signature change: `getArrowColor(score, gameCount, isHovered)` — drop `winPct` and `lossPct` parameters since score is the canonical input. Move Explorer's call site (`MoveExplorer.tsx:228`) updates to pass `entry.score` instead of `entry.win_pct, entry.loss_pct`. `NextMoveEntry` schema gains a `score: float` field on the backend (mirrors Phase 75 D-09 — score is also computed by the moves repository alongside confidence; trivially derived from the existing W/D/L aggregates).
- **D-14:** Move Explorer moves-list row tint uses the same `getArrowColor()` output as the arrows (existing pattern in `MoveExplorer.tsx:228-230`); no separate logic. Score-based.
- **D-15:** Old constants `LIGHT_COLOR_THRESHOLD` and `DARK_COLOR_THRESHOLD` are removed from `arrowColor.ts` (Phase 75 D-13 deferred this — they were kept alive only because the function body still used them). The CI consistency test (`tests/services/test_opening_insights_arrow_consistency.py`) had its `LIGHT_COLOR_THRESHOLD` / `DARK_COLOR_THRESHOLD` assertions removed in Phase 75 D-13, so removing the constants completes that cleanup.

### Explainer popover (INSIGHT-UI-06)

- **D-16:** Four `InfoPopover` icons, one per section title in `OpeningInsightsBlock` (`white-weaknesses`, `black-weaknesses`, `white-strengths`, `black-strengths`). All four show the same copy. Rationale: matches the existing pattern on other Stats tabs (no block-level title with a single ?). Reuses the existing `InfoPopover` component (`frontend/src/components/ui/info-popover.tsx`); no new component.
- **D-17:** Popover copy lives in a single exported constant in `openingInsights.ts` (replacing the now-stale `INSIGHT_THRESHOLD_COPY`) so all four popovers reference the same string. Draft A — score-first three-paragraph framing:

  > **Score** is (W + ½D) / N. 50% means you and your opponents broke even.
  >
  > A finding shows up when your score sits at least 5% from 50% — enough of a gap that it's probably not random.
  >
  > **Confidence** says how big the sample is. *Low* findings are worth a glance; *high* findings are well-supported.

  Markdown-style emphasis stays inline (matches existing `InfoPopover` consumers that render React fragments with bold/italic). Wording tweaks during planning/execution are fine; the framing (score → effect-size gate → confidence as sample-size cue) is locked.
- **D-18:** No block-level "Opening Insights" title is added (rejected during discuss-phase for consistency with the other Stats tabs, which don't have one).

### Stale-code cleanup (folded into scope)

- **D-19:** `OpeningFindingCard.tsx:26` currently reads `finding.loss_rate` / `finding.win_rate` — both fields removed by Phase 75 D-09. The card has been broken since Phase 75 backend shipped; D-02 prose migration fixes this naturally (re-derives from `score`).
- **D-20:** `frontend/src/lib/openingInsights.ts` cleanup:
  - `MIN_GAMES_FOR_INSIGHT = 20` → update to `10` (matches `OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE`); rename if it's used as a "show this number to user" string. Verify call sites; if it's purely a comment / informational constant, keep the name and update the value.
  - `INSIGHT_RATE_THRESHOLD = 55` → remove (no longer the metric); replace any consumer with the new score-based exports from `arrowColor.ts`.
  - `INSIGHT_THRESHOLD_COPY` → remove (its content is replaced by the popover copy from D-17). Verify no dangling consumers.
- **D-21:** `frontend/src/types/insights.ts` `OpeningInsightFinding` interface — remove `loss_rate` and `win_rate` fields (lines 85-86); add `confidence: 'low' | 'medium' | 'high'`, `p_value: number`. Already done implicitly by Phase 75's API contract; the frontend type just hasn't caught up.

### CI consistency test (extends Phase 75 D-13 scope)

- **D-22:** `tests/services/test_opening_insights_arrow_consistency.py` is extended to also assert that the moves-explorer payload's `confidence` field comes from the same `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH` / `OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH` constants the insights service uses. Concretely: the test verifies both backend call sites (`compute_insights` and the moves explorer service) call the same `score_confidence.py` helper, so divergence is structurally impossible. If this test grows brittle, replace the assertion with a unit test of `score_confidence.compute_confidence_bucket()` covering boundary cases (half_width = 0.10 exact, = 0.20 exact, n=10 floor).

### Out-of-scope clarifications

- **D-23:** Arrows on the chessboard stay confidence-agnostic — no opacity, dashing, or dotting cue (per design note "Rejected: confidence cue on board arrows"). Arrows show effect size only (color intensity). Confidence lives on insight cards and moves-list rows.
- **D-24:** No changes to `_dedupe_continuations`, `_dedupe_within_section`, attribution pipeline, section caps. The metric / sort changes are scoped to `_classify_row`, `compute_insights`'s ordering, and the API field set — everything else is metric-agnostic and untouched.
- **D-25:** Mobile parity (INSIGHT-UI-07) is satisfied by D-08 (Conf column visible at 375px), D-09 (Confidence line wraps in card prose area), D-16 (InfoPopover already mobile-tested via FilterPanel/charts usage), and the existing UNRELIABLE_OPACITY mute rule (D-11) which is viewport-agnostic.

### Claude's Discretion

- The exact pixel width of the "Conf" column on mobile (responsive Tailwind classes) — pick something that doesn't blow past 375px when combined with the existing Move + Games + WDL columns.
- Whether the level-specific tooltip (D-10) renders via `Tooltip` (used by `OpeningFindingCard` linksRow already) or a small custom span. `Tooltip` is the obvious pick unless touch-only behavior breaks.
- Score-prose rounding edge cases (e.g. score = 0.499 → display "50%" but classified as weakness): rounding at display time is a one-liner; just be consistent so the displayed % never contradicts the section the card sits in. If it does, fall back to `.toFixed(1)`.
- Whether the Conf column header itself gets a small InfoPopover or just title-tooltip — the section-title popover (D-16) already covers the framing, so a column-header tooltip is optional decoration.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 75 backend lock-in (consumed by Phase 76 frontend)

- `.planning/phases/75-backend-score-metric-confidence-annotation/75-CONTEXT.md` — Phase 75 D-01..D-16. Locks the `score` / `confidence` / `p_value` contract, the trinomial Wald formula, the bucket boundaries, and the anti-pattern against duplicating the formula. Phase 76's D-05/D-06/D-07 directly extend Phase 75's D-07/D-09.
- `.planning/notes/opening-insights-v1.14-design.md` — milestone-level design lock. Authoritative on (a) "arrows are effect-size only, no confidence cue", (b) "score is the canonical metric across all surfaces", (c) "discovery framing — low-confidence still surfaces but de-emphasised". Phase 76 D-23 cites this.

### Milestone

- `.planning/milestones/v1.14-ROADMAP.md` — Phase 76 success criteria + open questions list.
- `.planning/REQUIREMENTS.md` — INSIGHT-UI-01..07. Note: INSIGHT-UI-04 descopes per D-04 — apply the amendment at Phase 76 commit time.

### Style and prompt-tone references

- User memory `feedback_llm_prompt_design.md` — point #5 ("Percent/rate metrics pass through as 0-100, not 0-1") and #6 ("Whole-number percents end-to-end, no 'pp' unit") inform D-02 and D-17 copy form.

### Code touched by Phase 76

Backend:
- `app/services/score_confidence.py` — NEW module per D-06. Houses `compute_confidence_bucket(w, d, l, n) -> tuple[Literal["low","medium","high"], float]` (returns `(bucket, p_value)`). Migrates Phase 75's `_compute_confidence`.
- `app/services/opening_insights_service.py` — `compute_insights` re-sort per D-03; import switches from local `_compute_confidence` to `score_confidence.compute_confidence_bucket`.
- `app/repositories/openings_repository.py` — `query_top_openings_sql_wdl` returns the raw counts for the new payload computation; no schema-level change to the SQL.
- A moves-explorer service or the existing query path — applies `score_confidence.compute_confidence_bucket` to each `NextMoveEntry` post-aggregation.
- `app/schemas/openings.py` (or wherever `NextMoveEntry` is defined) — add `score: float`, `confidence: Literal["low","medium","high"]`, `p_value: float`.

Frontend:
- `frontend/src/lib/arrowColor.ts` — `getArrowColor()` body rewrite (D-12); signature change (D-13); remove `LIGHT_COLOR_THRESHOLD` / `DARK_COLOR_THRESHOLD` (D-15).
- `frontend/src/lib/openingInsights.ts` — clean up stale constants (D-20); add the popover copy constant (D-17).
- `frontend/src/types/insights.ts` — `OpeningInsightFinding` field changes (D-21); `NextMoveEntry` (in the relevant types file) gets `confidence` + `p_value` + `score`.
- `frontend/src/components/move-explorer/MoveExplorer.tsx` — new "Conf" column (D-08); `getArrowColor` call-site update (D-13); mute rule extends to `confidence === "low"` (D-11).
- `frontend/src/components/insights/OpeningFindingCard.tsx` — prose migration (D-02); new "Confidence: …" line (D-09) + tooltip (D-10); mute rule (D-11).
- `frontend/src/components/insights/OpeningInsightsBlock.tsx` — four `InfoPopover` icons next to section titles (D-16).

Tests:
- `tests/services/test_opening_insights_arrow_consistency.py` — extension per D-22.
- `tests/services/test_opening_insights_service.py` — update sort assertions per D-03; ensure existing tests still pass under the rewritten compute_insights ordering.
- A new `tests/services/test_score_confidence.py` — unit tests for the migrated helper covering boundary cases.
- Frontend Vitest tests for `OpeningFindingCard` (prose change), `MoveExplorer` (new column, mute extension), `arrowColor` (score-based mapping).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`InfoPopover`** (`frontend/src/components/ui/info-popover.tsx`) — already shared and tap-friendly. D-16 reuses it directly; the "shared HelpPopover" question from the roadmap is answered.
- **`UNRELIABLE_OPACITY` and `MIN_GAMES_FOR_RELIABLE_STATS`** (`frontend/src/lib/theme.ts:74-77`) — D-11 reuses both, no new constants needed.
- **Phase 75 additive exports in `arrowColor.ts`** (`SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE`, `MIN_GAMES_FOR_COLOR = 10`) — already in place. D-12 plugs into them.
- **Existing row tint pattern in `MoveExplorer.tsx:222-253`** — combines opacity (unreliable) with tintColor (severity) with optional pulse. D-11 just extends the trigger condition; the merge logic stays.
- **`Tooltip` component used by `OpeningFindingCard.tsx:68,80`** — D-10 reuses it for the per-card confidence tooltip.

### Established Patterns

- Two-column desktop / stacked mobile layout in `OpeningFindingCard` (`OpeningFindingCard.tsx:103-130`) — the new "Confidence: …" line slots into the existing prose flex column on both layouts.
- Move Explorer's `<table>` structure with `<th>`/`<td>` columns — adding "Conf" is mechanical (one new column header + one new cell per row).
- The `getSeverityBorderColor` helper (`openingInsights.ts:19`) maps `(classification, severity) → hex` — already mirrors `getArrowColor`'s shade scheme. After D-12, this helper can be simplified to read directly from score buckets, but that's a Claude's-discretion cleanup, not a locked decision.

### Integration Points

- `compute_insights` in `opening_insights_service.py` already builds the four-section response. D-03 just changes the sort key; the response shape stays.
- The moves explorer endpoint already returns `NextMoveEntry[]`. D-05 adds three fields; consumers (`MoveExplorer.tsx`) read them but the existing fields stay.

</code_context>

<specifics>
## Specific Ideas

- Card prose final form (D-02): `You score 38% as White after 1.e4 c6` — both sections, X% rounded.
- Conf column header text: literally "Conf" (D-08).
- Conf column labels: `low` / `med` / `high` — note `med` is abbreviated; full word `medium` only appears on the card (D-09).
- Card line label: literally "Confidence: " followed by the level word (D-09).
- Tooltip strings (D-10): exact text locked above; refine inline during execution if a beta tester finds them confusing.
- Section-title popover copy (D-17): Draft A score-first three-paragraph form, exact text locked above.

</specifics>

<deferred>
## Deferred Ideas

- **`getSeverityBorderColor` simplification** — after D-12 lands, the helper could read directly from score buckets instead of mapping `(classification, severity) → hex`. Tracked as Claude's discretion in execution; revisit if the helper grows brittle.
- **Calibrating the `low / medium / high` bucket boundaries against real data** — already deferred from Phase 75 (`75-CONTEXT.md` Deferred Ideas). Recheck after Phase 76 ships and we have telemetry on which buckets findings land in across real users.
- **Extending the `(low) / (medium) / (high)` cue to other chart surfaces** (e.g. WinRateChart, EndgameTimelineChart) — out of scope for v1.14; would need its own design pass if ever pursued.
- **Surfacing raw p-value or half-width to power users** — explicitly rejected in design note. Stays out.
- **LLM narration over opening findings** — already a future seed beyond v1.14.

</deferred>

---

*Phase: 76-frontend-score-coloring-confidence-badges-label-reframe*
*Context gathered: 2026-04-28*
