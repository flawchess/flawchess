# Phase 242: Openings Stats + Insights Rework (SEED-204) - Context

**Gathered:** 2026-10-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Rework the Openings Stats and Insights tabs the way Phases 238/239 reworked the Endgame and Library Stats
pages: simpler, more readable, no loss of information. Implements sketch 012 (Round 2 winner). Insights merge
into the Stats tab (findings above a per-colour repertoire table under one sticky White | Black switch); the
eval verdict is re-centred on the colour baseline for the Openings tab only; most-played rows are deduped and
split into current vs past repertoire.

ONE phase, several plans: a backend wave first, then the frontend rework (owner decision 2026-10-17).

**The full locked design lives in SEED-204 "Locked decisions" and sketch 012 README "Round 2".** Those are
binding and are not repeated here; the decisions below resolve the items SEED-204 left "Open for
discuss-phase" and record defaults for the rest.

</domain>

<decisions>
## Implementation Decisions

### Locked upstream (summary only, read SEED-204 for the full list)
- **D-00:** All SEED-204 "Locked decisions" apply verbatim: Insights merged into Stats (subtab + mobile tab +
  route removed), one sticky colour switch (not persisted), 99% findings gate with top 5 per section,
  finding-card layout, repertoire table columns (Opening · Games · Results · Score · Eval after opening),
  rows <20 games faded and never coloured, duplicate-row collapse, expanded row contents, `ScoreChart` reuse
  with optional weekly volume bars, multi-line bookmark chart dropped, eval centred on the colour baseline
  (Openings tab only: Moves, Games, Stats; Endgames `evalContext="endgame-entry"` unchanged), popover
  footers with 99% CI + p + reference + n, no ECO codes, no "pawns" unit, "After the opening" dropped.
  The 238/239 system decisions D-14..D-17 apply unchanged.
- **D-00b:** Score band stays the shared ±5% (45–55%, today's `SCORE_BULLET_NEUTRAL_*`). Benchmark §2 pooled
  IQR [46.1%, 57.3%] confirms keeping it; no re-derivation in this phase.

### Current vs past repertoire cutoff
- **D-01:** An opening is **current** when it was last played within the user's last 200 games of that colour
  **OR** within the last 60 days, whichever reaches further back. Everything else is "past".
  Rationale (prod check 2026-10-17, 1,276 user×colour pairs): with a pure 200-game rule, users with
  1000+ games per colour get a window of only ~61–68 days median and ~15–17 days at p10, so an opening
  last played 3 weeks ago would be "past". The 60-day floor fixes that and leaves light users unchanged
  (<200 games per colour = everything current; 466 of 1,276 pairs).
- **D-02:** The cutoff is computed **under the active sidebar filters** (TC, platform, rated, opponent type,
  recency, etc. via `apply_game_filters()`), per colour. "Current" stays consistent with the rows shown.
- **D-03:** Constants, not magic numbers: e.g. `CURRENT_REPERTOIRE_RECENT_GAMES = 200`,
  `CURRENT_REPERTOIRE_MIN_DAYS = 60`. The day floor anchors on `now_utc` from the `dev_now_utc` dependency
  (`app/core/dev_clock.py`), never `datetime.now()`.
- **D-04:** The cutoff drives all three SEED-204 uses: most-played rows → "Played before (n)" group; stale
  bookmarks stay pinned with a "not played recently" chip; findings from older games get an "older games"
  chip and sort after current ones. Backend returns the cutoff date (or a per-row `is_current` flag; planner
  picks) so the frontend does not re-derive it.

### Most-played row count
- **D-05:** Per colour, show **up to 10 current rows** in the main table and **up to 10 past rows** in the
  collapsed "Played before (n)" group. The backend fetches enough candidates before dedupe and the split
  (order of 30 per colour; planner/researcher sizes it) so past openings never push current ones out.
  Replaces the single `TOP_OPENINGS_LIMIT = 10` (`app/services/stats_service.py:41`) with named limits for
  current/past plus a fetch limit.
- **D-06:** Order of operations: fetch → dedupe (identical game sets keep the deeper line; most-played rows
  duplicating a same-colour bookmark position are dropped, bookmark wins) → split current/past → cap each
  at 10. Bookmarks are never capped and never dropped.
- **D-07:** Minimum game count for a most-played row is unchanged (`MIN_GAMES_FOR_OPENING = 1`). The faded
  <20-games styling carries the low-sample signal, in both the current table and "Played before".

### Findings density
- **D-08:** Phone shows **2 finding cards per section**, then a "Show more" control expanding to the 5-card
  cap. Desktop/tablet shows all 5 (2-column grid). "Show more" needs a testid and an Umami event
  (frontend/CLAUDE.md).
- **D-09:** The faded "Not clear yet (n)" list holds **only medium-confidence candidates (p < 0.05, not at
  99%)**. Low-confidence rows are dropped as noise (D-17). The header count `n` is the full count of medium
  candidates for that section.
- **D-10:** "Not clear yet" shows at most **10 rows**, sorted by strongest p first (lowest p), with current
  findings before "older games" ones (same rule as the cards). No colour, faded, collapsed by default.
- **D-11:** The empty-state copy ("Nothing clear yet as Black. 3 moves lean this way…") counts the same
  medium-confidence candidates as D-09.

### Claude's Discretion (defaults accepted by owner, 2026-10-17)
- **D-12:** Plan split: backend wave first (eval baseline centring + z-test, dedupe, current/past cutoff,
  row limits, weekly game counts per time series), then frontend plans. Planner decides plan granularity.
- **D-13:** The baseline-centred eval z-test ships in this phase for **all Openings call sites**, including
  the Moves tab (`openings_service.py:190`), alongside `stats_service.py` (most-played + bookmark phase-entry
  metrics) and `opening_insights_service.py:407`. `endgame_service.py` stays untouched. Update the "H0 = 0 cp,
  baseline is only a tick" comments (`stats_service.py` ~line 425, `opening_insights_constants.py`,
  `app/schemas/stats.py:89`).
