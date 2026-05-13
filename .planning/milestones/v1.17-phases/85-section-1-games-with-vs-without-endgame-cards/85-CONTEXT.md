# Phase 85: Section 1 — Games with vs without Endgame cards - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the legacy table at the top of `EndgamePerformanceSection.tsx` ("Games with vs without Endgame") with two side-by-side cards on lg+ (stacked on mobile), plus a full-width Score Gap footer bullet spanning both cards. Reuses the established `EndgameStartVsEndSection.tsx` tile shell + `MiniBulletChart` + sig-gating pattern. Section 1 has **no peer bullet** (cohort-only): the per-card score bullet is anchored at the natural balanced-WDL anchor (0.50), not at a population p50.

Scope:
1. New section component (`EndgameGamesWithWithoutSection.tsx` or similar) — two cards (No / Yes) + footer Score Gap bullet.
2. Per-card Score row: chess-score `(W + 0.5·D)/n` + Wilson 95% CI whiskers + score bullet vs 0.50 with neutral band `[SCORE_BULLET_NEUTRAL_MIN, SCORE_BULLET_NEUTRAL_MAX]`; font color gated on `n ≥ MIN_GAMES_FOR_RELIABLE_STATS ∧ p < 0.05 ∧ outside neutral band` (SEC1-06).
3. Per-card WDL bar (`MiniWDLBar`).
4. Footer Score Gap bullet (`Yes − No`, center 0, neutral band `[SCORE_GAP_NEUTRAL_MIN, SCORE_GAP_NEUTRAL_MAX]` from `generated/endgameZones.ts`) — zone-color font only, no sig test.
5. Per-card score-row `InfoPopover` (SEC1-05) explaining that 0.50 is the balanced-WDL natural anchor (no rating-tier confound applies).
6. Mount swap in `Endgames.tsx` and removal of the legacy `EndgamePerformanceSection` function (knip clean per SEC1-07).
7. **Backend addition:** `non_endgame_score_p_value: float | None` on `EndgamePerformanceResponse`, computed in the same place `endgame_score_p_value` is computed (mirror identity).

**Out of scope:** Mirror-bucket peer bullets (no peer baseline in Section 1), per-class breakdown, the `EndgameScoreOverTimeChart` (preserved as-is — only relocated as a file move per D-04), Section 2/3 cards (Phases 86/87), polish decisions deferred to Phase 88.

</domain>

<decisions>
## Implementation Decisions

### Score row p-value derivation (LOCKED)

- **D-01:** **Add `non_endgame_score_p_value: float | None` to the backend `EndgamePerformanceResponse`**, computed in the same code path as the existing `endgame_score_p_value` (apply the Wilson score-test vs `H0: score == 0.5` to `non_endgame_wdl.{wins,draws,total}`). The new card uses the backend p-value, mirroring how the Yes card already consumes `endgame_score_p_value`. Rationale: single derivation site, identical formula for both cards, matches the existing pattern; the local `computeScoreConfidence` is then used only for the CI (`wilsonBounds`), keeping p-value semantics consistent with `EndgameStartVsEndSection` Tile 2.
- **D-02:** **Wilson CI** comes from `wilsonBounds(score, total)` in `frontend/src/lib/scoreConfidence.ts` — computed frontend-side for both cards (matches the Tile 2 pattern at `EndgameStartVsEndSection.tsx:124`). No backend CI field needed.
- **D-03:** Sig-bucket bucketing reuses the existing `deriveLevel(p, n)` pattern from `EndgameStartVsEndSection.tsx:73-78` (`n < 10 → low`, `p < 0.01 → high`, `p < 0.05 → medium`, else low). `isConfident(level)` from `@/lib/significance` drives the font-color gate. Do not invent a parallel sig-bucket helper.

> **Milestone-boundary note (flag to planner):** The v1.17 ROADMAP description says "Frontend-only refactor". D-01 adds one float field on the backend `EndgamePerformanceResponse` and a 2-3 line Wilson p-value call in the service. The user authorized it explicitly. Plan-phase should note this in the plan summary and the phase-close milestone description should be amended from "Frontend-only" to "Frontend-only with one backend additive field" or similar.

