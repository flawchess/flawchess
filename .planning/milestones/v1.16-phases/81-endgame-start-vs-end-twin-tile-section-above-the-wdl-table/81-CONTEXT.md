# Phase 81: Endgame Start vs End — twin-tile section above the WDL table - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a new **Endgame Start vs End** section to the *Endgame Overall Performance* area of the Endgames page, positioned **above** the existing "Games with vs without Endgame" WDL table. The section renders two tiles via the existing `MiniBulletChart`:

1. **"Where you start"** — avg eval at endgame entry (pawns), tested against 0
2. **"What you do with it"** — absolute endgame score (%), tested against 50% (equal-footing break-even)

Both tiles use three-state color (sig positive → green / sig negative → red / not sig → neutral) and reuse the established Openings-page popover pattern (`BulletConfidencePopover` + `ScoreConfidencePopover`) for confidence details.

This phase is **purely additive**. The existing WDL table (incl. Score Gap column) and the "Endgame vs Non-Endgame Score over Time" chart remain unchanged.

</domain>

<decisions>
## Implementation Decisions

### Section Composition (LOCKED)

- **D-01:** Section sits inside *Endgame Overall Performance*, immediately above the existing WDL table. New section, additive — no restructuring of the existing WDL table or the score-over-time chart.
- **D-02:** Section heading: **"Endgame Start vs End"** (matches the phase name; H3 / `<h2>` matching the existing `Endgame Overall Performance` heading style on the page).
- **D-03:** No standalone lead paragraph under the section heading and no section-level info popover. The concepts accordion + per-tile popovers carry the explanation.
- **D-04:** Two tiles side-by-side on desktop (≥`lg`), stacked vertically on mobile.

### Per-Tile Composition (LOCKED — matches Openings ExplorerTab pattern)

Each tile renders:

1. **Punchy title** at the top of the tile (Tile 1: "Where you start", Tile 2: "What you do with it").
2. **Inline value row** matching `frontend/src/pages/openings/ExplorerTab.tsx` rows 2 & 3:
   - Label + numeric value (colored by sig-test verdict zone) + popover icon
   - Tile 1 label: "Avg eval at endgame entry"; popover = `BulletConfidencePopover` (existing — already shows n, p-value, confidence inside)
   - Tile 2 label: "Endgame score"; popover = `ScoreConfidencePopover` (existing — same)
3. **`MiniBulletChart`** below the inline value row — same component as Openings ExplorerTab uses for eval and score bullets. No new chart component.
4. **No standalone stats line** ("n=… · p<0.05") — n and p-value live INSIDE the existing popovers. Don't duplicate.

- **D-05:** **n ≥ 10** is the gate for both compute and render — matches the project's existing chess-score / eval-bullet convention everywhere else. Overrides the n=30 figure from the obsolete design note. The planner should reconcile this with the existing `wilson_score_confidence` helper and the eval-bullet code path so all three are consistent.
- **D-06:** Empty / sparse states:
  - `n < 10` on a tile → tile renders the same "Not enough data yet" placeholder used elsewhere in the codebase (look at the existing eval-bullet / score-bullet sparse rendering for the canonical phrasing and structure).
  - Both tiles have zero data (no endgame games at all) → hide the entire section.
  - Mixed sparse (one tile <10, the other ≥10) is essentially impossible in practice: n is the same for both unless Stockfish failed to evaluate the entry position during import. If it ever happens, render both tiles with the empty one showing the placeholder — keeps layout stable.

### Sig-Test Verdicts (LOCKED — from ROADMAP.md)

- **D-07:** Tile 1 (entry eval): one-sample test of mean against 0, Wald z. Mate scores excluded (`eval_cp NOT NULL`).
- **D-08:** Tile 2 (endgame score): Wilson score test against 50% (the equal-footing break-even line under rating-matched opponents).
- **D-09:** Three-state color: sig positive → green (`ZONE_SUCCESS`), sig negative → red (`ZONE_DANGER`), not sig → neutral gray (`ZONE_NEUTRAL`). Reuse the existing theme constants in `frontend/src/lib/theme.ts`.
- **D-10:** Significance threshold: p < 0.05.

