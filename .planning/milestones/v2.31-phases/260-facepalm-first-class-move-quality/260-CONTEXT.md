# Phase 260: Facepalm as a First-Class Move Quality - Context

**Gathered:** 2026-11-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Facepalm blunders (blunders with a facepalm score at or above the stats cut) become a move quality of their
own, split from Blunder in the same way everywhere a player picks or counts move qualities: a row in the
game card's move quality table, a dot on the eval chart, and a "Facepalm" tag in the Flaws filter. The
Facepalm Score range filter is removed, in the UI and in the API.

In scope:

- `MoveStats` (Library game card and `/analysis` tags panel): an 8th "Facepalm" row, split from Blunder.
- The mobile compact row of the game card.
- The eval chart flaw dots and their tooltip.
- The Flaws filter: a third tag "Facepalm" next to Blunder and Mistake, and the new meaning of Blunder.
- Removal of the Facepalm Score range filter: the frontend control, its store fields and query parameters,
  and the backend `min_facepalm_pct` / `max_facepalm_pct` parameters.
- Backend: the severity filter of the shared flaw clause builder accepts the facepalm value.
- The desktop game card's miniboard size, which grows with the 8-row table.

Out of scope: the facepalm score model, the cut value (Phase 259, plan 259-12), the Library Stats page
content, Train, Blunder Check, and any replacement filter for hard-to-see blunders.

</domain>

<decisions>
## Implementation Decisions

### Move quality table (game card and /analysis)

- **D-01: Facepalm is an 8th two-sided row, a main category like the other seven.** Label "Facepalm", the
  existing "???" icon (257 D-22). It is the last row, after Blunder. Not a nested "of which" line (rejected by
  the owner in the explore session). The same 8 rows render in `AnalysisTagsPanel`.
- **D-02: Blunder and Facepalm are disjoint in this table.** Blunder row = blunders that are not facepalms
  ("??" moves), Facepalm row = facepalm blunders ("???" moves). Every move sits in exactly one row, like
  Best vs Gem / Great, and the counts match the icons drawn on the chart and board.
- **D-03: Definition of a facepalm here:** `severity === 'blunder' && isFacepalmBlunder(facepalm_score)`.
  A blunder without a score is never a facepalm and stays in the Blunder row.
- **D-04: Cell cycling follows the split.** The Blunder cell cycles through the "??" plies only, the
  Facepalm cell through the "???" plies only. Zero-count cells stay inert as today.
- **D-05: Mobile compact row:** Gem, Great, Best, Mistake, Blunder, Facepalm, chevron (7 cells, today 8).
  Inaccuracy and Good leave the compact row only; the expanded table keeps all 8 rows. Counts and cycling
  stay scoped to the user's side as today, with the D-02 split.
- **D-06: Info popover (`MoveStatsInfo`).** Add the Facepalm definition to the list, in the wording family
  of the existing facepalm copy: a blunder that should have been easy to see for a player at the mover's
  level. The Blunder definition stays "Costs 15% winning chances or more." The Lichess sentence gains one
  statement: blunders and facepalms together match the Lichess blunder count. Do not state the cut as a
  literal; read `FACEPALM_HIGH_CUTOFF` if the number is shown at all.
- **D-07: Where the split applies.** The move quality table, the eval chart and the Flaws filter tags use
  the split (Blunder = not a facepalm). Everywhere else "blunder" keeps its Lichess meaning, facepalms
  included: Library Stats, the Flaws Timeline, the KPI tiles, accuracy, and the severity stored and
  returned by the API. No blanket copy change.

### Flaws filter

- **D-08: Three tags in the Flaws row, labelled in the singular and in this order: Facepalm, Blunder,
  Mistake.** Today's "Blunders" / "Mistakes" labels become singular, consistent with the Gem / Great tags. They combine with OR like every
  tag section; nothing selected shows everything, as today. The Facepalm tag uses the "???" icon and the
  dark red `SEV_FACEPALM` in the pill style of the other two.

  | Selected | Listed |
  |---|---|
  | Facepalm | facepalm blunders |
  | Blunder | blunders that are not facepalms (below the cut, or unscored) |
  | Blunder + Facepalm | all blunders |
  | Mistake + Facepalm | mistakes and facepalm blunders |
  | nothing, or all three | all mistakes and blunders |

