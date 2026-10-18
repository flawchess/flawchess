---
sketch: 012
name: opening-stats-repertoire
question: "How do the Openings Stats and Insights tabs become readable, consistent with the Endgame (009) and Library (010) redesigns?"
winner: "Stats A + Insights A, merged into one Stats tab; After the opening dropped (round 2)"
tags: [openings, stats, insights, repertoire, gap-bars, mobile]
---

# Sketch 012: Opening Stats Repertoire

## Design Question
The Openings Stats and Insights tabs repeat one card (board + WDL bar + score bullet + eval bullet)
across 8 colour-split sections. The score bullet repeats the WDL bar, three gates (spine, font colour,
dimming) disagree, and "score vs 50%" mixes opening quality with everything played afterwards. How do
we carry over the 009/010 system (one verdict bar, grey typical band, words, Search popover, 99% gate)?

Baseline screenshots: taken live on dev 2026-10-17 (not saved).

## How to View
open .planning/sketches/012-opening-stats-repertoire/index.html
(sticky White | Black switch; 99% / 95% gate toggle; Phone/Tablet/Desktop bottom-right).
Round 1 (A/B variants, separate Insights tab) is kept at `temp/opening-redesign/index.round1.html`.

## Decisions going in (owner, 2026-10-17)
- Split each opening's result into **Eval after opening** (avg eval at middlegame entry) and
  **After the opening** (actual score minus the score that eval predicts).
- Stats tab becomes a **table**, not board cards.
- **Bookmarks and most-played merge** into one list per colour (bookmarks pinned).
- **No TC switch** on Openings (thin per-opening samples); sidebar filters stay.

## Variants
Round 1:
- **Stats A: Board thumbnails** (44px board per row). ★ picked
- **Stats B: Compact** (board only in the expanded row).
- **Insights A: Cards** (move-led cards, 2-column grid, "why" line). ★ picked
- **Insights B: List** (the same findings as rows in one card).

Round 2 (owner feedback, 2026-10-17):
- **Insights merged into the Stats tab**, above the repertoire table; the Insights subtab is gone.
- **One White | Black switch, sticky on scroll** (not persisted), driving both sections; the table header
  sticks under it.
- **No ECO codes.**
- **No "your move" / "their move" badges** on the finding cards.
- **Current vs past repertoire:** "Current" = last played within the user's last 200 games with that
  colour (activity-relative, not a calendar window). The Games cell shows last played ("11 days ago",
  "Oct 2023"); non-current most-played rows move to a collapsed "Played before (n)" group; stale bookmarks
  stay pinned with a "not played recently" chip. The expanded row's "Score over time" chart mirrors the existing
  ScoreChart (rolling 50-game score, ordinal axis that cuts out inactivity, palm-tree marker with the
  break length for gaps over 90 days) plus grey weekly bars of games in that opening (tallest bar = bottom
  20%, as in EndgameScoreOverTimeChart); the build reuses ScoreChart with an optional volume series,
  shown only when the chart holds a single opening. Findings from older games get an "older games" chip and sort
  after current ones. Owner data: 6 of 9 White most-played rows are past (Queen's Gambit, 280 games, last played
  Oct 2023).
- **Score column:** the score moves out of the Results cell into its own column, compact like the eval
  (verdict dot + "56%" + popover). On phone, Score and Eval stack top right next to the opening name;
  the WDL bar runs full width below with "N games · last played".
- **Phone expanded row:** the Moves / Games / Bookmark links stack to the right of the board.
- **Lighter table:** the eval column is a compact "+0.9" with a verdict dot (full bar only in the
  expanded row); the Trend sparkline column is gone (score-over-time chart stays in the expanded row).
  On phone the eval sits top right, next to the opening name.
- **Eval centred on the colour baseline** (+0.25 White, −0.25 Black): the bar's centre tick (with a
  white/black swatch) is the average game for that colour, the ±0.30 band sits around it, and the verdict
  dot and 99% test use `eval − baseline`. A faint dashed tick marks 0 (equal). Labels keep the raw eval.
  Rationale: benchmark §2.1 measured the ±0.30 IQR on baseline-centred data, and anchoring on 0 turns
  colour into a verdict (owner data: 5 of 25 repertoire verdicts change, all colour-driven). Reverses
  the "H0 = 0 cp, baseline is only a tick" choice in `opening_insights_constants.py` / `stats_service.py`.
- **p-values in the popover footers** (greyed stats line): score vs 50% (findings use the backend Wilson
  p), eval vs the colour baseline, next to the 99% CI and n. Finding cards' score gets the same popover.
- **Score bar in the expanded row**, above "Eval after opening": the same verdict bar, centred on 50%, grey band
  45–55% (today's score-bullet neutral zone), 99% gate.
- **No "pawns" unit:** the eval shows as a signed number (+0.9 / −0.4).
- **"After the opening" dropped** (owner, 2026-10-17). It was never significant at 99% on the owner's
  games, needed an Elo × TC refit of the eval → score curve plus a made-up typical band, and added a
  column against the goal of simplifying. "Actual vs expected" means more at endgame entry, closer to the
  end of the game, so the refit moved to **SEED-203** (Endgames "Do you keep your entry advantage?" card).
  Rows now show the result (WDL + score) and one verdict bar, Eval after opening. The finding cards' "why"
  line reads only the opening eval and is hidden when it has nothing to say.

## What to Look For
- Does "Eval after opening" read without explanation next to the score?
- Insights at 99% has no "cost you" findings for the owner: acceptable, or gate findings differently
  (e.g. by the eval, which carries far more information per game)?
- Phone: four "Moves that work" cards push the table down; show two with "show more"?

## Data
Real dev data (owner account, human opponents, all TCs, 2026-10-17) from `/stats/most-played-openings`,
`/insights/openings`, `/openings/time-series`, `/stats/bookmark-phase-entry-metrics`. Weekly series and
the current/past cutoff from the dev DB (`temp/opening-redesign/monthly.py week`). Derived in `temp/opening-redesign/build_data.py`:
- The ±0.30 eval band is benchmark §3.
- Round 2 explored an "After the opening" gap with an Elo × TC refit of the expected-score curve
  (`temp/opening-redesign/fit_kd.py`, `kd_table.json`); dropped, see SEED-203 for the numbers.
- 99% CIs: eval from the reported 95% CI.

## Implied work
- Frontend: merge the Insights tab into Stats (one sticky colour switch, findings above the repertoire
  table), repertoire table with WDL + score and a compact eval cell; expanded row with Score bar, Eval after opening bar and score-over-time chart; drop ECO
  codes and the score bullet.
- Backend: the user's 200th-most-recent game date per colour (current/past cutoff), and games per week
  per series for the volume bars; `last_played_at` and the time series already exist.
- Backend: eval z-test against the colour baseline (`mean − EVAL_BASELINE_PAWNS_*`) for opening stats
  and insights.
- Backend: dedupe identical game sets in most-played (same W/D/L and eval under two names; keep the
  deeper line, bookmarks win), 99% gate for findings, eval 99% CI per row.
