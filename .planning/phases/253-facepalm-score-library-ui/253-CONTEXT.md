# Phase 253: Facepalm Score in the Library UI (SEED-261114-0ke) - Context

**Gathered:** 2026-11-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Show the Phase 250 `facepalm_score` to users in the library:

1. A **Facepalm range filter** in the Tags side panel, on the Games and Flaws tabs.
2. A **`Facepalm N%` chip** with a popover on Flaws-tab cards, when the flaw has a score.

Backend: min/max score query params on the library endpoints, one clause in the shared flaw filter, the score on
the flaw card schema. No migration, no backfill, no opponent scoring.

Out of scope: the score in the blunder-check solution screen; facepalm rate stats and opponent scoring
(SEED-261114-iuv); any change to the score itself or to `FACEPALM_SCORE_MIN`.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (seed and roadmap, owner 2026-11-14; not re-discussed)
- **D-01: Name and casing.** "Facepalm", capitalized: `Facepalm 94%` on the chip, "Facepalm" as the filter label.
  UI, code and docs all say facepalm.
- **D-02: Icon.** lucide `TreePalm`, always followed by the word. The icon never appears alone.
- **D-03: Not a probability** (250 D-01). The score is a ranking; no copy presents it as a share of peers or a
  chance. Banned wording: "avoidable", "chance you'd see it".
- **D-04: Filter semantics.** Full range 0-100% = no filter (no clause added). A narrowed range keeps only flaws
  with a non-NULL `facepalm_score` in range, so mistakes, inaccuracies and blunders without a score drop out.
- **D-05: User flaws only.** Tag filters already pass through `player_only_gate`; no opponent scoring needed.
- **D-06: Games tab.** The range joins the single flaw `EXISTS`, so it combines with severity, tags and tactic
  filters on the same flaw row.
- **D-07: Provisional values.** Until 250-10 runs, scores come from unrepaired lines and pre-refit constants. The
  owner accepts this; no "provisional" note in the UI and no code change is needed after 250-10.

### Filter control shape
- **D-08: Presets plus slider.** A third wrapper over the shared `PresetRangeFilter`, same look as Tactic Depth:
  label with info popover, active summary, preset chips, two-handle slider.
- **D-09: Four presets, fixed cutoffs at 30% and 70%.** All = 0-100 (no filter), Low = 0-29, Mid = 30-69,
  High = 70-100. The cutoffs are plain UI constants, independent of `FACEPALM_SCORE_MIN`; they do not move when
  the drill cut is refitted. (The owner considered thirds at 33/66 and settled on 30/70.) All is the default.
- **D-10: Slider step 5%.** The upper handle covers its whole 5% bucket, so the bounds are half-open on the top
  side: Low puts the handles at 0 and 25 and matches score < 30; Mid at 30 and 65, matching 30 <= score < 70;
  High at 70 and 100. A handle at 100 includes 100%. Chip labels and the summary still read 0-29, 30-69, 70-100.
  How the half-open rule is split between frontend and API params is the planner's call, but a score of 27% must
  land in Low and 69.9% in Mid.

### Narrowed-range behavior
- **D-11: Severity toggles are left alone.** No dimming, no coupled state. With Mistakes selected and a narrowed
  range, mistakes simply return nothing.
- **D-12: Hint while narrowed.** A one-line note under the slider, shown only when the range is not All:
  **"Mistakes are excluded"**. Do not mention unscored blunders: basically all blunders are scored once Phase 252
  and 250-10 finish (owner).
- **D-13: Panel position.** Directly under the Flaws section (Blunders / Mistakes toggles), above Best Moves and
  Tactic Depth, on both tabs.

### Chip on the Flaws-tab card
- **D-14: Placement.** In the tags row, directly after the Blunder severity badge and before the tactic motif
  chips. Not a metadata line: the owner first asked for a line under the engine eval-drop line, then withdrew it
  because the metadata stack has no room.
- **D-15: Neutral color.** Muted text on a neutral bordered pill, identical for every value. No grading by band,
  no blunder red.
- **D-16: The chip is its own popover trigger** (tap on mobile, click on desktop). No Facepalm entry in the
  shared Tags legend.
- **D-17: Rendered only when `facepalm_score` is non-NULL.** Nothing otherwise.

### Popover copy (owner-approved wording)
- **D-18: Chip popover.**
  > How obvious this blunder was for a player at your level, as judged by our model. High means a careless slip,
  > low means it was hard to see. Not a probability.
- **D-19: Filter info popover.**
  > How obvious a blunder was for a player at your level, as judged by our model. High means a careless slip, low
  > means it was hard to see. Not a probability.
  >
  > Low keeps 0 to 29%, Mid 30 to 69%, High 70 to 100%. Drag either handle for a custom range. Any range other
  > than All shows blunders only.

  No mention of the blunder-check drill or its cut.

