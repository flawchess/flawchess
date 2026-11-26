# Phase 251: Blunder-Check Schedule, Streak and Leaderboards (SEED-261108-dk0) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-18
**Phase:** 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-dk0
**Areas discussed:** Launch and first run, Leaderboard details
**Areas offered, not selected:** Streak day edge cases, Cross-mode cooldown rules

---

## Launch and first run

### Rollout

| Option | Description | Selected |
|--------|-------------|----------|
| Beta soak, then flip (Recommended) | Ship behind the beta flag first (non-beta users count as blunder-check size 0), play it on prod for a few days, then a small release drops the gate. | |
| Everyone in one release | The merging release drops the beta gate for registered users and guests at once. | ✓ |
| Registered first, guests later | Drop the gate for registered users at merge; guests in a follow-up release. | |

**User's choice:** Everyone in one release
**Notes:** Chosen over the recommendation. CONTEXT D-18 records that the streak rule gets no prod rehearsal and asks for test coverage instead.

### Pitch line

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, until first session (Recommended) | One line under the Blunder Check row, gone after the first completed blunder-check session. | ✓ |
| Yes, for both modes | Same rule on the Puzzles row too. | |
| No, keep it collapsed | Variant B as sketched; discovery rests on the Phase 255 dot and the launch notice. | |

**User's choice:** Yes, until first session

### Level question

| Option | Description | Selected |
|--------|-------------|----------|
| One-time step after first Start (Recommended) | First Start shows the level choice plus short how-it-works, once, only for users without rated games; the Phase 249 start screen is retired. | ✓ |
| Only in the collapsed row | No extra screen; Start uses Intermediate unless the user opens the collapsed row. | |
| Keep a start screen for everyone | Every first session of the day lands on the Phase 249 start screen. | |

**User's choice:** One-time step after first Start

### Launch notice

| Option | Description | Selected |
|--------|-------------|----------|
| Existing Train users, until acted on (Recommended) | Users with a settings row before launch; gone on dismiss, on a completed blunder-check session, on changing the amount, or after 14 days. | ✓ |
| Streak holders only | Same dismissal rules, only for users with a streak above 0 on launch day. | |
| Everyone, fixed 7 days | Time-boxed banner for all users, no per-user state. | |

**User's choice:** Existing Train users, until acted on

---

## Leaderboard details

### Minimum windows for Score %

| Option | Description | Selected |
|--------|-------------|----------|
| 18 windows (Recommended) | Three default sessions, about the effort of the 20-puzzle rule. | ✓ |
| 12 windows | Two default sessions; fills podiums faster, noisier. | |
| 30 windows | Five default sessions; stable, but the board may sit empty at first. | |

**User's choice:** 18 windows

### Lifetime medal tally

| Option | Description | Selected |
|--------|-------------|----------|
| Per mode (Recommended) | Blunder-check boards count blunder-check medals; puzzle boards count puzzle medals. | ✓ |
| Combined across modes | One tally per player on every board. | |
| Per board | Each of the four boards shows only its own medals. | |

**User's choice:** Per mode

### Default mode on the leaderboard card

| Option | Description | Selected |
|--------|-------------|----------|
| Last viewed, else Puzzles (Recommended) | Remembered in the browser; first visit opens on Puzzles; the blunder-check score screen links to its boards. | ✓ |
| The mode the viewer trained last | Server reports the most recent completed session's mode. | |
| Always Puzzles | Fixed default, no memory. | |

**User's choice:** Last viewed, else Puzzles

### Guest view

| Option | Description | Selected |
|--------|-------------|----------|
| Same as puzzles today (Recommended) | Public board plus the guest's private would-be row and the existing sign-up ask. | ✓ |
| Public board only | No would-be row on the blunder-check boards. | |

**User's choice:** Same as puzzles today

---

## Claude's Discretion

- Streak day edge cases (not selected): puzzles with nothing to serve are not required that day; an open blunder-check session expires with its session day; an off-day freeze credit needs every required mode; the reminder fires while any required mode is pending; days settled before launch stay as judged.
- Cross-mode cooldown (not selected): 7 days keyed on the flaw; interaction with the puzzle spaced-repetition ladder left to research.
- Which windows count toward the weekly boards, tie-breaks, the medal dialog layout, slider bounds, board key names, copy.

## Deferred Ideas

- Adaptive level from the catch rate.
- Reusing the stored level for the lichess warm-up puzzles and the default bot strength.
- Single-retry spaced repetition.
- Progress stats without re-serving (catch-rate trend, facepalm rate in real games).
- Blunder-check windows in the Archive tab.
