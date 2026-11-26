# Phase 253: Facepalm Score in the Library UI (SEED-261114-0ke) - Context

**Gathered:** 2026-11-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Show the Phase 250 `facepalm_score` to users in the library:

1. A **Facepalm range filter** in the Tags side panel, on the Games and Flaws tabs.
2. The score **inside the Blunder badge** on Flaws-tab cards (`Blunder <TreePalm> N%`), with a popover on the
   badge, when the flaw has a score.

Backend: min/max score query params on the library endpoints, one clause in the shared flaw filter, the score on
the flaw card schema. No migration, no backfill, no opponent scoring.

Out of scope: the score in the blunder-check solution screen; facepalm rate stats and opponent scoring
(SEED-261114-iuv); any change to the score itself or to `FACEPALM_SCORE_MIN`.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (seed and roadmap, owner 2026-11-14; not re-discussed)
- **D-01: Name and casing.** "Facepalm", capitalized, as the filter label and in popover copy. UI, code and docs
  all say facepalm. (Revised 2026-11-14: the card no longer shows the word, see D-14.)
- **D-02: Icon.** lucide `TreePalm`. (Revised 2026-11-14, owner: on the Flaws card the icon stands without the
  word, inside the Blunder badge, see D-14. The popover names it.)
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

### Score on the Flaws-tab card (revised 2026-11-14 during planning, owner; replaces the separate chip)
- **D-14: Inside the Blunder badge, no new chip.** The Flaws-card severity badge reads
  `Blunder <TreePalm> 94%` when the flaw has a score: the word, then the icon, then the whole percent.
- **D-15: Badge styling unchanged.** The score inherits the Blunder badge colors (`SEV_BLUNDER*`). No neutral
  pill, no grading by band.
- **D-16: The Blunder badge is the popover trigger** when it carries a score: opens on hover (desktop pointer)
  and on click or tap (owner, 2026-11-14). Keyboard focus should open it too. No Facepalm entry in the shared
  Tags legend.
- **D-17: Only when `facepalm_score` is non-NULL.** Without a score the badge is exactly today's plain,
  non-interactive `Blunder` span, with no popover. Mistake and Inaccuracy badges never change. The Games-card
  count badges (`3 Blunders`) are untouched.

### UAT revision (owner feedback, 2026-11-14, commit 20127b5cc; supersedes D-14 to D-16, D-18, D-19 where they conflict)
- **D-20: The score is its own chip again.** On the Flaws card a `<TreePalm> Facepalm 94%` pill sits right after
  the Blunder badge, sized and colored like the neutral context tags (`FACEPALM_CHIP*` in theme.ts), not blunder
  red. Replaces D-14 and D-15. The chip is the popover trigger with the D-16 behavior (hover, click or tap,
  keyboard focus). D-17 still holds: scored blunders only.
- **D-21: Severity badges lead with the move-quality glyph** on the Flaws card (`??` / `?`, the move-list icon).
  Games-card count badges stay icon-less.
- **D-22: The score also shows on the analysis surfaces.** Analysis move list: a `<TreePalm> 95%` mini-chip after
  the `??` glyph of a scored blunder, with the same explanation popover. Eval chart tooltip: a `Facepalm 95%`
  line below the severity verdict. `FlawMarker` carries `facepalm_score` for this. No opponent scoring is added:
  only rows that already have a score show one (wording switches to "their level" if an opponent row ever does).
- **D-23: One shared explanation copy, filter renamed "Facepalm Score".** Replaces the D-18 and D-19 wording:
  > How easy it is to see for a player at your level that the move is a blunder, as estimated by our model. A high
  > facepalm score means it should be easy to see, low means it's probably hard to see.

  The filter popover keeps its second paragraph (band ranges). The explicit "Not a probability." sentence is
  dropped; D-03 still bans probability wording.

### Popover copy (owner-approved wording)
- **D-18: Blunder badge popover.** A heading line `Facepalm 94%` (the word names the icon, owner 2026-11-14),
  then:
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
- Umami event target and values (preset key or `custom`, never the bounds), `data-testid` names, the icon size
  and spacing inside the badge, the badge `aria-label` (it must say "Facepalm", since the icon carries no text).
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
- `frontend/src/components/library/SeverityBadge.tsx` — gains the optional score and popover (D-14, D-16). It is
  a plain span on the Flaws card today (no `onHover`/`onActivate`); `TagChip.tsx` shows the popover-trigger
  hover/focus treatment to match.
- `app/services/facepalm_score.py`, `app/models/game_flaw.py` (`facepalm_score` REAL, nullable).

### Established Patterns
- Full range means no clause: `_TACTIC_DEPTH_FULL_MIN/MAX` in `app/repositories/library_repository.py`.
- Router params: `min_tactic_depth` / `max_tactic_depth` in `app/routers/library.py` (two endpoints, lines ~73
  and ~321) are the pattern to copy.
- All flaw filtering goes through `build_flaw_filter_clauses` and `flaw_exists_from_table` in
  `library_repository.py`, and the flaw `EXISTS` in `apply_game_filters` (`app/repositories/query_utils.py`).
  Add the score clause there once, not per endpoint.
- Other chips on the flaw card take `showDefinitionPopover={false}` and rely on the shared legend; the scored
  Blunder badge is the exception (D-16).

### Integration Points
- `frontend/src/components/filters/FlawFilterControl.tsx` — insert the filter after the severity block (line
  ~548), before Best Moves; new `facepalm` value/onChange props.
- `frontend/src/hooks/useFlawFilterStore.ts` — min/max state, defaults, `isFlawFilterNonDefault`.
- `frontend/src/components/library/FlawCard.tsx` — `tagsRow` (line ~347): pass the score to `SeverityBadge`; no new element.
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
- Card tags row: `[Blunder <TreePalm> 94%] [Missed: Fork] ...`, the badge in its usual blunder colors.
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
