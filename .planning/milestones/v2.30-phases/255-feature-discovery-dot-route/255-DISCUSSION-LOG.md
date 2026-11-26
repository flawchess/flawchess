# Phase 255: Feature Discovery Dot Route (SEED-261115-d0t) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-15
**Phase:** 255-Feature Discovery Dot Route (SEED-261115-d0t)
**Areas discussed:** Route contents and order, Ignored steps, Completion and veterans, Scope edges

Background: the idea came from an unsaved `/gsd-explore` session on 2026-11-09 (dot only, one dot at a time,
solve the path problem). Server-side storage was chosen on 2026-11-15 before the discussion. At area selection
the owner added: "We might remove dots for some features like opening bookmarks. We only want to use the dot
on the important stuff to avoid dot fatigue."

---

## Route contents and order

| Question | Options | Selected |
|----------|---------|----------|
| Top-level sections as steps | Openings, Endgames, Train, Bots | all four |
| Subtabs as steps | Library Flaws, Library Stats, Openings Stats, Train blunder check | Library Stats, Openings Stats |
| Openings sidebar chain | Remove all three (recommended), Remove bookmarks only, Fold into the route | Fold in played-as and filters, drop bookmarks |
| Route order | Analysis first, Nav bar order, Engagement first | Engagement first: Train, Bots, then the rest |
| Order after Train and Bots | Openings block then Endgames then Library Stats (recommended), Sections first, Library Stats before Openings | Openings block, Endgames, Library Stats |
| Blunder-check tab | Add when it leaves beta (recommended), Add now for beta users, Never | Add when it leaves beta |

**Notes:** The first version of the Bots option wrongly said Bots sits under Train in the nav; it is a
top-level item, corrected before the order question. The owner rejected the first order question to state
"Engagement first: 1. Train, 2. Bots, ...".

---

## Ignored steps

| Question | Options | Selected |
|----------|---------|----------|
| Stuck dot | Auto-skip after N days shown (recommended), Strict wait, Skip on any other progress | Auto-skip after N days shown |
| N | 3 (recommended), 5, 7 | 3 days |
| New feature while older steps are open | Jumps the queue (recommended), Always route order | Always route order |

**Notes:** Owner: "Maybe the user_activity table can help since it contains records for each day a user was
active."

---

## Completion and veterans

| Question | Options | Selected |
|----------|---------|----------|
| When is a step done | Visit for pages and use for controls (recommended), Real use everywhere, Visit everywhere | Visit for pages, use for controls |
| Existing users | Carry over old flags with new steps open (recommended), Infer from server data, All done, Everyone starts fresh | All done for existing users |
| Completion before the dot arrives | Record every completion (recommended), Only the current step | Record every completion |

---

## Scope edges

| Question | Options | Selected |
|----------|---------|----------|
| Train count badge | Badge replaces the dot (recommended), Badge pauses the route | Badge replaces the dot |
| Library import dot | Stays separate (recommended), Becomes step 0 | Becomes step 0 of the route |
| Guests | Same route (recommended), Registered only | Same route |
| Sticky subnav | Keep out (recommended), Make Library's subnav sticky | Keep out |
| Import step auto-skip | Never skips (recommended), Skips to Train and Bots only | Free text, see notes |

**Notes:** On the import step the owner answered: "Some users may have no chess.com or lichess account. I
think the dot should clear when the import subnav is visited (happens automatically I think as this is the
landing page when no games have been imported)."

---

## Claude's Discretion

Storage shape, the step-became-current timestamp, how existing users are identified, handling of steps whose
target is locked without games (suggested: no dot and no skip clock while locked; not asked explicitly), dot
geometry on subtabs and controls, the mobile drawer path, cleanup of old localStorage keys, Umami events.

## Deferred Ideas

Blunder-check step when it leaves beta; SEED-199's sticky subnav, tab affordance, renaming, teaser links and
post-import bubble links; "What's New" panel and "New" pills (rejected for now).
