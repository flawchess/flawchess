---
sketch: 010
name: library-stats-you-vs-opponents
question: "How do the Library Stats you-vs-opponent sections (context tags, tactic motifs) become readable for non-statisticians, consistent with the Endgame percentile-first redesign but without percentiles?"
winner: "Round 5: tiles + opponents, zero-centred gap bars (gap only, rates in popovers), What stands out, three tactic tables by filter-panel group (Advanced collapsed), synced TC switch"
tags: [library, stats, flaws, tactics, bullet-charts, iqr, mobile, SEED-196]
---

# Sketch 010: Library Stats, You vs. Your Opponents

## Design Question
Below the Flaw Stats tiles and timeline, the Stats tab shows 15 context-tag bullets and 12+ tactic
bullets with red/green halves, a blue IQR band, CI whiskers and signed deltas where negative is good.
How do we carry over the Endgame redesign (sketch 009 / SEED-196: one horizontal bar, grey typical
band, dot coloured by band, stats in the popover) when there are no percentiles, only benchmark IQRs
of the you-minus-opponent gap?

Baseline screenshots (gitignored): `temp/library-stats/`.

## How to View
open .planning/sketches/010-library-stats-you-vs-opponents/index.html (round 2)
open .planning/sketches/010-library-stats-you-vs-opponents/round1.html (round 1, all variants)

## Round 2 (owner decisions 2026-10-12)
- **Tiles B**: only Blunders and Mistakes (inaccuracy tile removed), each with the opponent rate and a
  gap bar. Replaces the Severity card and its "Flaw rate" row.
- **Context tags A (gap bars)**: the middle tick is always 0 ("same as your opponents"); the grey band
  sits where the benchmark IQR is (may be off-centre). Linear inside the band, saturating outside so big
  gaps never clip. Better to the right. Combos (hasty miss, low-clock miss) removed: four cards,
  Clock (3) | Game phase (3), Opponent errors (2) | Lost advantages (2).
- **What stands out** card included: top 3 strengths / weaknesses by distance outside the band, then
  the typical tags in one line.
- **Tactics B (one table, split into three in round 3)**: Missed and Allowed side by side, all motifs, no accordion, per 100 games.
  Mini charts use the same circle dot + centred zero tick.
- **Info icons**: lucide Search to the right of the gap words ("1.7 fewer"), opening the
  RankedMetricPopover-style bubble (definition, you vs. opponents, typical gap, basis, grey stats footer).
- **Wording**: "flaws" / "blunders" / "mistakes" instead of "events".
- **Typical values print white**; only better/worse gaps are green/red. The dot stays blue for typical.
- **Card headers** (band + body) for all cards; Fredoka only for the h2 section titles.
- **Synced TC switch** in every section (blitz / rapid here), like the Endgame page.

## Round 3 (owner, 2026-10-12)
- Tactics split into three tables following the filter panel groups (`TACTIC_GROUPS`): Piece Attacks,
  Checkmate, Checks & Discoveries, Advanced; motifs in panel order, fixed column widths so the tables
  line up. Motifs with no flaws on either side are listed under the table, not as rows.
- Cells under 40 flaws (you + opponents) are faded and get no red/green verdict (1-vs-0 gaps are noise);
  the popover says "Too few flaws to call it".
- Search-icon popovers on every "What stands out" item.

## Round 4 (owner, 2026-10-12)
- No "you vs. opponents" rates on the page: context rows, "What stands out" items and tactic cells show
  only the gap (words + bar); both rates live in the search-icon popover. Tiles keep their
  "Opponents x.xx" line.
- Tactic tables: Motif | Missed | Allowed, each cell a full-size gap bar (same component as the cards).
  Phones stack Missed / Allowed under the motif.

## Round 5 (owner, 2026-10-12)
- The Advanced tactics card is collapsed by default: header + chevron + the endgame page's
  "Click or tap for details" hint (ShellyQuote `EXPAND_HINT` styling), hint hidden once open.

## Data
Real dev data per TC (owner account, blitz 1,000 / rapid 1,841 analyzed games, 2026-10-12).
Context-tag IQRs are the real benchmark zones from `/api/library/flaw-comparison` (identical for
blitz and rapid: the benchmark collapsed them to one global zone). **Tactic IQRs are made up**
(about ±40% of the average rate) until the benchmark pipeline computes them.

## Implied work
- Tactic-motif IQR zones (missed + allowed per family, per Elo × TC with the collapse check) in the
  `/benchmarks` skill, from the full-analysis benchmark sample (classical + rapid done, blitz ~half).
- TC switch vs. the sidebar time-control filter on this tab (same open question as SEED-196).
- Frontend: a gap-bar component sibling to `PercentileBar`, tile rework, table, popover; retire
  `MiniBulletChart` usage on this page and the combo rows.