### Backend Additions (LOCKED — from ROADMAP.md)

- **D-11:** `EndgamePerformanceResponse` gains:
  - `entry_eval_mean_pawns: float`
  - `entry_eval_n: int` (mate excluded, `eval_cp NOT NULL`)
  - `entry_eval_p_value: float | None` (Wald z; None when n < 10)
  - `endgame_score_p_value: float | None` (Wilson score test against 50%; None when n < 10)
- **D-12:** Aggregation reuses the existing `first_endgame` ply walk in `app/repositories/endgame_repository.py` (the same SQL path conv/parity/recov use). One additional column in that query path — not a new pipeline.

### Concept-Explainer Accordion (LOCKED)

- **D-13:** Add two paragraphs to the existing `endgame-concepts-trigger` accordion in `frontend/src/pages/Endgames.tsx`:
  - **"Avg eval at endgame entry"** — explain Stockfish-eval-at-entry concept, equal-footing baseline (~0 cp), what positive/negative values mean from the user's perspective, sig-test verdict ("we can't tell" framing for the null), mate exclusion. The phrasing in `.planning/notes/endgame-entry-eval-tile-design.md` §"Concept-explainer accordion" is a strong starting point — final wording refined during execution.
  - **"Absolute endgame score"** — explain the 50% break-even line under rating-matched opponents, how the Wilson score test detects deviation, "we can't tell" null framing. Note the link to the Opponent Strength filter for tightening the test.
- **D-14:** Place both new paragraphs after the existing Conversion / Parity / Recovery paragraphs and before the trailing rating-changes caveat paragraph.

### Visual / Axis Defaults (Claude's discretion — iterate during execution / UI review)

- **D-15:** Pawn-axis domain for Tile 1: **±2.0 pawns**. Per `.planning/notes/endgame-entry-eval-tile-design.md`, this fits typical user data (per-user means cluster well within `[−0.5, +0.5]` under equal-footing) with headroom. Wider domains make most dots cluster center.
- **D-16:** Score-axis domain and neutral band for Tile 2: **reuse the existing Openings score-bullet constants** (`SCORE_BULLET_CENTER`, `SCORE_BULLET_NEUTRAL_MIN`, `SCORE_BULLET_NEUTRAL_MAX`) so the visual reads identically across the Openings and Endgames pages. If those constants don't exist as exports, extract them.
- **D-17:** Mobile ordering when stacked: **entry-eval first, score second** — chronological (setup → execution).

### Out of Scope (LOCKED — from ROADMAP.md "Concept" + design notes)

- **D-18:** No clock-diff pairing in this section. Cross-user analysis (`.planning/notes/endgame-entry-eval-tile-design.md` §"Why we did NOT pair with clock-diff") shows the trade-off only holds in bullet/blitz (r ≈ −0.4) and vanishes in rapid/classical (r ≈ 0). Clock-diff stays in the existing Time Pressure section.
- **D-19:** No per-TC stratification of entry eval — population baseline is TC-invariant under equal-footing.
- **D-20:** No distribution-histogram view of per-game evals — heavier on the page; future "click to expand" detail at most.
- **D-21:** WDL table stays exactly as-is. Score Gap column is **not** removed and not given a sig test in this phase. The obsolete design note's "drop Score Gap column / restructure WDL table" plan is rescinded.

### Claude's Discretion

- Final wording of the accordion paragraphs.
- Final visual polish (spacing, alignment of the inline value row, info-icon placement) — iterate during UI review.
- Whether to colorize the punchy title text or only the value text. Default: only the value text is colored, matching the Openings ExplorerTab pattern.

### UAT Amendment — Entry-Eval Aggregation Source (added 2026-05-09)