- **D-09: The Blunder tag now means "blunder that is not a facepalm",** the same split as the table
  (D-02, D-03). An unscored blunder counts as a Blunder. Owner's reasoning: it matches the move quality
  list and the way the Gem / Great tags work.
- **D-10: The Facepalm Score range filter is removed.** No slider, no presets, no hint. Supersedes
  253 D-04 and D-09 to D-12 and this session's first outcome (the "???" on the High preset and a range that
  applies to blunders only). Reasoning: the score is a model output that supports a cut, not 5% steps;
  Gem / Great and the severities are also cuts on continuous quantities with no slider; a hard-to-see
  blunder is the unremarkable case, like a plain Best move. Known loss, accepted by the owner: no way to
  filter for very hard-to-see blunders (0 to 30% apart from 30 to 70%).
- **D-11: The facepalm score stays visible** where it is today (the chip on the Flaws card, the eval chart
  tooltip, the move list, `FacepalmExplanation`). Only the filtering by range goes.
- **D-12: Backend, severity filter.** The shared flaw clause builder in
  `app/repositories/library_repository.py` accepts the facepalm value in the severity filter and applies
  D-08, using `FACEPALM_STATS_MIN` for the cut, so the Games tab, the Flaws tab and every other caller of
  the builder agree. The stored severity and `FlawSeverity` (inaccuracy / mistake / blunder) do not change:
  the filter value set is its own `Literal`. No migration.
  — **Reversibility:** reversible — a query-clause change; the request parameter keeps its name and gains
  one accepted value.
- **D-13: Backend, parameter removal.** `min_facepalm_pct` / `max_facepalm_pct` are removed from the API
  (router, service, repository, `query_utils.py`) together with `_facepalm_clause` and helpers that have no
  reader left. This is the last plan of the phase and runs after Phase 259 has merged to `main`, so it does
  not collide with plans 259-13 and 259-14 in the same files.
  — **Reversibility:** costly — the parameters run through about 15 function signatures; bringing a range
  filter back means re-threading them (git history has the shape).
- **D-14: Frontend removal.** `FacepalmFilter`, the `facepalmMin` / `facepalmMax` store fields, the query
  parameter mapping and the range, preset and summary helpers in `lib/facepalm.ts` that lose their last
  reader (knip gates this). `FACEPALM_HIGH_CUTOFF`, `isFacepalmBlunder`, `toFacepalmPct` and the copy
  constants stay. Any persisted filter state that still carries the range fields must load cleanly.

### Desktop game card height

- **D-15: The miniboard grows with the table.** The 8th row keeps today's row spacing; the desktop
  miniboard (`DESKTOP_BOARD_SIZE`, 225 in `LibraryGameCard.tsx`, local to that file) is enlarged so the
  board and the move quality card still end level. Every desktop game card gets taller by about one row.
  Rejected: tightening the rows to keep 225px, and letting the card overhang the board.
- **D-16: Everything that is sized to the miniboard height follows it** (the eval chart block and the lane
  row next to the board). The new size is derived from the table, not picked by eye. Mobile sizing
  (`MOBILE_BOARD_SIZE`, 50% viewport) is untouched.

### Eval chart and filter emphasis

- **D-17: A facepalm blunder's dot is dark red.** Use the existing `SEV_FACEPALM` (theme.ts, equal to the
  Flaws Timeline band swatch); no new theme constant. It applies to every blunder dot that is drawn today,
  for either side, in the normal, highlighted and dimmed states alike. This reverses the "eval-chart flaw
  dots" exclusion of 257 D-22.
- **D-18: The chart tooltip of a facepalm blunder shows the "???" icon** in place of "??", in the same
  dark red.
- **D-19: Highlighting follows D-04:** cycling or hovering the Blunder cell highlights only "??" dots, the
  Facepalm cell only "???" dots.
- **D-20: The filter ring (`outlinedRef`) marks the cells whose tags are selected,** on the user's side:
  Blunder rings the Blunder cell, Facepalm the Facepalm cell, Mistake the Mistake cell. With several tags
  selected (but not all three) each selected cell is ringed, so a single `outlinedRef` no longer suffices.
  Nothing selected, or all three: no ring, as today for "both".

### Parallel work with Phase 259

- **D-21: The cut belongs to plan 259-12.** This phase never changes the value of `FACEPALM_HIGH_CUTOFF`
  or `FACEPALM_STATS_MIN` and never states the cut as a literal in code, copy or tests. Removing the range
  presets (D-14) deletes `FACEPALM_MID_CUTOFF` and `PRESET_RANGES`; 259-12 only moves the High cutoff, so
  the overlap in `frontend/src/lib/facepalm.ts` is one constant that this phase leaves untouched.
