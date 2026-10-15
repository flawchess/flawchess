# Phase 240: Train First-Session Onboarding Load - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-10-15
**Phase:** 240-train-first-session-onboarding-load
**Areas discussed:** Puzzle-1 teaching surface, Tour split + stamp storage, Score-screen rationale fit, First-session ordering rules

---

## Puzzle-1 teaching surface

| Option | Description | Selected |
|--------|-------------|----------|
| P1 tour bubble | Result step of tour part 1 explains the call for this position, per answer type | ✓ |
| Full verdict text | One-off line in the verdict; hidden behind the strip tap on phones | |
| Both | Tour bubble plus verdict line | |

| Option | Description | Selected |
|--------|-------------|----------|
| Drop scoring explanation | [+1]/[+2] already shown; P1 stays 2 steps | ✓ |
| Move to P2 tour | P2 becomes 3 steps | |
| Third P1 step | P1 = 3 steps | |

| Option | Description | Selected |
|--------|-------------|----------|
| Just drop warm-up notice | Existing verdict tail + score clause carry it | ✓ |
| Strengthen the P1 tail | Longer warm-up tail on puzzle 1 | |
| Score screen only | No verdict change | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep welcome as is | Already short and audience-correct | ✓ |
| Tighten | Claude drafts shorter variants | |
| Merge into one bubble | Intro = 1 step | |

**Notes:** Code scan showed the phone verdict is a one-line strip, so the seed's "first verdict teaches
the vocabulary" became the tour's P1 bubble.

## Tour split + stamp storage

| Option | Description | Selected |
|--------|-------------|----------|
| Next reveal after prior part | Account-scoped, one part per reveal | ✓ |
| Session-1 puzzle index | Puzzles 2/3 of the first session only | |

| Option | Description | Selected |
|--------|-------------|----------|
| 2 new columns + reuse old | reveal_tour_1/2_seen_at, old column = part 3 | |
| 3 fresh columns | reveal_tour_1/2/3_seen_at | |
| Stage counter | SmallInteger reveal_tour_stage 0-3 | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Stamp old column at stage 3 | Keeps funnel query unchanged | |
| Retire it | Backfill stage=3, drop the column | ✓ |
| Leave it frozen | Keep for history, stop writing | |

| Option | Description | Selected |
|--------|-------------|----------|
| One-release compat shim | Accept old step, derived response field | |
| Hard cut | Stale tabs get 422 and replay the old tour | ✓ |

**Notes:** Defaults accepted: a part completes on leaving its last step; stage only advances N-1 to N.

## Score-screen rationale fit

| Option | Description | Selected |
|--------|-------------|----------|
| Shortened, merged into line 1 | Still 2 lines, fold check at UAT | ✓ |
| Own third line | Risks Phase 222 fold regression | |
| Not on the score screen | Move to tour part 3 | |

**Notes:** Scope confirmed: first completed session, all three branches (regular, perfect, warm-up).

## First-session ordering rules

| Option | Description | Selected |
|--------|-------------|----------|
| Answer-key type 'sharp' | Same classification as the verdict | ✓ |
| Source proxy | Any filler or SR item | |

| Option | Description | Selected |
|--------|-------------|----------|
| Any 'several' puzzle | Herring or soft SR, swap into puzzle 2/3 | ✓ |
| Herring only | | |
| Soft first, herring fallback | | |

| Option | Description | Selected |
|--------|-------------|----------|
| First-ever session only | No earlier drill_sessions row | ✓ |
| Until tour part 1 is seen | Reorder while stage = 0 | |

## Added by owner at wrap-up

"While we're at it, let's also remove the info on the score screen about how many puzzles will come
back when. It's not important and only adds clutter." Folded in as D-18 (all sessions; per-puzzle
verdict return tails stay).

## Claude's Discretion

- All new/rewritten copy within the 145-char budget (owner reviews at UAT).
- Onboarding endpoint shape for the stage advance.
- Tour-part selection logic on the reveal; Phase 233 `review_walkthrough` flag handling.

## Deferred Ideas

None.

## Follow-up (same session)

- Owner asked for the full copy sheet with conditional variants; reviewed and accepted it, with the
  warm-up shortening on the first completed session (line 1 drops "nothing to bring back yet"). Added
  as D-19 + the sheet in CONTEXT `<specifics>`.
- Owner: "the highlighting of the elements which are being explained should be more salient. How about
  a gold border (like the flaw fixed card) with a pulsating golden glow?" Added as D-20 (reuses the
  flaw-fixed bronze `rgba(205,127,50,…)`, one shared spotlight class, reduced-motion fallback, the chips
  row now gets highlighted too).
