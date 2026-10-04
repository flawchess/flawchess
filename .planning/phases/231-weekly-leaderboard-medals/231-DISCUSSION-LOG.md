# Phase 231: Weekly Leaderboard Medals - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-10-04
**Phase:** 231-weekly-leaderboard-medals
**Areas discussed:** none interactively; the owner answered "You decide" for all presented areas

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Who gets a final row | Hidden / guest / tentative Accuracy rows; one vs two hint lines | |
| Medal dialog content | Entry content, medal visual, sound reuse, where it appears | |
| Podium edge states | First week, empty board, no qualifiers, which week | |
| Medal floor edge cases | 0 points earning a medal; fewer than 3 entrants | |

**User's choice:** "You decide" (all four areas delegated to Claude).
**Notes:** SEED-186 and the ROADMAP entry already locked nearly every user-facing decision, so only
these edges were open.

## Claude's decisions (recorded in CONTEXT.md)

- Who gets a final row: public board only (Points all public entrants, Accuracy qualified only); no
  rows for hidden, guest or tentative users; "finished #N" is a separate hint line for non-medallists (D-01..D-04)
- Medal floor: value must be above zero; fewer entrants means fewer medals (D-05, D-06)
- Podium: immediately previous week only, hidden when that board awarded nothing (D-07..D-09)
- Dialog: Train landing only, all unclaimed medals newest first, tinted lucide Medal, reuse `game-win` sound,
  Claim closes the dialog after firing confetti and sound, dismiss claims silently (D-10..D-13)

## Deferred Ideas

- "Finished #N" / "N short of qualifying" for hidden and tentative users
- Revisit the zero-value medal rule if the owner prefers no floor at all