### Footer Score Gap bullet (LOCKED)

- **D-04:** **Zone-color only — no sig gating.** Footer Score Gap bullet keeps the legacy color rule: font color from `score_difference` vs `[SCORE_GAP_NEUTRAL_MIN, SCORE_GAP_NEUTRAL_MAX]` zones (green above, neutral within, red below). SEC1-04 does not require sig gating, and a true paired test on the gap would need new statistical plumbing (two-proportion z-test on chess-score, or paired-sample variant) that's out of v1.17 scope. Keep the legacy zone-only semantics to preserve user-facing behavior; the per-card sig gating in D-01 / D-03 already conveys reliability.
- **D-05:** Footer bullet uses `MiniBulletChart` with `center=0`, `neutralMin=SCORE_GAP_NEUTRAL_MIN`, `neutralMax=SCORE_GAP_NEUTRAL_MAX`, `domain=0.20` (same `SCORE_GAP_DOMAIN` the legacy uses at `EndgamePerformanceSection.tsx:44`).
- **D-06:** Footer Score Gap value is `scoreGap.score_difference` (already on `ScoreGapMaterialResponse.score_difference`, scale 0-1, signed: `endgame_score - non_endgame_score`). No new backend field needed for the gap.

### Section header and per-card info popovers (Claude's Discretion → LOCKED)

- **D-07:** **Keep the section-level h3 header + InfoPopover above the cards** (preserves explanation continuity for users already familiar with the legacy section). Header text reuses the legacy copy: `Games with vs without Endgame` h3 + the existing 1-line sub-tagline + section-level `InfoPopover` content unchanged. The per-card score-row popover (SEC1-05) is additive, not a replacement.
- **D-08:** Per-card score-row `InfoPopover` copy (SEC1-05): explain that 0.50 is the balanced-WDL natural anchor (one win + one loss = 0.50 score, all draws = 0.50 score) and is conceptually different from a population p50 cohort baseline (so no rating-tier confound applies here, unlike the dropped per-type p50 in Sections 2/3 per the single-bullet doctrine). Re-uses the `InfoPopover` component already used in the legacy section.

### Legacy code removal mechanics (Claude's Discretion → LOCKED)

- **D-09:** **Extract `EndgameScoreOverTimeChart` to its own file** (`frontend/src/components/charts/EndgameScoreOverTimeChart.tsx`) before deleting the legacy `EndgamePerformanceSection.tsx`. Move the chart + its `SCORE_BAND_CLASS` export + the `useIsMobile` hook + the Phase-68 comment block intact. Update the import in `Endgames.tsx:21` to two lines (one per file) → after section removal, just one line for the chart. This satisfies SEC1-07 (knip-clean removal of `EndgamePerformanceSection`) without entangling the unrelated timeline chart. Rationale: the file is named after a section that no longer exists; renaming it to match the new chart-only contents is cleaner than leaving an orphan section import path.
- **D-10:** New Section 1 component file: `frontend/src/components/charts/EndgameGamesWithWithoutSection.tsx`. Component export: `EndgameGamesWithWithoutSection`. Mounts in `Endgames.tsx` at the same spot where the legacy `<EndgamePerformanceSection data={...} scoreGap={...} />` currently lives (line 422). Props: `{ data: EndgamePerformanceResponse; scoreGap: ScoreGapMaterialResponse }` — note `scoreGap` becomes required (was optional in the legacy section), since the footer Score Gap bullet always renders.

### Tile shell & layout (LOCKED — carried forward from Phase 81)

