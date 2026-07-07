---
id: SEED-086
status: dormant
planted: 2026-07-07
planted_during: /gsd-explore session shrinking Phase 157 (2026-07-07)
trigger_when: after Phase 157's FlawChess Agreement Verdict ships, if the game-review surface still wants a comparison anchored on the move the user *actually played* (not just FlawChess-vs-Stockfish)
scope: small–medium (one lookup + one prose line, or a badge; possibly one supplementary grade call)
source: the original Phase 157 REVIEW-02 "what you played vs what was practically best for you", dropped when the prose was reframed to FlawChess-vs-Stockfish agreement
depends_on: Phase 157 (FlawChess Agreement Verdict — reuses its prose + ProseMoveSpan surface)
---

# SEED-086: Played-move vs practical-best comparison (game review)

## What this is

The original, game-review-specific half of Phase 157's REVIEW-02: at each reviewed position of
a loaded game, show an explicit comparison between **the move the user actually played** and the
FlawChess Engine's top **practical** recommendation — including when they match ("you played the
practically best move"). This is distinct from what Phase 157 actually shipped, which narrates
**FlawChess vs Stockfish** agreement and is *not* anchored on the played move (and renders on free
analysis too).

## Why it was dropped from Phase 157

During the `/gsd-explore` session (2026-07-07) the prose direction was reframed: instead of
"your played move vs practical best", the FlawChess card verdict narrates whether the engine's
top practical move agrees or diverges from Stockfish's top objective move. That reframe:

- works on **both** free analysis and game review (shared `Analysis.tsx`), so it isn't
  game-review-specific;
- doesn't need the played move at all.

The played-move comparison is still potentially valuable **only** on the game-review surface —
that's the one place we know the move the user chose in a real game — so it's parked here rather
than deleted.

## Implementation sketch (from the explore session)

- The FlawChess search expands the root position's candidate children and grades each with a
  practical score. If the played move is among those expanded candidates, its practical score is
  **already computed** — just read it off.
- If the played move was pruned / never expanded (an off-book move the engine didn't rank), do
  **one supplementary grade call** on that single move to get its practical score, so the
  comparison works even for moves the engine didn't consider.
- Surface: reuse Phase 157's prose + `ProseMoveSpan` machinery (hover → board arrow + "practically
  X · objectively Y" popover, click → play). A game-review-only line like:
  *"You played **Nf3** (practically −0.4 for you); the FlawChess Engine would play **Bb5** (+0.2)."*
  Include the match case: *"You played **c4** — the FlawChess Engine's top practical move."*

## Open questions to resolve before planning

- Is this worth a distinct surface once the FlawChess-vs-Stockfish verdict (Phase 157) is live, or
  does the verdict already give the user enough? (Re-evaluate against the shipped verdict.)
- Cost of the supplementary grade call on off-book played moves — acceptable inline, or only when
  the played move is in the expanded set?
- Does it belong in the FlawChess card, or as an annotation near the played-move arrow / move list?