- **D-22 (LOCKED, post-UAT):** Entry-eval aggregation consumes **bucket_rows** (one row per endgame game, eval at the **chronologically first** endgame position) instead of per-class **entry_rows**. Surfaced during UAT against user 28: the original per-class pipeline (group by `(game_id, endgame_class)`, dedupe by lowest endgame_class) excluded ~5 games per typical user where total endgame plies met the 6-ply threshold but no single class span did (e.g. 1 ply rook + 5 plies mixed). The bucket query groups by `game_id` only and applies the same threshold game-globally, so `entry_eval_n + mate_excluded == endgame_wdl.total` holds by construction. Chronologically-first eval is also a more intuitive match for the tile label "Where you start". Implementation lives in `_get_endgame_performance_from_rows` (calls `query_endgame_bucket_rows`); per-game dedupe loop removed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and design history
- `.planning/ROADMAP.md` lines 80-86 — Phase 81 entry (the canonical scope statement, including the locked "second tile = absolute score vs 50%" decision and the explicit obsoletion of the older Score-Gap-restructure plan).
- `.planning/notes/endgame-entry-eval-tile-design.md` — original twin-tile design exploration (2026-05-03). **Partly obsolete:** the second-tile framing (Score-Gap-as-second-tile, WDL-table restructure) is rescinded by ROADMAP. The benchmark / null-framing content (§"Population baseline", §"Why we did NOT pair with clock-diff") and the per-tile anatomy guidance still apply.

### Population reference data
- `.claude/skills/benchmarks/SKILL.md` §2 — population baseline for entry eval (~0 cp under equal-footing, per-game SD ≈ 418 cp), Cohen's-d collapse verdicts.
- `reports/benchmarks-2026-05-03.md` — concrete benchmark snapshot (mean, percentiles, distribution shape) used to size the pawn axis and the n threshold.

### Backend integration points
- `app/repositories/endgame_repository.py` — existing `first_endgame` ply walk; the new `entry_eval_mean_pawns` / `entry_eval_n` aggregation hooks into this same SQL path.
- `app/schemas/` — location of `EndgamePerformanceResponse` (planner: locate exact module and add the four new fields per D-11).
- `app/services/endgame_zones.py` + `frontend/src/generated/endgameZones.ts` — zone registry. CI fails on drift; re-run `scripts/gen_endgame_zones_ts.py` if zone constants change.

### Frontend integration points (reuse, do NOT reinvent)
- `frontend/src/components/charts/MiniBulletChart.tsx` — the chart component used by both tiles. Already supports `value`, `center`, `neutralMin`, `neutralMax`, `domain`, `ciLow`, `ciHigh`, `barColor`.
- `frontend/src/components/insights/BulletConfidencePopover.tsx` — eval-bullet popover. Use for Tile 1.
- `frontend/src/components/insights/ScoreConfidencePopover.tsx` — score-bullet popover. Use for Tile 2.
- `frontend/src/pages/openings/ExplorerTab.tsx` lines 100-200 — canonical reference for the inline value-row + popover + bullet-chart layout pattern. Mirror this structure inside each tile.
- `frontend/src/pages/Endgames.tsx` — section sits inside the `showPerfSection` block, above the `<EndgamePerformanceSection ... />` div (line 392-394). Concept paragraphs go inside the existing `<AccordionContent>` block.
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — the existing WDL table component. Read to understand the surrounding visual style and ensure the new section visually integrates above it.
- `frontend/src/lib/theme.ts` — `ZONE_SUCCESS`, `ZONE_DANGER`, `ZONE_NEUTRAL` for the three-state color logic.

