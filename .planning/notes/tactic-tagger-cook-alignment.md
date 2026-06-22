# Tactic-tagger cook.py alignment spec (Tier 1 + Tier 2)

**Date:** 2026-06-22
**Context:** Workstream-A spec for SEED-064 (tactic precision hardening). Per-motif
diagnosis of where `app/services/tactic_detector.py` diverges from lichess-puzzler's
`tagger/cook.py` — the AGPL tagger that generated every theme label on our CC0 fixture.
Closing the divergence is the precision ceiling (the labels *are* cook's output).

> **AGPL boundary.** cook.py is AGPL-3.0. This note describes its *heuristics* as original
> pseudocode (ideas aren't copyrightable); it copies **no** source. Reimplement from this
> prose, never paste cook.py bodies. Reference clone: `/home/aimfeld/Projects/Python/lichess-puzzler`.

---

## Index convention (cook ↔ ours) — read this first

cook iterates `puzzle.mainline`, where **`mainline[0]` is the opponent's setup/blunder move**
and pov's moves are the **odd** indices `mainline[1::2]`. Our detector receives the refutation
PV where **`moves[0]` is pov's first move** and pov moves are the **even** indices.

| cook expression | meaning | our equivalent |
|---|---|---|
| `mainline[1::2]` | all pov moves | `moves[0], moves[2], …` (even `k`) |
| `mainline[1::2][1:]` | pov moves from the 2nd | `moves[2], moves[4], …` (`range(2, len, 2)`) |
| `mainline[1::2][:-1]` | pov moves except the last | even `k` excluding the final pov move |
| `node.parent` ("prev") | opponent move just before this pov move | `moves[k-1]` |
| `node.parent.parent` ("grandpa" / prev pov node) | the earlier pov move | `moves[k-2]` |
| `node.board()` | board **after** the pov move | `boards[k+1]` |
| `node.parent.board()` | board **before** the pov move | `boards[k]` |

Note: cook's first pov move (`mainline[1]`) has a preceding opponent move (`mainline[0]`); our
`moves[0]` does not. Every relational detector below uses `[1:]` (skips the first pov move), so
our `range(2, len, 2)` is the correct mirror — no missing-context bug there.

---

## Shared utilities — two divergences that leak across many motifs

cook's helpers are stricter than ours. Aligning these alone moves multiple motifs:

1. **`is_defended` is ray-aware; our `_is_hanging` is not.** cook treats a piece as defended if
   it has a normal defender **or** an X-ray (ray) defender sitting behind a friendly ray piece
   (it removes the front ray attacker and re-checks defenders). Our `_is_hanging`
   (`tactic_detector.py:256`) only checks `attackers(color)` non-empty. So we call pieces
   "hanging" that cook considers ray-defended → false positives in fork/hanging/pin/skewer/
   interference (all consume `is_hanging`). **Port the ray-aware `is_defended`.**

2. **`is_in_bad_spot` — the gate fork/skewer rely on, which we lack entirely.**
   `is_in_bad_spot(square)` = the piece is attacked by the opponent **and** (it is hanging
   **or** it can be captured by a lower-valued non-king piece). This is the "is this piece
   actually loose" test. cook uses it as a **prune** in fork (skip the move if the *forker*
   lands in a bad spot) and as an **accept** in skewer. We have no equivalent.

Also note cook uses **`king_values`** (`{P1,N3,B3,R5,Q9,K99}`) for fork/skewer value comparisons,
so attacking the enemy **king** counts as a high-value target (a forking check). Our
`_piece_value` has no king entry.

---

## Per-motif spec (priority by prod-volume × precision gap)

### skewer  — P(test) 0.15 → target >0.9 or suppress
cook (`mainline[1::2][1:]`): for a pov move that **captures** with a **ray piece** (Q/R/B) and is
**not** checkmate:
- let `between = squares_between(from, to)` of the capturing move;
- let `op = ` the opponent's immediately-prior move (`moves[k-1]`);
- **require** `op.to != capture_square` **and** `op.from ∈ between` (the opponent's piece moved
  *across the skewer line*, from a square between the capturer and the capture square);
- **require** `king_values[piece the opponent just moved] > king_values[captured piece]` (a more
  valuable piece was in front) **and** `is_in_bad_spot(board_before_capture, capture_square)`.

**Our divergence:** detector is badly broken (0.15). Rebuild to this exact relational predicate;
it hinges on `is_in_bad_spot` (missing) and the `op.from ∈ between` geometry.

### discovered-attack  — P(test) 0.17 → target >0.9 or suppress
cook: **True if `discovered_check`** (see below); else for a pov **capture** (`[1:]`):
- `between = squares_between(from, to)`;
- if the opponent's prior move went to **this capture square** → **False** (it's a recapture);
- let `prev = moves[k-2]` (the earlier pov move); **require** `prev.from ∈ between` **and**
  `to != prev.to` **and** `from != prev.to` **and** `prev` is not castling.
