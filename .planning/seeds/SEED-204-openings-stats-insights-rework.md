---
id: SEED-204
status: dormant
planted: 2026-10-17
planted_during: sketch 012 (opening-stats-repertoire), after the 238/239 Endgame and Library Stats reworks
trigger_when: owner opens the next Openings milestone or asks to implement sketch 012
scope: large; ONE phase with several plans (owner decision 2026-10-17): a backend wave first, then the frontend rework
---

# SEED-204: Openings Stats + Insights rework (implement sketch 012)

## Goal

Rework the Openings Stats and Insights tabs the way phases 238/239 reworked the Endgame and Library Stats
pages: simpler, more readable, no loss of information. The design is settled in
`.planning/sketches/012-opening-stats-repertoire/` (open `index.html`; README "Round 2" lists every
decision, MANIFEST "012 →" summarises the winner). The 238/239 system decisions apply unchanged: one
verdict bar per metric with a grey typical band and a red/blue/green dot, uncoloured values, words for
gaps, Search-icon popover with a greyed stats footer, red/green only at 99% (D-14), symmetric bands
(D-15), significance-only verdict without a band (D-16), "show less rather than noise" (D-17).

## Locked decisions (owner, 2026-10-17)

- **Insights merge into the Stats tab.** The Insights subtab (desktop and `OpeningsMobileBoardPanel`)
  goes away. "Moves that cost you" / "Moves that work" sit above the repertoire table, per colour.
- **One sticky White | Black switch** for the merged page; the table header sticks under it. Sticky on
  scroll only, not persisted.
- **Findings gate stays at 99%** (backend confidence "high", p < 0.01), like 238/239. Top 5 per section;
  the rest in a collapsed "Not clear yet (n)" list, faded, no colour. Empty sections get the empty state
  ("Nothing clear yet as Black. 3 moves lean this way…"). Owner data has no "cost you" finding at 99%;
  that is accepted.
- **Finding cards** lead with the move ("After 2...e6"), opening name (no ECO) + full line as subtitle,
  board with arrow, "You score X%" (with a score popover) + WDL bar, Eval after opening bar, a one-line
  "why" that reads only the eval (hidden when unremarkable). No "your move / their move" badges.
- **Repertoire table** replaces the 4 bookmark / most-played sections: bookmarks pinned, then most played,
  one table per colour. Columns: Opening (44px board, name without ECO, move line) · Games (count + last
  played) · Results (WDL bar) · Score (compact "56%" + verdict dot + popover) · Eval after opening (compact
  signed value "+0.9" + verdict dot + popover). No Trend column, no score bullet, no left spines, no coloured fonts, no CI whiskers. Rows
  under 20 games are faded and never coloured.
- **Duplicate rows collapse:** same colour + position (bookmark wins), and most-played rows with
  identical W/D/L and eval under two names (keep the deeper line). Owner data: "Caro-Kann: Advance,
  Botvinnik-Carls" and "vs. Caro-Kann: Advance" were the same 172 games.
- **Expanded row:** 200px board, Moves / Games / Bookmark links, Score bar (band 45–55%, today's
  `SCORE_BULLET_NEUTRAL_*`), Eval after opening bar, and the per-opening Score over Time chart.
- **Score over Time = reuse `ScoreChart`** (ordinal axis that cuts out inactivity, palm-tree break
  markers over 90 days), one opening per chart, plus **grey weekly bars of games in that opening** (tallest
  bar = bottom 20%, as `EndgameScoreOverTimeChart` does with `per_week_total_games`). The volume series is
  optional and shown only when the chart holds a single opening.
- **The multi-line bookmark Score over Time chart is dropped** (replaced by the per-row charts).
- **Eval is centred on the colour baseline** (+0.25 White, −0.25 Black, `EVAL_BASELINE_PAWNS_*`): bar
  centre, ±0.30 band, verdict dot and the z-test all use `eval − baseline`; a faint tick marks 0 (equal);
  labels keep the raw eval. Rationale: benchmark §2.1 measured the ±0.30 IQR on baseline-centred data,
  and the zero anchor turns colour into a verdict (owner data: 5 of 25 repertoire verdicts change, all
  colour-driven). This reverses the "H0 = 0 cp, baseline is only a tick" note in
  `opening_insights_constants.py` and `stats_service.py`.
  **Scope: the Openings tab only (Moves, Games, Stats).** The Endgames page shows the endgame-entry eval
  (`PositionResultsPanel` with `evalContext="endgame-entry"`) and must not change; the shared panel needs
  the centring scoped to the middlegame-entry context.