### Statistical method
- Project's existing chess-score Wilson sig-test util (planner: locate the helper used by the Openings score bullet — `wilson_score_confidence` or similar — and use it for Tile 2; do not reinvent). Tile 1 uses a one-sample Wald z test of mean against 0; if no helper exists, add one alongside the score helper rather than duplicating logic.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`MiniBulletChart`** (`frontend/src/components/charts/MiniBulletChart.tsx`): drop-in for both tiles. Already used by the Openings ExplorerTab for both eval and score bullets, so behavior is well-understood.
- **`BulletConfidencePopover`** + **`ScoreConfidencePopover`** (`frontend/src/components/insights/`): drop-in popovers — already render n, p-value, confidence level, and supporting context. No new popover needed.
- **`first_endgame` ply walk** (`app/repositories/endgame_repository.py`): the SQL path conv/parity/recov already uses. New fields are one additional column off this path.
- **Existing Openings score-bullet constants** (`SCORE_BULLET_CENTER`, `SCORE_BULLET_NEUTRAL_MIN`, `SCORE_BULLET_NEUTRAL_MAX`): reuse for Tile 2 so the visual matches across pages.
- **Wilson score confidence helper** (project's existing chess-score util): the canonical method for Tile 2's significance test — do not editorialize methodology in design.

### Established Patterns
- **Inline value row + popover + bullet chart** (per Openings ExplorerTab rows 2 & 3): the locked layout pattern for both tiles in this phase.
- **n ≥ 10 threshold** for "render value vs render placeholder" — the project-wide convention. Apply here for consistency.
- **Three-state color via theme constants** (`ZONE_SUCCESS` / `ZONE_DANGER` / `ZONE_NEUTRAL`): the locked color scheme; never hard-code colors.
- **Concepts accordion in the Endgames page**: existing `endgame-concepts-trigger` accordion is the home for the two new explainer paragraphs. Don't add a parallel info structure.
- **Backend response shape extension**: extend `EndgamePerformanceResponse` rather than introducing a new endpoint or response type.

### Integration Points
- **`frontend/src/pages/Endgames.tsx`** at the `showPerfSection` block (around line 339-403): new section is rendered above the `<EndgamePerformanceSection data={perfData} scoreGap={scoreGapData} />` `charcoal-texture` card.
- **`EndgamePerformanceResponse` schema**: four new fields (D-11). Frontend type generation / hand-written types must be updated.
- **`app/repositories/endgame_repository.py`**: the new aggregation lives in the same query path as conv/parity/recov.
- **Concepts accordion**: two new `<p>` blocks added to the existing `<AccordionContent>` in `Endgames.tsx`.

</code_context>

<specifics>
## Specific Ideas

- **Match the Openings page visual language exactly.** The score bullet on the Openings ExplorerTab and the score tile on this new section should be visually indistinguishable (same domain, same neutral band, same colors). This is intentional — it teaches users that "endgame score vs 50%" is the same kind of metric they already understand from openings.
- **Don't show p-values as a stats line.** They live inside the popover only. The user explicitly called this out — the Openings pattern doesn't surface p-values inline either.
- **Phrase the null as "we can't tell," not "no advantage."** A non-significant result on a few-hundred-game corpus often means the test couldn't detect the effect, not that the effect is zero. Carry this framing into the popover copy and the concepts paragraphs.
- **Tile 2's value-line wording should mirror Tile 1's signed-magnitude pattern** (e.g., "+0.4 pawns ahead" / "56% — above break-even"), so both tiles read as parallel observations rather than mismatched UIs.

</specifics>

<deferred>
## Deferred Ideas

- **Distribution / histogram view of per-game entry evals.** More informative than a single mean, but heavier on the page. Future "click to expand" detail at most — its own phase.
- **Per-TC stratification of entry eval.** Population baseline is TC-invariant under equal-footing, so this only matters if a future analysis surfaces a TC-specific signal worth a dedicated tile.
- **Sig-test on Score Gap (in the WDL table).** The original design note proposed adding this for symmetry. Out of scope for this phase — Score Gap stays descriptive in the WDL table. If we ever revisit, the work would be small (Wilson on the gap itself or a paired comparison).
- **Cross-user across-game eval × clock-diff correlation as a displayed metric.** Interesting cross-section, but doesn't belong in Overall Performance. Would warrant its own exploration if at all.
- **Pre-endgame eval over time chart** (analog of `EndgameScoreOverTimeChart` for entry eval). Could pair nicely with the new tile, but adds a second chart this phase doesn't promise. Future phase if user asks.

</deferred>

---

*Phase: 81-Endgame Start vs End*
*Context gathered: 2026-05-09*
