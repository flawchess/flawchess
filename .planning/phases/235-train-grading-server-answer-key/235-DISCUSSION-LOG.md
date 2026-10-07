# Phase 235: Train Grading Anchored to the Server Answer Key - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-07
**Phase:** 235-train-grading-server-answer-key
**Areas discussed:** Key delivery (P-01), Disagreement recheck, Disagreement copy + guess, Disagreement record

Pre-discussion prod query (60 days): sharp SR 1,428 solves, 934 played the key, 2 off-key graded
good; soft SR 2,371 solves, 693 off-key graded good. Showed (a) needs a two-write protocol and a
type-blind pre-POST trigger would fire on ~29% of soft solves.

---

## Key delivery (P-01)

| Option | Description | Selected |
|--------|-------------|----------|
| (b) best UCI in TrainPuzzle | Relax P-01 for the key; mount search runs after-key during think time | ✓ |
| (a) key in SolveResponse only | Keeps P-01; needs a second write to fix the tier | |
| (c) commit-guess endpoint | Key returned after the guess is recorded | |

**User's choice:** (b). User asked first whether the key was withheld for fear of leaking the
solution; on confirmation: "If users want to cheat, they can just run a separate stockfish engine in
a different tab. Let's not worry about that."
**puzzle_type:** "If sending both the best move and puzzle_type helps, assuming the user doesn't
cheat, I'd send both. If it doesn't make a difference for UX, don't send it." Claude: it helps (the
re-check can run pre-POST on sharp puzzles only) -> send both.

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to today | No key -> client mount best, today's grading | ✓ |
| Exclude from pool | Every served puzzle has a key | |

| Option | Description | Selected |
|--------|-------------|----------|
| Phone's line after the key | Server picks moves, phone supplies numbers, clamp to key line | ✓ |
| Server's stored line | Server PV/eval, mixes engines | |

**Notes:** User asked whether the server's best could read below a phone-rated second best, or
whether the server's second best would be used. Answer: the phone no longer picks alternatives; every
shown move is server-picked or user-played; small inversions are clamped as today; large ones are
the disagreement case; `su` stays the soft "also fine" move and is server-graded on sharp.

---

## Disagreement recheck

| Option | Description | Selected |
|--------|-------------|----------|
| Good or inaccuracy | Drop < MISTAKE_DROP, exactly what "sharp" denies | |
| Good only | Only the visible contradiction | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| 3s each, ~6s total | ~2x today's budget | ✓ |
| 4s each, ~8s total | Deeper, noticeable wait | |

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit message | "Taking a closer look…" | ✓ |
| Same spinner | Longer "Checking your move…" | |

| Option | Description | Selected |
|--------|-------------|----------|
| SR sharp + sharp filler | Same rule for every sharp puzzle | ✓ |
| SR sharp only | Skip filler | |

---

## Disagreement copy + guess

First pass picked "server verdict stands"; user then asked: "What's the point of double-checking if
we then don't credit the user with or use the result?" Claude conceded the inconsistency (crediting
the move while marking "several" wrong contradicts the screen) and noted a plain flip would punish a
"critical" guesser.

| Option | Description | Selected |
|--------|-------------|----------|
| Either guess counts | Position ambiguous; both guesses earn the point | ✓ |
| Only 'several' counts | Treat as soft; 'critical' becomes wrong | |
| Server verdict stands | Recheck affects move points and flag only | |

| Option | Description | Selected |
|--------|-------------|----------|
| "Qh4 is the engine's first choice, but your move holds up too." | SEED-192 draft | ✓ |
| "Close call: the engine prefers Qh4, but a closer look rates your move as good too." | Explains borderline | |
| "Qh4 and your move both work here." | Shortest | |

| Option | Description | Selected |
|--------|-------------|----------|
| Show honest phone numbers | No clamp on this path | ✓ |
| Keep the clamp | Key never visibly loses | |

---

## Disagreement record

| Option | Description | Selected |
|--------|-------------|----------|
| Every recheck | confirmed + resolved, gives a denominator | ✓ |
| Confirmed only | Smaller, no noise baseline | |

| Option | Description | Selected |
|--------|-------------|----------|
| New nullable JSONB column | Separate from telemetry because it feeds grading | ✓ |
| Boolean column + telemetry details | Split storage | |
| Telemetry keys only | Breaks Phase 233 D-05 | |

---

## Claude's Discretion

Field and column names, re-check payload keys, exact wait copy, timeout/movetime constants, D-14
sanity checks, stale-bundle degradation.

## Deferred Ideas

- "Guessed several, played the key" on a mis-classified sharp puzzle stays "wrong call" (step 4).
- Server deep re-check queue / stored puzzle-type flip for confirmed disagreements.
- Re-checking a phone "inaccuracy" reading on sharp puzzles.
