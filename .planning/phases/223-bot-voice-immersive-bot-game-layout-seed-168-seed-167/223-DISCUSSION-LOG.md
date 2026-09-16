# Phase 223: Bot Voice & Immersive Bot Game Layout - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-15
**Phase:** 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167
**Areas discussed:** Swing signal & thresholds (the other three offered areas were left to Claude's discretion)

---

## Swing signal & thresholds

### Q1: Which signal drives the tease / bot-loses lines?

| Option | Description | Selected |
|--------|-------------|----------|
| Existing Stockfish score delta | Delta between consecutive post-bot-move expected scores the hook already computes for resign/draw gates; all 24 personas; sac-safe; zero new engine calls; silent in book | ✓ |
| Maia WDL delta | Surface wdlByElo through selectBotMove (new plumbing); rating-aware but weak on sacrifices | |
| Both, Stockfish primary | Stockfish gates, WDL picks flavor; most work | |

**User's choice:** Existing Stockfish score delta (recommended).

### Q2: Threshold

| Option | Description | Selected |
|--------|-------------|----------|
| Large only, ~0.20 | Roughly a clean piece; a couple of lines per game at most | ✓ |
| Medium, ~0.12 | Catches a pawn-plus or bad trade; chattier, riskier teases | |
| You decide | Planner picks from grade data, tunes in UAT | |

**User's choice:** Large only, ~0.20 (recommended).

### Q3: Player-threat detection

| Option | Description | Selected |
|--------|-------------|----------|
| Hanging or under-defended bot piece | Pure chess.js after the player's move; board-visible, no engine | ✓ |
| Any check or king-zone attack | Narrower, misses piece threats | |
| Stockfish-only | Score drop without capture; engine-derived, risks leaking what the bot "sees" | |

**User's choice:** Hanging or under-defended bot piece (recommended).

### Q4: Partial punishment

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, delta is delta | Realized swing over threshold earns the tease regardless of optimality | ✓ |
| No, only if top grade | Needs multi-candidate grading; hides earned lines | |

**User's choice:** Yes, delta is delta (recommended).

### Q5: Voicing a swing against the bot

| Option | Description | Selected |
|--------|-------------|----------|
| One "you got me" bucket | Single self-deprecating line that also credits the player | |
| Split by capture | Player's move captured → "you punished my mistake"; else → "nice move" compliment; cheap, occasionally wrong on a sac-in-reply | ✓ |
| Two lines, engine-decided | Extra grade per ply to attribute the drop | |

**User's choice:** Split by capture (not the recommended option; the user preferred the richer voicing over the simpler bucket).

**Notes:** Prompted to continue, the user chose "I'm ready for context" with the remaining areas left as Claude's discretion.

---

## Claude's Discretion

- Trigger priority & pacing (one line per bot move, priority order, 3-bot-move spacing, once-per-game start/first-capture, game-end line alongside the result dialog).
- Sound switch home & the gear (More drawer + desktop header account area; gear dropped from the mobile top bar).
- Roster host & greeting tables (Train's day-index rotation without the Train-only gates; two separate tables).
- Back-arrow semantics (pending store + ResumeGate), size constants, PlayerBar data sources, test strategy.

## Deferred Ideas

- A real `/settings` page.
- Maia-WDL-flavoured line variants.
