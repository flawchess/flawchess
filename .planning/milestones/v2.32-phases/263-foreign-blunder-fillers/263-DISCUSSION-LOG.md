# Phase 263: Similarly Rated Players' Blunders Replace the Lichess Fillers - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-23
**Phase:** 263-Similarly Rated Players' Blunders Replace the Lichess Fillers
**Areas discussed:** Seed refinement (before the phase was added), Deleted source game, What the solver is told, Which blunders get picked, Points / streak / Activity / reveal

---

## Seed refinement (chat, before /gsd-discuss-phase)

| Question | Options considered | Selected |
|---|---|---|
| Old lichess filler solves | Delete the rows in a migration (seed decision of 2026-11-20) / keep them as inert history | Keep, after a code check showed the remaining cost is light |
| Warm-up concept | Reword the warm-up copy / retire the concept | Retire entirely |

**User's choice:** "if the filler history doesn't leave us with old baggage that's heavy to carry, we can just leave it instead of deleting. I think we can retire the warm-up concept entirely"
**Notes:** Keeping the rows removes every side-effect question (session counts, points totals, frozen standings, streaks).

---

## Deleted source game

| Option | Description | Selected |
|--------|-------------|----------|
| Drop it | Live join; an unsolved puzzle whose game vanished is skipped, session completes one shorter | ✓ |
| Keep it via snapshot | Store FEN and answer key at composition (pool table or columns) | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep outcome only | Solved row keeps points, guess and move quality; position not re-openable | ✓ |
| Must stay reviewable | Forces the snapshot option | |

**User's choice:** Drop it; keep outcome only.

---

## What the solver is told

| Option | Description | Selected |
|--------|-------------|----------|
| Reveal line, every one | One neutral line after solving on each foreign puzzle | ✓ |
| Reveal line, first only | Only on the first foreign puzzle of a session | |
| Start screen only | No per-puzzle line | |
| Marked before solving | Badge while solving plus the reveal line | |

| Option | Description | Selected |
|--------|-------------|----------|
| Truthful variant | Two welcomes, no "warm-up" | ✓ (with the owner's own wording) |
| One welcome for all | A single line true in both cases | |

| Option | Description | Selected |
|--------|-------------|----------|
| Plain line, no name | One start-screen sentence on an exhausted day | ✓ |
| No message | Session starts like any other | |

**User's choice:** Reveal line on every foreign puzzle; truthful welcome worded as "These puzzles come from games of players at your level. Once some of your games are imported and analyzed, puzzles will come from your own games."; plain line on an exhausted day.
**Notes:** Claude pointed out that warm-up covered two cases (cold start and the exhausted day, Phase 206 D-05 / D-06), so retiring it also removed the "none of your own mistakes are due today" message unless kept.

---

## Which blunders get picked

| Option | Description | Selected |
|--------|-------------|----------|
| Plain random | Any servable blunder in the rating band | ✓ |
| Facepalm cut | Only blunders at or above the facepalm cut | |

| Option | Description | Selected |
|--------|-------------|----------|
| No, rating only | No time-control matching | ✓ |
| Prefer the same | Solver's most-played time control first | |

| Option | Description | Selected |
|--------|-------------|----------|
| Guarantee one sharp | First-ever session always holds a sharp puzzle | ✓ |
| Leave it to chance | Ordering code already tolerates none | |

| Option | Description | Selected |
|--------|-------------|----------|
| Never | Per-user no-repeat, no exhaustion re-serve | ✓ |
| Only after exhaustion | Re-serve when fresh ones run out | |

**User's choice:** All four recommended options.
**Notes:** Backed by the prod supply measurement taken at the start of the discussion (see CONTEXT.md specifics).

---

## Points, streak, Activity, reveal

| Option | Description | Selected |
|--------|-------------|----------|
| Same as old fillers | Points board and streak, not the Accuracy board | ✓ |
| Count everywhere | Also on the Accuracy board | |
| Streak only, no points | Keeps the day alive, earns nothing | |

| Option | Description | Selected |
|--------|-------------|----------|
| New row, keep the old | New Activity source row; old one relabelled retired | ✓ |
| New row, hide the old | Retired solves drop out of the breakdown | |

| Option | Description | Selected |
|--------|-------------|----------|
| Show it, neutral label | Played blunder shown, no link, no names | (label part kept) |
| Hide it | Best move and own move only | |
| Show it, with game link | Neutral label plus a way to open the game | first pick, withdrawn |

**User's choice:** First "Show it, with game link". Claude raised the conflict with Phase 249 D-09 (blunder check shows a stranger's game as neutral facts, no names, no link) and the cost of each kind of link. On the follow-up:

| Option | Description | Selected |
|--------|-------------|----------|
| Neutral facts, no link | Same line as blunder check | ✓ |
| Link out to the platform | Names a FlawChess user as the blunderer | |
| Open in FlawChess, anonymised | New cross-user read endpoint | |
| Open in FlawChess, with names | Same endpoint, exposes usernames | |

**Notes:** The anonymised in-app view is recorded as a deferred idea.

---

## Claude's Discretion

- Dropping `drill_solves.sharp_puzzle_id` and the enum / wire naming
- Exact copy within the chosen directions
- How the client learns a session has no own puzzles without a session flag
- Sessions open at deploy with unsolved lichess filler rows
- Whether a foreign reveal offers the tactic line
- The replacement for `sharp_filler_available()` and empty-pool behaviour
- Acceptance criteria and test strategy

## Deferred Ideas

- Open a stranger's game in the analysis board, anonymised
- Facepalm-weighted filler draw