- i.e. an *earlier pov move* vacated a square on the current capture's line, unmasking the attack.

**Our divergence:** over-fires. Re-implement the "earlier pov move vacated a `between` square"
test and the recapture short-circuit. Preserve the discovered-check-wins-first split (D-03).

### discovered-check  — P(test) 0.83 → hold ≥0.85 (don't regress)
cook (`mainline[1::2]`): the post-move board has checkers **and the moved piece's destination is
not among the checkers** (something *other* than the moved piece gives check → discovered).
Clean and already strong; just don't break it while tightening discovered-attack.

### back-rank-mate  — P(test) 0.27 → target >0.9
cook (final position only): board `is_checkmate` and the defender king is on its back rank, then:
- build the king's three **forward** squares (one straight toward the board + the two forward
  diagonals, clipped at the a/h files);
- for each such square, if it is **empty**, or holds a **pov** piece, or is **attacked by pov** →
  **return False** (those must all be the defender's *own* blockers — the king is boxed by its own
  pieces, not merely confined by attack);
- finally **require at least one checker on the back rank**.

**Our divergence:** over-fires on corner mates (0.27). Port the own-blocker test + back-rank-checker
requirement verbatim-in-logic.

### fork  — P(test) 0.40 → target >0.9 or suppress
cook (`mainline[1::2][:-1]`, i.e. every pov move **except the last**): if the moved piece is **not a
king**:
- **prune:** if `is_in_bad_spot(board_after, to)` → skip (the forker itself is loose);
- count victims among `attacked_opponent_squares(to)`, **skipping pawns**, where the victim is either
  `king_values[victim] > king_values[forker]` (higher value, king counts) **or**
  (`is_hanging(victim)` **and** the victim's square is **not** itself an attacker of the fork square —
  i.e. the "hanging" victim isn't just defending the forker);
- fire if `count > 1`.

**Our divergence (`tactic_detector.py:295-346`):** four gaps — (1) no `is_in_bad_spot` forker-safety
prune; (2) we don't skip pawn victims; (3) we use `_piece_value` (no king=99) instead of `king_values`;
(4) we omit the hanging victim's "not an attacker of the fork square" clause; (5) we scan the last pov
move too. Recall is already 0.78, so this is purely a precision tightening.

### pin  — P(test) 0.44 → target >0.9 or suppress
cook fires pin if **either** sub-test holds (`mainline[1::2]`):
- **pin_prevents_attack:** some opponent piece is pinned (`board.pin(color, sq) != BB_ALL`) and it
  *attacks* a pov piece on a square **outside** the pin direction, where that pov piece is worth more
  than the pinned piece **or** is hanging. (The pin stops the pinned piece from making that capture.)
- **pin_prevents_escape:** some opponent piece is pinned and a pov attacker **inside the pin line**
  attacks it, where either the pinned piece is worth more than the attacker, **or** the pinned piece is
  hanging and cannot legally step off the pin line to safety.

**Our divergence:** SEED-057 lifted pin 0.41→0.44 (parity + reject-before-accept ordering). The
remaining gap needs the full two-sub-test port above (pin-direction membership via `board.pin`, the
outside-vs-inside-line distinction).

### anastasia-mate  — P(test) 0.86 → target >0.9
cook (final position): defender king on the **a- or h-file** but not a corner; the mating move is a
**queen or rook** on the king's file; normalize by flipping to the h-file; require an **opponent
blocker** on `king+1` and a **pov knight** on `king+3`. Port the file-normalization + blocker/knight
geometry exactly; small lift.

### hook-mate  — P(test) 0.84 → target >0.9
cook (final position): the mating move is a **rook adjacent to the king**, that rook is defended by a
**pov knight adjacent to the king**, and that knight is defended by a **pov pawn** (the classic hook
chain rook←knight←pawn). Port the defender chain; small lift.

### Already at/above bar — lock against regression, no detector work
`mate` (1.00), `smothered-mate` (1.00), `double-check` (1.00). cook's `double_check` = any pov move
producing ≥2 checkers. Keep their floors as the never-regress gate while editing neighbors.

---

## cook's dispatch is multi-label (why our recall is dispatch-capped)

`cook()` appends **every** matching tag (mate subtypes are an `elif` chain; geometric/fuzzy tags are
independent `if`s). So a single puzzle legitimately carries fork **and** pin **and** mate. Our detector
emits one motif by tiered min-depth dispatch — correct for the product (one missed + one allowed tactic
per flaw), but it means per-motif recall is structurally capped and is **not** the optimization target.
Precision is. (See SEED-064.)

## Not covered here (out of SEED-064 scope)
Tier-3 (deflection, attraction, intermezzo, x-ray, interference, clearance, capturing-defender,
sacrifice) — cook's logic for these is in `cook.py` lines 184-820 and is sequence-relational like
skewer/discovered-attack; defer to a later phase. hanging-piece's product false alarm is the
missed-vs-played call-site bug (SEED-064 Workstream B), not a cook predicate gap — its puzzle
precision is already 0.95.
