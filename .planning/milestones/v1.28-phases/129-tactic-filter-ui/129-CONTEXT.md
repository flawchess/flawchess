# Phase 129: Tactic Filter UI - Context

**Gathered:** 2026-06-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 129 is the **frontend** that surfaces the tactic data already stored and
contract-exposed by Phases 124–128. It lets a (beta) player filter and read tactics along
three axes — **motif family**, **missed vs allowed**, and **difficulty (depth)** — across
the Library, desktop + mobile.

Two distinct surfaces:

1. **Library Flaws tab** (the user's own flaws, `player_only_gate`):
   - A **depth (difficulty) filter** — new control + new backend filter param.
   - A tri-state **orientation toggle** (Either / Missed / Allowed) governing the flaw list
     and its chips.
   - Motif **chips** carrying a `missed:`/`allowed:` prefix.
2. **Library stats / comparison surface** (`TacticComparisonGrid`, you-vs-opponent aggregate):
   - Each family card shows **two bullet charts** ("Missed X" + "Allowed X").
   - **No** orientation toggle here; it always shows both orientations.
   - Top-6 ranked by **Missed**; the rest behind a **"More Tactics"** accordion.

**Builds on the locked 128 contract** (`orientation ∈ {missed, allowed}`, both column sets
in schemas) and the 126 chip/grid/filter UI. **Two pieces of NEW backend work** fall out of
the decisions below and are in 129 scope:
- a **depth filter** param (none exists today), and
- an **"either"** orientation state (the 128 param is binary; "either" = OR across both
  `missed_*` and `allowed_*` column sets).

**Out of scope:** new motifs/detector work (frozen at 127); any new Stockfish/eval; tactic
**benchmark zones** (the grid degrades gracefully where no zone exists — 126); a standalone
scouting/opponent-flaw view (TACMISS-01, deferred); prod re-backfill (127/128 runbook).
</domain>

<decisions>
## Implementation Decisions

### Depth (difficulty) control — Flaws tab
- **D-01:** **Single max-depth slider**, cloning the visual + interaction pattern of
  `OpponentStrengthFilter.tsx` (`lib/opponentStrength.ts`), but **single-handle** instead of
  a range. Semantics: "show tactics up to N deep." Beginner / Intermediate / Advanced
  **preset chips snap the slider**; the slider can also set a custom depth. Reuse the
  preset-chip + `derivePreset`/`presetToRange`/`sliderToValue` + `InfoPopover` + summary +
  mobile (`h-11 sm:h-7`) idiom.
- **D-02:** **Always-on**, default preset = **Intermediate** (the filter genuinely narrows on
  load, deeper tactics one drag away). NOTE this differs from the existing tag/family
  "off-by-default (empty=no filter)" semantics — the depth filter is intentionally always
  active, so its filter-dot/active state reads as on by default.
- **D-03:** Player-facing unit = **"moves deep"** (full moves, ⌈ply/2⌉) — chess players reason
  in moves, not half-moves. Storage stays raw half-move ply (127 D-04); the UI converts. The
  one-ply baseline offset between `missed_tactic_depth` and `allowed_tactic_depth` (128 D-05)
  is NOT exposed as a raw number — the "moves deep" label smooths it.
- **D-04:** **Mates always render regardless of the depth filter** (127 D-03). Add one line to
  the depth-filter `InfoPopover` (e.g. "Forced mates always show, regardless of difficulty"),
  matching the OpponentStrengthFilter info-popover convention. No special chip.
- **D-05 (NEW backend work):** A **depth filter param** must be added to the flaw filter query
  layer (`build_flaw_filter_clauses` / `apply_game_filters`, `library_repository`) — it does
  **not** exist in the 128 contract. It filters on the **active orientation's** depth column
  (`missed_tactic_depth` / `allowed_tactic_depth`; in "either" mode, the matching column of
  whichever orientation qualifies). Mates exempt per D-04.

### Orientation toggle — Flaws tab
- **D-06:** Tri-state **`ToggleGroup type="single"`** with options **Either / Missed / Allowed**,
  styled exactly like the **"Played as"** control (`FilterPanel.tsx:265-286`). Placed inside
  **`FlawFilterControl`** (the flaw "Tags" panel/drawer), **above** the Tactic Motif family
  filter. Default = **Either**.
- **D-07 (reverses SC#2 / 128 D-08 / 126 — user directive 2026-06-20):** The default is
  **Either**, NOT "missed." The planner must amend ROADMAP **SC#2** ("defaulting to missed")
  to reflect Either-default. The locked-but-overridden decision is conscious; record it.
- **D-08 (NEW backend work):** "Either" is a **third orientation state** the 128 param
  (`Literal["missed","allowed"]`, default `allowed`) does not cover. Implement "either" as an
  **OR across both column sets** — a flaw qualifies if its `missed_*` OR `allowed_*` motif is
  in the selected families (and within the depth bound). Extend the param to a 3-value
  `Literal["either","missed","allowed"]` (or equivalent) in both filter sites (`query_utils`,
  `library_repository`). Reuse `FAMILY_TO_MOTIF_INTS` + `_TACTIC_CHIP_CONFIDENCE_MIN` (70)
  unchanged for both orientations.
- **D-09:** The toggle governs the **Flaws-tab list + its chips only**. It does **not** appear
  on, or drive, the stats-page comparison grid (see D-13/D-14).

### Chips — Flaws list rows + single-game card
- **D-10:** Chips carry a **`missed:`/`allowed:` text prefix** in the label (e.g. "missed: fork",
  "allowed: discovered-attack"). **Family color = the family**; the **prefix word = orientation**
  (no new color/style/icon code for orientation). Keep the shipped `TagChip` / `TacticMotifChip`
  family-color + definition-popover pattern.
- **D-11:** Show **both** chips when a flaw has both a missed and an allowed motif; show one
  chip when only one orientation is populated. Under **Missed**/**Allowed** the card shows only
  that orientation's chip; under **Either** it shows both (when both exist).
- **D-12:** **Chip + definition popover IS the whole narration** — no extra inline sentence
  (popover-copy minimalism). Applies to Library list rows AND the single-game flaw card
  (126 D-10), with mobile parity. Since the Flaws list is player-only, the flaw-maker is always
  the user, so the matrix collapses to the two player rows ("you missed" / "you allowed") — no
  opponent/scouting narration on cards.

### Stats comparison grid (`TacticComparisonGrid`)
- **D-13:** **Two bullet charts per family card** — "Missed X" and "Allowed X" (e.g. the Fork
  card shows a Missed-Fork bullet and an Allowed-Fork bullet). The grid has **no** orientation
  toggle and is **independent** of the Flaws-tab depth/orientation filters (it shows both
  orientations; existing game filters still apply per the comparison endpoint). This requires
  the **tactic-comparison endpoint to return both orientation rates per family** (today it
  returns the single `allowed` rate) — backend change in scope.
- **D-14:** **Top-6 family selection ranked by the Missed orientation** (was: largest
  significant gap, 126 D-07). Families that don't make the top 6 go into a **collapsible
  "More Tactics"** section using the shared **`Accordion`** component (`AccordionTrigger band`),
  the same pattern as **"Endgame Statistics Concepts"** (`Endgames.tsx:390-397`).

### Claude's Discretion
- Exact depth band thresholds for Beginner/Intermediate/Advanced (named constants), calibrated
  against Phase 127's depth-vs-puzzle-Rating correlation output. No magic numbers.
- Exact param name/shape for the depth filter (e.g. `max_tactic_depth: int | None`) and the
  3-value orientation enum (D-08).
- Ranking detail for D-14 top-6-by-Missed (tie-break/volume fallback; align with the existing
  126 server-side ranking helper).
- Whether "More Tactics" reuses the same family-card renderer (preferred) or a compact variant.
- All `theme.ts` token reuse (family colors already added in 126; no new orientation tokens
  per D-10).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & prior phase decisions
- `.planning/REQUIREMENTS.md` — TACUI-01/02/03 (Phase 126, Complete); TACMISS-01 (deferred
  standalone-missed, NOT this phase). 129's own REQ IDs are TBD (roadmap says "to be
  assigned during discuss-phase" — planner assigns/maps).
- `.planning/ROADMAP.md` §"Phase 129: Tactic Filter UI" — goal + SC#1–4. **SC#2 needs amending**
  (D-07: default is Either, not missed).
- `.planning/phases/126-comparison-stats-frontend/126-CONTEXT.md` — beta gate (D-01), family
  taxonomy + colors (D-08), the chip + comparison-grid + motif-filter UI this phase extends,
  server-side top-N ranking (D-07, now reframed by 129 D-14).
- `.planning/phases/127-detector-hardening-validation/127-CONTEXT.md` — depth = raw detector-loop
  ply (D-04); always-on depth filter framing (D-06); **mates filter-exempt** (D-03);
  depth-vs-Rating correlation is the calibration basis for D-01 band thresholds.
- `.planning/phases/128-missed-opportunity-tagging/128-CONTEXT.md` — the locked `orientation`
  filter contract (D-07/D-08/D-09), both column sets in schemas, depth baseline differs by one
  ply between sets (D-05), narration = column-set × `is_opponent_expr` (D-10).

### Design notes (read first)
- `.planning/notes/missed-vs-allowed-tactic-design.md` — the two orthogonal axes, mover-relative
  columns (no `tactic_pov`), the narration matrix, depth-as-difficulty/slider.
- `.planning/notes/tactic-tagging-architecture.md` — single-tag-per-orientation, `tactic_confidence`
  query-suppression knob, motif set + tiers, D-07 priority/mate dominance.

### Frontend assets to clone / extend
- `frontend/src/components/filters/OpponentStrengthFilter.tsx` + `frontend/src/lib/opponentStrength.ts`
  — **the** pattern to clone for the single-handle depth slider + preset chips (D-01).
- `frontend/src/components/filters/FilterPanel.tsx:265-286` — the "Played as" `ToggleGroup` to
  mirror for the Either/Missed/Allowed orientation control (D-06).
- `frontend/src/components/filters/FlawFilterControl.tsx` — host for the orientation toggle +
  depth filter (above Tactic Motif families); already renders severity/tags/tacticFamilies.
- `frontend/src/hooks/useFlawFilterStore.ts` — module-level flaw-filter store; add `orientation`
  + depth fields; update `isFlawFilterNonDefault` (note D-02 always-on default).
- `frontend/src/components/library/TacticComparisonGrid.tsx` (393 LOC) — current one-bullet-per-
  family grid to extend to two bullets/card + Missed-ranked top-6 + "More Tactics" (D-13/D-14).
- `frontend/src/components/library/TacticMotifChip.tsx`, `frontend/src/lib/tacticMotifDefinitions.ts`,
  `frontend/src/lib/tacticComparisonMeta.ts` (`TacticFamily`) — chip + family meta to extend with
  the `missed:`/`allowed:` prefix (D-10).
- `frontend/src/components/library/FlawCard.tsx`, `frontend/src/pages/library/FlawsTab.tsx` — flaw
  card + Flaws tab render sites for chips + the filter controls.
- `frontend/src/components/charts/MiniBulletChart.tsx` — bullet chart reused for the two-per-card
  grid (D-13).
- `frontend/src/pages/Endgames.tsx:390-397` — the `Accordion`/`AccordionTrigger band` collapsible
  ("Endgame Statistics Concepts") to reuse for "More Tactics" (D-14).
- `frontend/src/components/ui/slider.tsx`, `frontend/src/components/ui/info-popover.tsx`,
  `frontend/src/components/ui/accordion.tsx` — shared primitives.
- `frontend/src/types/library.ts:101-117` — flaw schema already exposes both orientation chip
  fields (128); extend types for the new depth/orientation filter + two-orientation grid rates.

### Backend (NEW work in scope)
- `app/repositories/query_utils.py:90` — `build_flaw_filter_clauses(..., orientation=...)`; add the
  **depth filter** (D-05) and the **"either"** state (D-08). `:23` `is_opponent_expr`, `FAMILY_TO_MOTIF_INTS`.
- `app/repositories/library_repository.py` (`:196-201` filter clause, `:51` `_TACTIC_CHIP_CONFIDENCE_MIN`,
  `:470-476` chip read) — second filter/read site; mirror depth + either.
- `app/schemas/library.py:53-70,179-188` — flaw/chip + comparison schemas; comparison response must
  return BOTH orientation rates per family (D-13).
- `app/routers/library.py` (`/library/tactic-comparison`), `app/services/library_service.py` — endpoint
  + service to compute/return two-orientation rates and the Missed-based ranking (D-13/D-14).

### Rules
- CLAUDE.md "Frontend > Browser Automation Rules" — `data-testid` + ARIA + semantic HTML + 375px
  mobile parity (SC#4); theme constants in `theme.ts`; min `text-sm`; `tsc -b` before integrating
  (shared-type changes). Beta-gate all new tactic UI behind `beta_enabled` from
  `useUserProfile().data` (NOT `useAuth().user` — see project memory `frontend_beta_gating_source`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OpponentStrengthFilter` + `lib/opponentStrength.ts`: preset-chips-snap-slider pattern — clone
  single-handle for depth (D-01).
- "Played as" `ToggleGroup` (`FilterPanel.tsx`): tri-state single-select control — clone for
  Either/Missed/Allowed (D-06).
- `TacticComparisonGrid` + `MiniBulletChart`: existing one-bullet grid to extend to two bullets +
  Missed-ranked top-6 + accordion (D-13/D-14).
- `TacticMotifChip` + family color/definition meta: extend label with orientation prefix (D-10).
- `Accordion` (`AccordionTrigger band`): "Endgame Statistics Concepts" collapsible to reuse for
  "More Tactics" (D-14).
- Backend `orientation` param + `FAMILY_TO_MOTIF_INTS` + `_TACTIC_CHIP_CONFIDENCE_MIN`: reuse for
  both orientations; extend with depth + "either" (D-05/D-08).

### Established Patterns
- Flaws list is **player-only** (`player_only_gate`, D-04 in library_repository) — flaw-maker is
  always the user; card narration collapses to "you missed"/"you allowed".
- Module-level `useSyncExternalStore` filter store (no Zustand) — add orientation/depth fields.
- Beta gate = render-time conditional from `useUserProfile().data.beta_enabled`.
- Theme color constants only in `theme.ts` (families already there from 126; no new tokens, D-10).
- Apply every control + chip change to BOTH desktop and mobile drawer (CLAUDE.md).

### Integration Points
- `FlawFilterControl` gains the orientation toggle + depth slider (above Tactic Motif); store +
  query-params thread through to the flaw list query.
- Query layer (`query_utils` + `library_repository`) gains a depth filter and an "either" branch.
- `tactic-comparison` endpoint/service returns two-orientation rates + Missed ranking; the grid
  renders two bullets/card + a "More Tactics" accordion.
- Shared types (`types/library.ts`) change → run `tsc -b` before integrating (project memory).

</code_context>

<specifics>
## Specific Ideas

- Depth control: "Reuse the pattern and visual style from the opponent strength filter, but with
  a single slider instead of range. Beginner/Intermediate/Advanced presets set the tactic max
  depth slider; the slider can set a specific depth."
- Orientation: "Inside the Tags FilterPanel/drawer, above the Tactic Motif. Three options: Either
  (default), Missed, Allowed. Use the same control as the 'Played as' filter."
- Chips: "Tactic tags now include the missed/allowed prefix in the chip label (e.g. 'missed fork',
  'allowed discovered-attack'). Show a missed chip AND an allowed chip when both exist."
- Stats grid: "The Library stats page has no tags filter and therefore no Either/Missed/Allowed
  filter. Each tactic card should show a missed and an allowed bullet chart. Order cards by Missed
  for the top-6 selection. Add a collapsible 'More Tactics' section for the rest, using the shared
  collapsible (same as 'Endgame Statistics Concepts')."

</specifics>

<deferred>
## Deferred Ideas

- **Standalone `missed-X` detection / scouting opponent-flaw view** — TACMISS-01, explicitly
  deferred; the v1.28 missed view is reconstructed from adjacent-row data, not a new axis.
- **Tactic benchmark zones** for the bullet grid — no benchmark pipeline this phase; grid degrades
  gracefully where no zone exists (126 deferred).
- **Per-card narration sentences / opponent-scouting narration** — rejected for cards this phase
  (D-12); chip + popover only, list is player-only.
- **Backend hard-gating of tactic data behind `beta_enabled`** — frontend-only gate stands (126 D-01).
- **Prod re-backfill** (SEED-054 pv + folded 127/128 `classify` re-sweep) — runbook step outside
  the phase gate.

### Reviewed Todos (not folded)
Keyword-overlap matches only ("opponent"/"frontend"/"bullet"/"phase"/"backfill"); none relate to
tactic filter UI (same false positives Phase 126 reviewed):
- "Reframe Recovery Score Gap popover copy" — endgame recovery surface, unrelated.
- "WR-01 pt-33 invalid Tailwind class on Score Y-axis label" — old score-chart bug.
- "Phase 94.4 prod backfill + D-12 reversal UAT" / "Phase 70 REQUIREMENTS amendments" — unrelated
  deploy/planning items.

</deferred>

---

*Phase: 129-tactic-filter-ui*
*Context gathered: 2026-06-20*
</content>
</invoke>
