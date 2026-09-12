# Phase 221: Tactic-Tagger Real-Game Precision — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-12
**Phase:** 221-tactic-tagger-real-game-precision-winning-floor-predicate-tightening-port-fixes-seed-165
**Areas discussed:** Winning floor, Sacrifice & clearance, Missed parity, Real-game gate & rollout

---

## Winning floor

| Option | Description | Selected |
|--------|-------------|----------|
| Per-tier: +200 tier-3/move-type, 0 tier-1/2 | lichess-puzzler advantage floor for sequence motifs; geometric motifs only "not losing" | ✓ |
| One floor +200 for every motif | simplest, costs ~3% of tier-2 tags | |
| One floor 0 for every motif | removes only clearly losing lines | |

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to game_positions evals when blob missing | allowed: eval after flaw; missed: eval before flaw | ✓ |
| Skip the floor, keep the tag | today's no-blob posture | |
| Suppress the tag | strictest | |

| Option | Description | Selected |
|--------|-------------|----------|
| Firing node only | matches "solver winning where the tactic lands" | ✓ |
| Firing node and node 0 | stricter, kills deep-converting sacs | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Mate for the solver before the flaw = already winning, reject | mate motifs exempt | ✓ |
| Only reject when mate-in-≤3 | softer | |
| You decide | | |

**User's choice:** all recommended options.

---

## Sacrifice & clearance

| Option | Description | Selected |
|--------|-------------|----------|
| Deficit still ≥2 after the next pov move, or line ends | drops zwischenzug shape | ✓ |
| Deficit at line end | stricter | |
| No persistence rule | cook fidelity | |

| Option | Description | Selected |
|--------|-------------|----------|
| Cap at 4 for sacrifice and clearance | other tier-3 keep full scan | ✓ |
| Cap at 4 for all tier-3 | | |
| No depth cap | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Strengthen, keep only if real-game precision ≥ 0.8 | no king/pawn vacating, line used, cap, floor | ✓ |
| Suppress now | | |
| Keep cook's predicate | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Same rules both orientations | | ✓ |
| Missed: floor only | | |

---

## Missed parity

| Option | Description | Selected |
|--------|-------------|----------|
| Apply cook's recapture exclusion on missed hanging-piece | parity with allowed pass | ✓ |
| Keep recaptures as hanging-piece | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Fix discovered-attack depth to k, accept dispatch/UI shift | | ✓ |
| Fix depth but keep DA ahead of fork/skewer at equal k | | |
| Leave k−1 | | |

---

## Real-game gate & rollout

| Option | Description | Selected |
|--------|-------------|----------|
| Claude labels all, user spot-checks ~20; CI-gated per-motif floor | | ✓ |
| Claude labels, report-only | | |
| User labels all 150 | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Prod, stratified by motif × orientation, before the fixes | | ✓ |
| Dev DB only | | |

**Clarification asked by the user:** does the retag run on the prod server or through the
tunnel? Answer: from the local box through `bin/prod_db_tunnel.sh` (`--db prod` →
`localhost:15432`); Phase 220 wrote through the same path. The Phase 143/145 "tunnel is
read-only" note is stale (only the MCP role is read-only).

| Option | Description | Selected |
|--------|-------------|----------|
| Retag right after deploy, same phase; full refresh clears int-14 rows | | ✓ |
| Deploy now, retag later | | |

| Option | Description | Selected |
|--------|-------------|----------|
| One release, one retag | | ✓ |
| Two releases, two retags | | |

## Claude's Discretion

Placement of the tier→floor map and eval-reading helper; the clearance "line is used"
helper; sampling mechanics for the real-game set; re-measured floor values.

## Deferred Ideas

"Missed recapture" as its own signal; multi-label storage; discovered-check label source;
per-motif floors beyond the tier split.
