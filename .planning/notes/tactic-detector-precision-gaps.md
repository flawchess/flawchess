---
title: Tactic detector — precision & validation gaps (post-implementation)
date: 2026-06-19
context: /gsd-explore session after Phase 126 UAT — tactic tags "make no sense"
status: problem record, feeds Phase 127
---

# Tactic detector — precision & validation gaps

Captured during a `/gsd-explore` session (2026-06-19). Trigger: spot-checking fork/pin
tags on flaw cards, the user could not find a fork or pin in the position. Investigation
of `app/services/tactic_detector.py` surfaced two real, structural problems plus a license
boundary. This note feeds **Phase 127 (detector hardening & validation)**.

## Problem 1 — the tactic is in the PV, not the displayed position (UX) AND the detector scans too deep (precision)

The detector does **not** inspect the played move's static position. It takes the position
*after* the flawed move and replays the engine's principal variation (up to
`PV_CAP_PLIES = 12`, `engine.py:99`), looking for the motif **anywhere in that line**.

So "the fork is 4 plies deep" is by design — but the implementation goes further and scans
the *entire* line for *any* occurrence:

- `detect_fork` (`tactic_detector.py:255`): `for i in range(0, len(moves), 2)` — flags a
  fork on **any** pov move across all 12 plies, not just the first 1–2.
- `detect_pin` (`tactic_detector.py:316`): `for board in boards:` then any pinned opponent
  piece in **any** of the 13 positions. The code comment is explicit:
  *"Simplified: pin exists and the pinner is a ray piece — that's enough."*

Consequence: an incidental pin/fork deep in a non-forcing continuation gets attributed to
the flaw, even when it is not the point of the refutation and not why the move was a
blunder. This is the most likely root cause of "the tags make no sense." The detectors lack
any check that the motif is *the* refutation (occurs early / is forcing / wins material
relative to the line).

**Depth as both feature and fix:** every detector already knows the ply at which the motif
fires (the loop index). Storing it (`tactic_depth`) lets a difficulty slider filter out the
deep incidental hits, and confidence can decay with depth. Depth storage is therefore a
mitigation for Problem 1, not only a feature. See [[missed-vs-allowed-tactic-design]].

## Problem 2 — the precision gate is circular (self-labeled fixtures)

`tests/services/test_tactic_detector.py` docstring claims fixtures were *"bucketed by the
detector and CONFIRMED BY HUMAN INSPECTION."* The first half is the problem: **the fixtures
were labeled by the detector itself**, then the test asserts the detector reproduces its
own labels. The 0.90/0.95 precision bars are largely vacuous — no independent ground truth.
The user confirms no human ever inspected them. **Recall is never measured at all.**

## Fix direction — validate against lichess CC0 puzzles (NOT cook.py)

- **`cook.py`** (`tagger/cook.py`, lichess-puzzler) is **AGPL-3.0**. FlawChess is **MIT**
  (`LICENSE`). Copying or porting cook.py code would be a license violation (AGPL viral
  copyleft, incompatible with MIT distribution). Phase 124 deliberately reimplemented from
  plain-English pseudocode and copied no source — keep it that way. **Do not vendor cook.py.**
- The **lichess puzzle database** (database.lichess.org/#puzzles) is **CC0 / public domain**:
  `PuzzleId, FEN, Moves, Rating, …, Themes, …` where `Themes` includes `fork`, `pin`,
  `skewer`, `discoveredAttack`, `backRankMate`, etc. The labels were *generated* by cook.py,
  but the published *dataset* is CC0 — using the data is not using the AGPL code. This is
  independent ground truth.
- Validation plan: map our 24 motifs to lichess theme names, sample N puzzles per motif, run
  `detect_tactic_motif(FEN, Moves)`, measure **precision AND recall** against the theme labels.
  - A puzzle is "side-to-move has the tactic" — the **missed** orientation — so it validates
    the core geometric detectors head-on.
  - Lichess themes are **multi-label**; some tier-3 motifs (`capturing-defender`,
    `self-interference`) have **no lichess equivalent** and stay unvalidated (be explicit
    about coverage, same as today's query-suppressed set).
  - Bonus: lichess puzzles ship a human-calibrated `Rating` — cross-check that our
    `tactic_depth` correlates with puzzle difficulty (sanity check on depth-as-difficulty).

## Key code references

- `app/services/tactic_detector.py` — `detect_fork:243`, `detect_pin:308`,
  `detect_tactic_motif:1227` (dispatcher, `pov = board_after_flaw.turn`).
- `app/services/engine.py:99` — `PV_CAP_PLIES = 12`.
- `tests/services/test_tactic_detector.py` — self-labeled fixtures + precision bars.
- `app/repositories/query_utils.py:23` — `is_opponent_expr` (perspective derivation).