- **D-22: The final visual UAT and the merge wait for 259-12** (the switch release), since the refit
  changes which blunders count as facepalms. Planning and execution of everything but D-13 can run before.
- **D-23: Order of the backend work.** D-12 (the new severity value) is small and local to the clause
  builder and can run now. D-13 (parameter removal) waits for Phase 259 on `main` and is then rebased
  onto it.

### Decided after research (2026-11-22, owner answers to the open questions in 260-RESEARCH.md)

- **D-24: Opponent blunders carry their facepalm score in the game card and `/analysis` payload.** The
  owner-only gate in `fetch_page_facepalm_scores` (`app/repositories/library_repository.py`) is dropped, so
  the Facepalm row and the chart split work for both sides (D-01, D-17). Accepted side effect: an
  opponent's "???" also shows on the move list, the board badge, the Explain bar and the chart tooltip.
  The Flaws filter and drill selection stay user-only (257 D-06 is unchanged there). This settles the
  "open product decision" named in that function's docstring.
  — **Reversibility:** reversible — one gate in one fetch; no stored data changes.
- **D-25: The desktop eval chart grows with the board (D-16 as written).** The chart is a fixed 104px
  today; it takes the extra height the taller miniboard creates, so the tags card does not absorb it.
- **D-26: Tooltip of a facepalm blunder (D-18):** the "???" icon replaces the dot glyph, in `SEV_FACEPALM`,
  and the line reads "You · Facepalm" / "Opponent · Facepalm". The tooltip is one of the split surfaces of
  D-07, like the table and the chart.
- **D-27: The `SeverityBadge` ring on the Flaws card and the Train card follows D-20.** The badge is
  ringed when its own tag (Facepalm for a "???" badge) is part of a narrowing selection; no ring when
  nothing or all three tags are selected.

- **D-28: The filter ring also marks the Gem and Great cells** (owner request, 2026-11-22, during
  planning). When the "has gem" / "has great" filter tag is selected (`hasGem` / `hasGreat` in
  `useFlawFilterStore`), the user's Gem / Great cell in the move quality table is ringed, with the same
  ring as the severity cells of D-20. Today these tags ring nothing. Each selected tag rings its own cell,
  independently of the Flaws tags, on the user's side only, and nowhere in `AnalysisTagsPanel` (no ring
  there). The multi-cell ring of D-20 carries these cells too.

### Claude's Discretion

- A `SEV_FACEPALM_BG` theme constant for the selected Facepalm pill, in the existing `SEV_*_BG` convention.
- Whether the mobile compact row shows the filter ring (research recommends yes).
- CHANGELOG: add new Changed / Removed bullets instead of rewriting bullets of the already deployed range
  filter; reconcile Phase 259's wording at merge.
- Wording of the Facepalm definition in `MoveStatsInfo` and of the Lichess sum sentence, within the
  popover-copy rule and "eval, not pawns". Whether the Flaws filter needs a line saying Blunder excludes
  facepalms, and where.
- The name and type of the facepalm filter value on the wire, and the type shape for the 8th category
  (`MoveStatCategory`) and for a multi-cell ring.
- Analytics: the `severity` filter-change target gains the facepalm value; the `facepalm` filter-change
  target loses its only caller and is removed from the registry (a removal, not a rename).
- How D-13 is split and ordered relative to the merge of Phase 259.
- Test updates, including backend tests for the D-08 table.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Origin and prior decisions
- `.planning/seeds/SEED-261122-j9p-facepalm-first-class-move-quality.md` — the seed: why, the decisions of
  the explore session, breadcrumbs. Its decision 5 (a Facepalm button beside a kept range filter), its "shortcut onto the
  slider" recommendation and its "frontend only" scope are superseded by D-08 to D-14 above.
- `.planning/phases/253-facepalm-score-library-ui/253-CONTEXT.md` — the range filter this phase
  removes (D-04, D-09 to D-12, all superseded by D-10 here). Read it to find everything that was built.
- `.planning/phases/257-facepalm-rate-library-stats/257-CONTEXT.md` — D-22 (the "???" badge,
  `SEV_FACEPALM`, where it is drawn; its "not changed" list for the eval chart dots and the Move Stats
  counts is reversed here), D-08 and D-10 (type tint and labels).