- **D-11:** Reuse the exact tile shell from `EndgameStartVsEndSection.tsx:140-148` (`<div className="charcoal-texture rounded-md p-4">` with `<h3 className="text-base font-semibold mb-2">` title and `<div className="flex flex-col gap-4">` body). Each card has its own tile.
- **D-12:** Reuse the grid pattern `grid-cols-1 lg:grid-cols-[14rem_minmax(0,1fr)] gap-x-3 gap-y-2 items-center` for the score row (left: label + value + popover trigger; right: `MiniBulletChart`). Stacked on mobile (single-column).
- **D-13:** Score bullet domain: `ENDGAME_TILE_SCORE_DOMAIN = 0.15` (matches `EndgameStartVsEndSection.tsx:54`; gives 35-65% axis with the ±0.05 neutral band filling ≈1/3 of the axis). Do **not** use the wider `SCORE_BULLET_DOMAIN = 0.25` from `scoreBulletConfig.ts`; the locked endgame-section convention is the tighter ±0.15 domain.
- **D-14:** Cards arranged in a 2-col grid on lg+ (`grid grid-cols-1 lg:grid-cols-2 gap-4`), stacked on mobile. Order: **No (without Endgame) left, Yes (with Endgame) right** per the v1.17-ROADMAP locked ordering ("(No / Yes)"). Footer Score Gap bullet sits below in a full-width row.
- **D-15:** Card titles: `Games without Endgame` (left) and `Games with Endgame` (right) — matches SEC1-01 verbatim.

### Claude's Discretion

- **Footer row layout granularity.** Planner picks whether the footer bullet sits inside a separate `<div>` row spanning both columns via `col-span-2` (preserves the tile-card visual containers cleanly) or as a third tile with its own header label (e.g., "Score Gap (Yes − No)"). D-07 keeps the section-level header above all three, so a sub-label on the gap row is optional. Recommendation: a full-width tile with a "Score Gap (Yes − No)" h3 to match the visual rhythm of the upper two cards.
- **Empty-state copy.** When `wdl.total == 0` on a card, planner picks the empty-state treatment. Recommend reusing `<p className="text-sm text-muted-foreground py-4">Not enough data yet</p>` per `EndgameStartVsEndSection.tsx:187`.
- **Test placement.** Add component tests under `frontend/src/components/charts/__tests__/` (or wherever the existing `EndgameStartVsEndSection` tests live). Planner picks the seam that matches existing structure.
- **Backend test placement.** D-01 adds a field to `EndgamePerformanceResponse`. Add the Wilson p-value test alongside the existing `endgame_score_p_value` test in whichever file currently covers it (`tests/services/test_endgame_service.py` or similar — planner locates).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.17 spec & roadmap
- `.planning/milestones/v1.17-ROADMAP.md` §Phase 85 — success criteria, card ordering (No / Yes), legacy removal mandate.
- `.planning/REQUIREMENTS.md` lines 16-22 — SEC1-01 through SEC1-07 (the seven Section 1 requirements).
- `.planning/notes/v1.17-single-bullet-doctrine.md` — pivot rationale; explains why Section 1 has no peer / cohort bullet (anchor is 0.50, a natural balanced-WDL anchor, not a population p50).

### Pattern template (LOCKED — replicate this)
- `frontend/src/components/charts/EndgameStartVsEndSection.tsx` — the canonical tile + bullet + sig-gating template. Reuse `deriveLevel(p, n)` (lines 73-78), the tile shell (140-148), the row grid (147), the sig-gating pattern (`isConfident(level) && isInColoredZone`), and `ENDGAME_TILE_SCORE_DOMAIN` (line 54).

