---
title: Phase-aware analytics ideas (post phase-classifier + transition evals)
date: 2026-05-03
context: Brainstorm during /gsd-explore. New data available per game_position: game_phase (opening/middlegame/endgame) + Stockfish evals at phase transitions. Adrian's concrete ideas are at the top (active focus); Claude's broader brainstorm is below (tabled for later).
---

# Phase-aware analytics ideas

## Active focus — Opening Success (Adrian, 2026-05-03)

Goal: extend the Openings → Stats subtab tables (bookmarked + most-played openings) with phase-transition signal so the player can see not just WDL but **how good the opening actually leaves them**.

New columns to add to those two tables:

1. **Eval column** — average Stockfish eval at middlegame entry for each opening, ± std.
2. **Eval significance** — one-sample t-test of eval vs 0; surface with a confidence indicator (high / medium / low) analogous to the opening insights cards.
3. **Avg clock diff at middlegame entry** — analogous to the existing "Avg clock diff" column in *Time Pressure at Endgame Entry*. Shows how much time the user wins/loses against their opponents when playing this opening.

Together these give a complete "how does this opening actually serve me" picture: WDL (already there) + position quality at handoff to middlegame + time advantage at handoff to middlegame.

## Tabled for later — broader phase-aware ideas

## Newly unlocked data
- `game_position.game_phase` ∈ {opening, middlegame, endgame} for every half-move
- Stockfish eval at each phase transition (opening→middlegame, middlegame→endgame)
- Existing: endgame eval at entry/exit already used for conv/recov; benchmarks; Endgame ELO

## Obvious extensions of existing analytics

1. **Middlegame ELO** — direct analogue to Endgame ELO. Eval at middlegame entry vs exit (= endgame entry) gives per-game middlegame skill score, bucketed by (platform, TC) over time.
2. **Opening ELO** — same trick using move-1 baseline (~0.0/+0.2) → eval at middlegame entry. Captures how well user navigates early non-book play.
3. **Per-phase WDL** decomposed by who-was-better-at-each-transition (e.g. WDL conditional on entering middlegame ahead).

## More interesting cross-cuts

4. **"Where do you bleed centipawns?" decomposition** — total game eval drift split into opening / middlegame / endgame contribution. Single per-user verdict like "you enter middlegame at +0.3 but exit at −0.6; middlegame is your leak." Most compelling self-review story.
5. **Opening → middlegame translation quality** — for every opening (or system-opening hash group), show average eval at middlegame entry. Surfaces openings that score well by WDL but leave you slightly worse, and vice versa. Connects the opening explorer to ground truth.
6. **Phase-conditional conversion / recovery** — extend existing conv/recov to all transitions: "you convert middlegame +1.0 advantages X% of the time", "you recover from −1.0 at middlegame entry Y% of the time". Currently endgame-only.
7. **Time-vs-phase correlation** — extend time-at-endgame-entry tracking to middlegame entry too. "You enter middlegame with 70% clock but only 25% by endgame entry — middlegame burn rate is the issue."
8. **Phase-flip games as a search dimension** — "show me games I won the opening but lost the middlegame" (sign flip across transition). Pure UX filter, very actionable for self-review.
9. **Opponent diff per phase** — opponent also has phase eval transitions. Per-phase eval-gain delta vs opponent at your ELO bucket → peer-benchmarked middlegame/endgame edge.
10. **LLM narrative upgrade** — endgame insights currently only see endgame data. Feeding full phase-by-phase eval trajectory enables narratives like "the opening is fine, the leak is middlegame planning." Bigger story per insight call.

## Probably not worth doing

- Per-phase blunder detection without per-move eval — only transitions are evaluated, can't localize a blunder, only attribute drift to a phase.
- Phase-length distributions on their own — interesting trivia, no clear action.