- **Current vs past repertoire:** "current" = last played within the user's last 200 games with that
  colour (activity-relative, not a calendar window). Non-current most-played rows move to a collapsed
  "Played before (n)" group at the bottom; stale bookmarks stay pinned with a "not played recently" chip;
  findings from older games get an "older games" chip and sort after current ones. Owner data: 6 of 9
  White most-played rows are past (Queen's Gambit, 280 games, last played Oct 2023).
- **Popover footers** carry the 99% CI, the p-value with its reference ("vs 50%", "vs +0.25") and n.
  Findings show the backend Wilson p.
- **No ECO codes, no "pawns" unit** anywhere on the page.
- **Dropped:** "After the opening" (score minus the eval-predicted score). Never significant, too many
  assumptions. Its expected-score refit moved to the Endgames page (SEED-203).

## Implied work

**Backend (first wave)**
- Eval z-test against the colour baseline for opening stats, bookmarks and insights:
  `compute_eval_confidence_bucket` call sites in `stats_service.py` (most-played, bookmark phase-entry
  metrics), `opening_insights_service.py`, `openings_service.py` (Moves tab). Leave `endgame_service.py`
  alone (endgame context). Update the constant comments that document "H0 = 0 cp".
- Dedupe most-played rows (identical game sets under two names) and drop most-played rows that duplicate
  a bookmark of the same colour + position.
- Current/past cutoff: the user's 200th most recent game date per colour under the active filters.
- Weekly game counts per time-series (for the volume bars); `last_played_at` already exists on
  most-played rows, bookmarks, findings and the time series.
- Possibly raise `TOP_OPENINGS_LIMIT` (10) now that past openings collapse (discuss).

**Frontend**
- Merge Insights into Stats; remove the Insights subtab, its mobile tab and route; redirect
  `/openings/insights` and any deep links (`useDeepLinkHighlight`, `useTabReset`, `useOpeningsHandlers`)
  to Stats.
- New repertoire table + expanded row, replacing `OpeningStatsSection` / `OpeningStatsCard` on this
  page; finding cards replacing `OpeningFindingCard` / `OpeningInsightsBlock`.
- Verdict bars via the 238/239 components (sketch 012 bars follow sketch 010); baseline-centred eval bar
  with a faint zero tick.
- `ScoreChart`: optional weekly volume series; keep the multi-bookmark mode wherever else it is used, or
  retire it if this page was the only caller.
- Phone layout: rows stack (name left; Score above Eval top right, each with dot + popover; WDL bar
  with "N games · last played" full width below).
- Testids and Umami events for the new controls (frontend/CLAUDE.md).

## Open for discuss-phase

- Validate the 200-game cutoff against the prod distribution of games per user and colour (a user with
  few games should not see everything as "past"; one with many should not see last month as "past").
- How many most-played rows to fetch per colour once past openings collapse.
- Phone: show 2 finding cards per section with "show more" (four cards push the table far down).
- Whether the "Not clear yet" list needs a cap.
- Score band check: benchmark §2 pooled IQR is [46.1%, 57.3%]; the shared ±5% band stays (benchmark says
  keep).

## References

- Sketch: `.planning/sketches/012-opening-stats-repertoire/` (index.html, README.md, data.js).
- System decisions: `.planning/milestones/v2.25-phases/238-*/238-CONTEXT.md`, `239-*/239-CONTEXT.md`
  (D-00..D-17); sketches 009 / 010.
- Benchmark: `reports/benchmark/benchmarks-latest.md` §2.1 (MG-entry eval baseline +25.21 cp, centred IQR
  [−23, +34] cp → ±0.30).
- Related: SEED-203 (Endgames expected-score refit).