### Legacy to be removed / extracted
- `frontend/src/components/charts/EndgamePerformanceSection.tsx:73-256` — the legacy `EndgamePerformanceSection` function (delete per SEC1-07).
- `frontend/src/components/charts/EndgamePerformanceSection.tsx:258-575` — `EndgameScoreOverTimeChart` (EXTRACT to its own file per D-09, do NOT delete).
- `frontend/src/components/charts/EndgamePerformanceSection.tsx:44` — `SCORE_GAP_DOMAIN = 0.20` constant (lift to the new section file).
- `frontend/src/components/charts/EndgamePerformanceSection.tsx:50-71` — `useIsMobile` hook (move with the chart in D-09; it's only used by the chart, not the legacy section).
- `frontend/src/pages/Endgames.tsx:21,422,426` — import + mount sites for the legacy section and the chart.

### Reusable components & utilities
- `frontend/src/components/charts/MiniBulletChart.tsx` — the bullet primitive used for the score row + footer gap.
- `frontend/src/components/stats/MiniWDLBar.tsx` — per-card WDL bar (already used by `EndgameStartVsEndSection`).
- `frontend/src/components/ui/info-popover.tsx` — section-level + per-card popover trigger.
- `frontend/src/lib/scoreConfidence.ts:51` — `wilsonBounds(score, total)` for CI whiskers.
- `frontend/src/lib/scoreBulletConfig.ts:11-26` — `SCORE_BULLET_CENTER`, `SCORE_BULLET_NEUTRAL_MIN/MAX`, `clampScoreCi`, `scoreZoneColor`.
- `frontend/src/lib/significance.ts` — `isConfident(level)` predicate (medium/high → true).
- `frontend/src/lib/theme.ts` — `MIN_GAMES_FOR_RELIABLE_STATS` (=10), `ZONE_NEUTRAL`, `ZONE_DANGER`, `ZONE_SUCCESS`.
- `frontend/src/generated/endgameZones.ts` — `SCORE_GAP_NEUTRAL_MIN/MAX` for the footer gap.

### Backend additive field (D-01)
- `app/schemas/endgames.py` — `EndgamePerformanceResponse` schema (already carries `endgame_score_p_value`; mirror with `non_endgame_score_p_value: float | None`).
- `app/services/endgame_service.py` — search for the `endgame_score_p_value` computation site; add the mirror call on `non_endgame_wdl`. Use the same Wilson score-test helper (likely `app/services/score_confidence.py`).
- `tests/services/test_endgame_service.py` — extend the existing p-value coverage with the non_endgame variant.
- `frontend/src/types/endgames.ts:58-76` — extend `EndgamePerformanceResponse` with `non_endgame_score_p_value: number | null` (mirror line 66).

### Wire shape (already populated, no backend change)
- `frontend/src/types/endgames.ts:58-76` — `EndgamePerformanceResponse` (with the D-01 extension).
- `frontend/src/types/endgames.ts:142-149` — `ScoreGapMaterialResponse.score_difference` (footer bullet value).
- `frontend/src/pages/Endgames.tsx` — `perfData` (= `EndgamePerformanceResponse`) and `scoreGapData` (= `ScoreGapMaterialResponse`) are both already loaded by the existing overview query.

### Prior phase context
- `.planning/milestones/v1.17-phases/84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit/84-CONTEXT.md` — Phase 84 mirror-rate audit; no Section 1 dependency but adjacent.
- `.planning/milestones/v1.16-phases/81-*` / `83-*` — Phase 81 / 83 `EndgameStartVsEndSection` build-out; the template Phase 85 replicates.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`EndgameStartVsEndSection.tsx` tile shell + `deriveLevel` + grid pattern** — direct template for the two cards. Copy the structure, swap inputs.
- **`MiniBulletChart`** — the bullet primitive. Already battle-tested for absolute score (Tile 2 of StartVsEnd) and signed gap (legacy footer).
- **`wilsonBounds` from `scoreConfidence.ts`** — frontend Wilson CI for the whisker plumbing.
- **`MiniWDLBar`** — drop-in per-card WDL bar (already wired in `EndgameStartVsEndSection.tsx:259-263`).
- **`InfoPopover`** — already used at the section-level header in the legacy component; reuse for per-card score-row popovers (SEC1-05).

### Established Patterns
- **Sig-gating triple** (`isConfident(level) ∧ isInColoredZone`): `EndgameStartVsEndSection.tsx:85-86, 100-103, 121-123`. Apply per-card to the score row, NOT to the footer gap (D-04).
- **`ENDGAME_TILE_SCORE_DOMAIN = 0.15`** local override (Tile 2 of StartVsEnd): the locked endgame-section axis half-width. Section 1 cards reuse this — DO NOT pull `SCORE_BULLET_DOMAIN = 0.25` from `scoreBulletConfig.ts`.
- **`charcoal-texture rounded-md p-4`** tile container (Phase 81 convention). Cards reuse this class set.
- **`grid-cols-1 lg:grid-cols-[14rem_minmax(0,1fr)]`** score-row grid (label | bullet). Stacked on mobile by default.
- **`flex flex-col gap-4`** vertical stack inside each tile (separates WDL bar row from Score bullet row).
- **`MiniBulletChart neutralMin/neutralMax` semantics**: the registry stores absolute bounds, but `MiniBulletChart` expects OFFSETS from center. For the per-card score bullet anchored at 0.50, use `SCORE_BULLET_NEUTRAL_MIN / SCORE_BULLET_NEUTRAL_MAX` directly (these are already ±0.05 offsets in `scoreBulletConfig.ts`). For the footer gap bullet anchored at 0, use `SCORE_GAP_NEUTRAL_MIN / SCORE_GAP_NEUTRAL_MAX` from `generated/endgameZones.ts` directly (also offsets). The CR-01 fix in `EndgameStartVsEndSection.tsx:217-218` (subtract center) does NOT apply to either Section 1 bullet because Section 1 uses the *offset*-form constants natively.

### Integration Points
- **`Endgames.tsx:422`** — mount swap site (legacy `<EndgamePerformanceSection>` → new `<EndgameGamesWithWithoutSection>`).
- **`Endgames.tsx:21,426`** — import path update for both the deleted section and the extracted `EndgameScoreOverTimeChart`.
- **`app/services/endgame_service.py`** — Wilson p-value site for `non_endgame_score_p_value` (mirror of `endgame_score_p_value`).
- **knip CI** — must pass after legacy removal (SEC1-07). Verify with `npm run knip` after the deletion.

### Sentry
- No new exceptional paths. Score / p-value / CI computations are pure arithmetic guarded by `total > 0` (handled by `wilsonBounds` and the existing patterns).

</code_context>

<specifics>
## Specific Ideas

- **Naming:** `EndgameGamesWithWithoutSection.tsx` for the new component file; matches the `EndgameStartVsEndSection.tsx` / `EndgameScoreGapSection.tsx` neighbor style.
- **Card titles:** verbatim from SEC1-01 — `Games without Endgame` (left) / `Games with Endgame` (right).
- **Sub-tagline:** keep the legacy "Do you perform better or worse when games reach an endgame?" line above the cards (under the section h3).
- **Section header InfoPopover:** keep the legacy copy unchanged (explains "endgame phase" definition + 6-half-move threshold + what the Score Gap means).
- **Per-card score-row InfoPopover:** new copy (SEC1-05) explaining the 0.50 natural anchor. Suggested copy: *"This score's neutral anchor sits at 50% by construction — at 50% your wins balance your losses (after accounting for draws as half-points). Unlike the rating-tier-conditioned p50 used in other sections, this anchor isn't a population statistic and doesn't shift with your rating or time control."*
- **Comment** in the new component referencing Phase 85 + the v1.17 single-bullet doctrine, like the existing Phase 81 / 83 header block in `EndgameStartVsEndSection.tsx:1-19`.

</specifics>

<deferred>
## Deferred Ideas

- **Paired-test sig gating on the footer Score Gap bullet** — D-04 keeps zone-color-only. A future phase could add a paired two-proportion z-test (or score-difference z) and gate font color on it. Out of scope for v1.17.
- **Per-card peer baseline** — Section 1 is deliberately cohort-only (no mirror-bucket peer bullet). Adding one would require a backend peer-rate field for "without Endgame" / "with Endgame", which is conceptually fuzzy (peers don't have a clean "with vs without endgame" mirror like material buckets do). Out of v1.17 scope.
- **Section-level merging with `EndgameStartVsEndSection`** — both sections live above the WDL table on the Endgames page and share visual language. A future polish phase could consider merging them into one composite section, but they answer different questions ("where you start vs end" vs "with vs without endgame") and should stay separate per current IA.

</deferred>

---

*Phase: 85-section-1-games-with-vs-without-endgame-cards*
*Context gathered: 2026-05-13*
