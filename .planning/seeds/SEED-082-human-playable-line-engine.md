---
id: SEED-082
status: dormant
planted: 2026-07-04
planted_during: SEED-081 explore/spike session
trigger_when: after SEED-081 ships (needs the Maia inference infra); a later milestone
scope: large (a novel engine — its own milestone)
source: /gsd-explore session 2026-07-04 (user idea)
depends_on: SEED-081 (Maia-3 inference in the browser)
---

# SEED-082: Human-playable-line engine (Maia-filtered Stockfish)

A **novel engine** that produces the **best *human-playable* line**, not the best objective
line. Take Stockfish's candidate lines and re-weight/prune them by **Maia move-findability at
the relevant ELO**, so the surfaced line is one a real player at that level could actually find
and follow — not an engine-perfect PV full of only-moves nobody at 1400 would see.

This is the practical-play complement to SEED-081: SEED-081 *diagnoses* human play
(per-ELO move distributions, WDL, flaw verdicts); this engine *prescribes* it (the strongest
line you can realistically execute).

## The core idea

Score each line on **two axes and combine**:
- **Objective quality** — Stockfish eval of the line.
- **Human findability** — aggregate of Maia `P(move | ELO)` along the line.

Surface the line that is both strong *and* findable, instead of Stockfish's top PV.

## Two refinements that change what the engine *is* (locked in discussion)

1. **Asymmetric ELO — whose ELO filters whose moves.** The naive version filters only *your*
   moves by *your* ELO. The deeper version is asymmetric: **your moves weighted by your ELO's
   findability; the opponent's replies weighted by the opponent's *likely* play (Maia at their
   ELO)** — i.e. assume the opponent plays like a real human at their level, not a perfect
   engine. That turns "Stockfish PV minus your hard moves" into a genuine **practical best
   line** (closer to a Maia-weighted expectimax than PV filtering), and ties directly to the
   WDL practical-chances thesis. Requires knowing/estimating the opponent ELO (we have it).

2. **Rank/flag, don't hard-discard.** Sometimes the only good move *is* hard to find — that's a
   teaching moment, not noise. Score lines on (quality × findability) and surface the
   trade-off; never silently delete a line just because it contains a low-probability move.

## MVP vs ambitious (natural phasing)

- **MVP:** re-rank Stockfish's existing **multipv** lines by a Maia-findability score at the
  player's ELO. Cheap — reuses the multipv we already compute; adds a Maia scoring pass per
  candidate line. Answers "of the good moves here, which is most human-playable for me?"
- **Ambitious (the real novel engine):** a **Maia-guided search** — expand Stockfish candidates
  and prune/weight by Maia `P(move|ELO)` at each ply (asymmetric per side), producing a
  practical best line rather than re-ranking a fixed PV set. This is the harder, more original
  build.

## Open questions (for when this is planned)

- **Findability aggregation:** product of `P(move|ELO)` along the line (harsh — one hard move
  tanks it), min, geometric mean, or a discounted sum? Different choices = different behavior.
- **Quality×findability combination:** Pareto front + a tunable weight? A single scalar? How to
  present the trade-off to the user.
- **Depth/branching cost** of the ambitious search vs the browser-latency budget (SEED-081 is
  client-side; this may need server compute — revisit the inference-location decision).
- **Prior art check:** Maia+Stockfish hybrids, "human-aware analysis", the Chessformer-in-lc0
  build the model card mentions for strength — survey before building.

## When to Surface

**Trigger:** a later milestone, **after SEED-081 ships** (this reuses its Maia inference layer;
building it before Maia exists is out of order). Not the next milestone.

## Breadcrumbs

- Depends on SEED-081 (`.planning/seeds/SEED-081-*`) — Maia-3 inference + per-ELO move
  distributions; spikes 004–006 established client-side Maia feasibility.
- Existing Stockfish multipv / PV infra (`app/services/engine.py`, `game_positions.pv`) is the
  MVP substrate for line re-ranking.
- Related: SEED-081 (diagnose ↔ this prescribes), SEED-066 (live engine analysis page).

## Notes

Captured 2026-07-04 from the SEED-081 explore session; user flagged it as "probably a later
milestone." The asymmetric-ELO and rank-don't-discard refinements were added in discussion.