- `.planning/ROADMAP.md` §Phase 260 — the phase entry and the parallel-work rule with Phase 259.

### Project rules
- `CLAUDE.md` — backend layout, ty and ruff gates, no magic numbers, the pre-merge gate.
- `frontend/CLAUDE.md` — theme constants in `theme.ts`, `text-sm` floor, testids, apply changes to mobile
  too, `trackFeature` rules, `npm run build` for type changes, knip.

No external specs. Requirements are fully captured in the decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/facepalm.ts`: `isFacepalmBlunder`, `FACEPALM_HIGH_CUTOFF`, `PRESET_RANGES`,
  `derivePreset`, `isFacepalmNarrowed`, the shared definition strings (`FACEPALM_CARD_INFO` and friends).
- `frontend/src/lib/theme.ts`: `SEV_FACEPALM` (= `FACEPALM_BAND_SWATCH`) already exists.
- `frontend/src/lib/severityGlyph.ts`: `FACEPALM_GLYPH`, the "???" glyph spec.
- `frontend/src/components/icons/MoveQualityIcon.tsx`: the row icon component; check how the "???" icon is
  rendered elsewhere before adding a quality value.
- `frontend/src/hooks/useGameOverlay.ts` and `LibraryGameCard.tsx` (`facepalmPlies`): the set of facepalm
  plies per game is already computed for the hover miniboard.
- `app/repositories/library_repository.py`: `_facepalm_clause`, `facepalm_range_active`,
  `FACEPALM_STATS_MIN` (pinned to the frontend cut by test).

### Established Patterns
- `MoveStats.tsx` drives rows, labels, definitions and the compact row from `CATEGORY_ORDER`; the compact
  row is `grid-cols-8` (7 categories + chevron) and needs its own category list after D-05.
- `moveStatsCounts.ts`: `MoveStatCategory` is its own type, deliberately not `FlawSeverity` (which stays
  3-valued per the backend contract). Counts come from `flaw_markers`, the same array the cycling walks.
- `LibraryGameCard.tsx`: `pliesForRef` maps a cell to its plies; `outlinedCellRef` is a single ref derived
  from `flawFilter.severity` only (no range today).
- `EvalChart.tsx`: `severityColor(sev)` picks the dot and tooltip colour from the severity alone.
- `FlawFilterControl.tsx`: severity toggles are OR within the row, empty = both, driven by
  `SEVERITY_BUTTONS`; `FacepalmFilter` renders directly under them, closed by a divider (both go).
- `useFlawFilterStore.ts` holds `severity` plus `facepalmMin` / `facepalmMax`; the range also feeds the
  "filter is active" check there.

### Integration Points
- `MoveStats` is used by `LibraryGameCard` (desktop and mobile) and `AnalysisTagsPanel` (no ring there).
- The desktop card comment at the accuracy strip notes the card height is tuned to the 225px miniboard;
  the mobile eval block uses a literal height class tied to `MOBILE_BOARD_SIZE`.
- The shared flaw clause builder feeds the Games tab, the Flaws tab and the stats paths that take the
  severity filter or the facepalm range; check each caller for D-08 and for D-13.
- The range parameters are wired through `frontend/src/api/client.ts`, `frontend/src/hooks/useLibrary.ts`,
  `app/routers/library.py`, `app/services/library_service.py`, `app/repositories/library_repository.py`
  and `app/repositories/query_utils.py`.

</code_context>

<specifics>
## Specific Ideas

- The filter should read like the move quality list: what a tag selects is exactly what its row counts.
- The purpose (GM Noel Studer's criticism of the usual blunder definition): the blunders worth a player's
  attention are the ones they should have seen at their level. One click on Facepalm leads straight to them.
- Owner rule: tags within one filter section combine with OR.
- Do not argue from usage data here: the score filter had only just shipped.

</specifics>

<deferred>
## Deferred Ideas

- **A filter for very hard-to-see blunders.** Lost with the range filter (D-10). If a need shows up, it
  returns as its own control designed for that purpose, not as a second control on the facepalm dimension.

### Reviewed Todos (not folded)
- The todo matcher returned keyword matches only (an invalid Tailwind class on a Score axis label, deferred
  review findings of Phase 172, bitboard storage). None concerns this phase.

</deferred>

---

*Phase: 260-Facepalm as a First-Class Move Quality*
*Context gathered: 2026-11-22*