- **D-14:** `ScoreChart`'s multi-bookmark mode is **retired**: `pages/openings/StatsTab.tsx` is its only
  caller. It becomes a single-opening chart with the optional weekly volume series.
- **D-15:** `/openings/insights` and any insights deep links (`useDeepLinkHighlight`, `useTabReset`,
  `useOpeningsHandlers`) **redirect to `/openings/stats`** (not a 404).
- Exact copy for chips, "Show more" and "Played before (n)" follows sketch 012 and the popover-minimalism
  rule; planner/UI phase may tune wording.

### Post-research decisions (owner, 2026-10-17, answering 242-RESEARCH.md open questions)
- **D-16:** The per-bookmark "Include in opening results" toggle (localStorage) is **retired**, together with
  its localStorage state. It only fed the dropped multi-line bookmark chart, and server-side bookmark-twin
  removal (D-06) would make an excluded bookmark's opening vanish from the table.
- **D-17:** The Moves and Games tabs get the **new 238/239-style eval verdict bar** (baseline-centred, ±0.30
  band, 99% red/green, popover with greyed stats footer), replacing their current eval `MiniBulletChart`
  display for `evalContext="opening-end"`. Endgames (`evalContext="endgame-entry"`) keeps its current display
  unchanged. This extends D-13 from backend-only centring to the Moves/Games UI.
- **D-18:** Bookmark Score p-value and 99% CI are computed **server-side** and returned in the
  `/openings/time-series` response, using the same score/Wilson util as the most-played rows.
- **D-05 (clarified, owner 2026-10-17):** the fixed top-60 fetch is not enough on its own. When fewer than
  10 current rows survive dedupe and the split, the backend runs a **second top query limited to games
  since the current/past cutoff** and merges its rows, so past openings never push current ones out.
  Plan sizing warnings (01 over budget ~10%, 06 at 18 files) were accepted as is; no further splits.

### Post-UAT decisions (owner, 2026-10-17)
- **D-19:** The repertoire table is replaced by **cards** (2 columns from lg, 1 below): name header, 128 px
  board, WDL bar with "N games · last played", Score and Eval verdict bars, Moves / Games / Bookmark links and a
  "Score over time" toggle that opens the chart inside the card. Reason: 44 px row boards were too small on
  desktop, expanding rows to see the board was impractical, and the stacked mobile rows read worse than the
  old cards. Supersedes the table / sticky column header / expanded-row parts of D-00.
- **D-20:** The findings gate **stays at p < 0.01**. "Not clear yet" moves render as the same finding cards
  (uncoloured verdicts, neutral arrow, no fade) instead of the faded mini-board list; amends D-10's "faded".