### Claude's Discretion
- **Percent rounding:** whole percent, rounded down, so a chip value always agrees with the filter band (a score
  of 0.697 shows 69% and sits in Mid). Offered to the owner at the area check, no objection.
- Summary text format in the label row, and when it renders in the active style (follow Tactic Depth: active
  when the range is not the default).
- Filter-store fields, the active-filter dot, URL/persistence: follow the tactic depth pattern.
- Umami event target and values (preset key or `custom`, never the bounds), `data-testid` names, the exact
  neutral chip tokens from `theme.ts`.
- API param names and whether the score travels as 0-1 or 0-100.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and prior decisions
- `.planning/seeds/SEED-261114-0ke-facepalm-score-library-ui.md` — owner decisions on name, icon, semantics,
  scope; breadcrumbs to every touched file
- `.planning/ROADMAP.md` (Phase 253 entry) — goal, dependency on Phase 250, provisional-values note
- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md` — D-01 (score definition, "a ranking, not a
  probability"), D-05/D-06 (stored columns, user blunders only), D-18 (recompute after Phase 252)
- `.planning/seeds/SEED-261114-iuv-facepalm-rate-library-stats.md` — what is deliberately NOT in this phase

### Project rules
- `CLAUDE.md` — shared query filters in `query_utils.py`, `Literal` types, no magic numbers, nesting depth gate
- `frontend/CLAUDE.md` — styling via `theme.ts`, test ids, Umami tracking rules

No external specs beyond these.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/filters/PresetRangeFilter.tsx` — presentational label + info popover + summary +
  preset chip grid + dual-thumb slider. The Facepalm filter is a third wrapper next to `TacticDepthFilter` and
  the opponent strength filter. It has no slot for a hint line yet (D-12 needs one, or the wrapper renders it).
- `frontend/src/components/filters/TacticDepthFilter.tsx` and `frontend/src/lib/tacticDepth.ts` — the wrapper
  and the constants/preset/summary module to mirror (`derivePreset`, `presetToRange`, `sliderToRange`,
  debounced commit tracking).
- `frontend/src/components/library/SeverityBadge.tsx`, `TagChip.tsx` — chip shape and hover/focus treatment to
  match for the new chip.
- `app/services/facepalm_score.py`, `app/models/game_flaw.py` (`facepalm_score` REAL, nullable).

### Established Patterns
- Full range means no clause: `_TACTIC_DEPTH_FULL_MIN/MAX` in `app/repositories/library_repository.py`.
- Router params: `min_tactic_depth` / `max_tactic_depth` in `app/routers/library.py` (two endpoints, lines ~73
  and ~321) are the pattern to copy.
- All flaw filtering goes through `build_flaw_filter_clauses` and `flaw_exists_from_table` in
  `library_repository.py`, and the flaw `EXISTS` in `apply_game_filters` (`app/repositories/query_utils.py`).
  Add the score clause there once, not per endpoint.
- Other chips on the flaw card take `showDefinitionPopover={false}` and rely on the shared legend; the Facepalm
  chip is the exception (D-16).

### Integration Points
- `frontend/src/components/filters/FlawFilterControl.tsx` — insert the filter after the severity block (line
  ~548), before Best Moves; new `facepalm` value/onChange props.
- `frontend/src/hooks/useFlawFilterStore.ts` — min/max state, defaults, `isFlawFilterNonDefault`.
- `frontend/src/components/library/FlawCard.tsx` — `tagsRow` (line ~347): chip goes right after `SeverityBadge`.
- `app/schemas/library.py` — add the score to the flaw card schema; regenerate any derived frontend types.

### Data note
Dev DB, 2026-11-14: 4,557 scored flaws; 49% below 30%, 24% in 30-69%, 27% at 70%+, 18% at 90%+ (bimodal).

</code_context>

<specifics>
## Specific Ideas

- Panel layout the owner picked:
  ```
  Flaws
  [ Blunders ] [ Mistakes ]
  Facepalm (i)            70-100%
  [All] [Low] [Mid] [High]
   o=============o
  Best Moves
  [ Gem ] [ Great ]
  Tactic Depth ...
  ```
- Card tags row: `[Blunder] [<TreePalm> Facepalm 94%] [Missed: Fork] ...` with the facepalm chip in neutral grey.
- Hint text is exactly "Mistakes are excluded".

</specifics>

<deferred>
## Deferred Ideas

- Facepalm rate stats and opponent scoring — SEED-261114-iuv.
- Score in the blunder-check solution screen — dropped by the owner in the seed.
- Tying the High preset to the drill cut, and a drill mention in the filter popover — rejected for now; revisit
  only if the 250-10 refit moves `FACEPALM_SCORE_MIN` far from 70.

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`,
  `2026-08-29-variation-tree-nested-button.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` —
  keyword matches only, unrelated to this phase.

</deferred>

---

*Phase: 253-Facepalm Score in the Library UI*
*Context gathered: 2026-11-14*