- **D-21:** No move sequences on repertoire cards or finding cards; the board shows the position.
- **D-22:** Score-over-time chart: no rotated "Score" y-axis label and no caption line under it.
- **D-23:** lucide `BookMarked` is replaced by `Bookmark` everywhere.
- **D-24:** Stats tab section order is **Bookmarks, Most Played, Moves that Cost You, Moves that Work**
  (findings move below the repertoire; amends D-00's "findings above"). Every section heading is an h2 in
  Fredoka (`font-brand`); the "Opening insights" umbrella heading and its explanation paragraph are dropped.
  Each findings section carries its "You score clearly below/above 50%." line under the heading.
- **D-25:** No "Playing as" label in the colour switch row. Repertoire cards drop the "N games · last played"
  line under the WDL bar (the count stays on the Games link); the last-played date sits muted on the right of
  the card header.
- **D-26:** The Stats White | Black switch **is the Played-as filter** (supersedes D-00's "not persisted"
  page state): switching writes the committed filters and the open panel draft, flips the board, and the
  sidebar Played-as button and filter panel follow it. A Played-as change via Apply no longer jumps from
  Stats to Moves (only a Piece filter change still does). Desktop switch is right-aligned.
- **D-27:** The "not played recently" chip is replaced by a muted lucide `Archive` icon right of the
  last-played date, on every card outside the current repertoire window (stale bookmarks and Played before).
  Indicator only, no action.
- **D-28:** The score-over-time chart marks the typical 45-55% range as a grey labelled band, like the
  Clock Gap at Endgame Entry chart. Section headings read "Bookmarked Openings" and "Most Played Openings";
  the Stats tab info popover follows the D-24 order. Repertoire and finding mini boards highlight the last
  played move in yellow (finding cards keep the candidate-move arrow on top).
- **D-29:** The Moves / Games "Results played as" card (shared `PositionResultsPanel`, so the Endgames Games
  subtab too) replaces the Score bullet chart with the verdict track (same 99% / 20-game / +-5-point rule).
  The opening-end End Eval row moves its label, value and popover into the left cell beside its track, the
  same layout as Score. The Score popover is the repertoire `ScoreVerdictPopover` with an extra "Last played"
  bullet; `WDLStats` (and `EndgameCategoryStats`) gain `ci99_low` / `ci99_high` for its 99% CI footer.
- **D-30 (UAT round 7, owner 2026-10-18):** The bottom verdict legend is removed. Each repertoire and finding
  card carries one muted sentence reading the Score and Eval verdicts together (`openingVerdictSentence`,
  `lib/openingVerdict.ts`): only 99%-clear parts are stated, an unclear eval falls back to the score-only
  sentence, and a <20-game card says "Too few games to call it yet." Every cell has a sentence (owner,
  same day: a card without one read as missing), e.g. "An ordinary opening for you: average positions and
  a typical score." and "Nothing clear yet. The differences could still be chance."
- **D-31:** The Stats subtab info popover is removed (Moves/Games popovers stay). Every Stats section h2 gets a
  one-line intro under it (Library Stats pattern); the first repertoire heading also explains Score and Eval.
- **D-32:** Findings density: a section without 99% cards shows its "Not clear yet" cards inline (phone 2,
  desktop 4, then Show more) instead of behind a toggle; the toggle stays only below clear cards. A section
  with neither reads "Nothing stands out as <colour> yet."; both sections empty merge into one
  "Moves that Stand Out" block. The duplicated "n moves lean this way" empty-state copy is gone (amends D-11).

### UAT round 9 decisions (owner, 2026-10-18)
- **D-33:** The Openings verdict gate drops from 99% to **95%** (confidence bucket 'medium' or 'high', p < 0.05)
  on every Openings surface: finding cards, repertoire and bookmark cards, and the Moves / Games "Results
  played as" panel (shared, so the Endgames Games subtab follows). A false positive is cheap and 99% hid too
  much. The popover footers quote the 95% CI, so the separate `ci99_*` / `score_ci99_*` / `eval_ci99_*`
  fields are dropped in favour of the existing 95% `ci_*` / `eval_ci_*` bounds (bookmark and most-played
  score CIs become `score_ci_low` / `score_ci_high`). Endgame Stats and Library keep `VERDICT_CI_Z_99`
  (about 50 cells per page). Amends D-00, D-17, D-18, D-20, D-29, D-30.
- **D-34:** "Not clear yet" is **removed** (it was "p < 0.05 but not at 99%", empty at a 95% gate): no
  not-clear lists or counts in the API, no not-clear cards or toggle. A section with no cards reads
  "Nothing stands out as <colour> yet."; both empty still merge into "Moves that Stand Out". Supersedes
  D-09, D-10, D-11 and the not-clear parts of D-20 and D-32.
- **D-35:** The Moves-tab move list (score text colour, row tint, board arrows) uses the **same verdict rule**
  as the cards (`openingVerdict`: 95% confidence, 20+ games, outside the +/-5-point band), replacing its
  own 10-game / >= 55% rule, so a move and the "Results played as" panel after it never disagree.
- **D-36:** Most Played rows need **at least 20 games** (`MIN_GAMES_FOR_OPENING = 20`, the verdict floor), in
  both the current list and "Played before"; no more padding with 1-3 game openings. The cutoff-restricted
  second fetch (D-05 clarified) stays, under the same floor. Bookmarks are never filtered. Amends D-07.

### UAT round 12 decision (owner, 2026-10-18)
- **D-37:** The findings card cap per section rises from 5 to **10** (`FINDINGS_CARD_CAP`). With 5, current
  findings filled every slot, so significant older-games findings never showed (owner's account: 14 significant
  white strengths, 5 shown). Desktop still shows every card; phone keeps 2 + "Show more". The 95% gate stays.
  Amends D-00's "top 5" and D-08.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked design
- `.planning/seeds/SEED-204-openings-stats-insights-rework.md` — locked decisions and implied work (binding)
- `.planning/sketches/012-opening-stats-repertoire/README.md` — Round 2 decisions (binding)
- `.planning/sketches/012-opening-stats-repertoire/index.html` + `data.js` — visual target (phone/tablet/desktop)
- `.planning/sketches/MANIFEST.md` — "012 →" winner summary

### System decisions carried from 238/239
- `.planning/milestones/v2.25-phases/238-endgame-stats-percentile-first/238-CONTEXT.md` — D-00..D-17 verdict-bar system
- `.planning/milestones/v2.25-phases/239-library-stats-you-vs-opponents/239-CONTEXT.md` — GapBar/GapPopover decisions

### Data / benchmark
- `reports/benchmark/benchmarks-latest.md` §2 (score band IQR) and §2.1 (MG-entry eval baseline +25.21 cp,
  centred IQR [−23, +34] cp → ±0.30 band)

### Related
- `.planning/seeds/SEED-203*` — expected-score refit moved to Endgames (not this phase)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/library/stats/GapBar.tsx`, `GapRow.tsx`, `GapPopover.tsx`, `lib/gapBar.ts` — the
  239 verdict bar + popover with greyed stats footer; base for the Score and Eval bars.
- `frontend/src/components/charts/ScoreChart.tsx` — rolling score chart with ordinal axis + inactivity
  breaks (`InactivityGapReferenceLines.tsx`); only caller is `pages/openings/StatsTab.tsx:237`.
- `EndgameScoreOverTimeChart` — `per_week_total_games` volume-bar pattern (tallest bar = bottom 20%).
- `app/services/eval_confidence.py:53` `compute_eval_confidence_bucket` — z-test; call sites need
  `eval − baseline` input.
- `EVAL_BASELINE_PAWNS_WHITE/BLACK` (`app/services/opening_insights_constants.py:85-86`).
- `app/repositories/query_utils.py` `apply_game_filters()` — the only filter implementation for the cutoff query.

### Established Patterns
- Insights confidence: `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P = 0.01`, `MEDIUM_MAX_P = 0.05`,
  `MIN_GAMES_PER_CANDIDATE = 20` (`opening_insights_constants.py`).
- `PositionResultsPanel` / `EvalConfidencePopover` / `EvalConfidenceTooltip` take
  `evalContext: 'opening-end' | 'endgame-entry'`; baseline centring must be scoped to `'opening-end'`.
- Sequential awaits on one `AsyncSession` (no gather) in `stats_service.get_most_played_openings`.

### Integration Points
- `frontend/src/pages/Openings.tsx` — `TAB_INFO` / tab triggers / `insightsTabEl` (lines ~69–710) lose the
  insights tab; mobile `OpeningsMobileBoardPanel` likewise.
- Endpoints: `/stats/most-played-openings`, `/stats/bookmark-phase-entry-metrics`, `/insights/openings`,
  `/openings/time-series` (needs weekly game counts).

</code_context>

<specifics>
## Specific Ideas

- Prod distribution for the cutoff (2026-10-17): median window of the last 200 games per colour is 433 d
  (50–199 games), 243 d (200–499), 129 d (500–999), 67 d (1000–1999), 68 d (2000–4999), 61 d (5000+);
  p10 15–36 d for 200+ game users. This is why D-01 adds the 60-day floor.
- Owner data references from SEED-204 (Queen's Gambit 280 games last played Oct 2023 → past; Caro-Kann
  Advance duplicate 172 games) are good UAT checks.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Reviewed todos from `todo.match-phase` were keyword-only
matches unrelated to this phase and were not folded.)

</deferred>

---

*Phase: 242-openings-stats-insights-rework*
*Context gathered: 2026-10-17*
