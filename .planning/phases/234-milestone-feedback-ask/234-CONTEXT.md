# Phase 234: Milestone Feedback Ask - Context

**Gathered:** 2026-10-05 (plan-phase, no discuss-phase run)
**Status:** Ready for planning

<domain>
## Phase Boundary

Scope and locked design live in the ROADMAP Phase 234 section and `.planning/seeds/SEED-191-milestone-feedback-ask.md`
(eligibility, three surfaces with one shared state, lifecycle, `users.prompt_state` JSONB, `feedback.source`).
This file records only the owner decisions taken after research (234-RESEARCH.md "Open Questions").

</domain>

<decisions>
## Implementation Decisions

- **D-01:** Ask copy inserts the user's actual `active_days`: "You've been with FlawChess for {N} days now, thanks! Got an idea that would make it better for you?" (the literal "5 days" is wrong for most recipients: ~98 users eligible at launch, re-asks fire at 15+).
- **D-02:** The round-2 re-ask uses the same copy as round 1 (with `active_days` inserted it reads differently on its own).
- **D-03:** Import page: the ask replaces both the `EXPLORE_PARTS` bubble and the `welcome` variant (registered user who never completed an import). One rule: the ask wins on the Import page whenever it is active.
- **D-04:** Train landing: the Train intro wins. Hilda does not replace Tank's intro host while the Train intro is not completed; the ask shows on the Train landing only once the intro is done.
- **D-05:** No UI-SPEC for this phase (owner decision). Surfaces reuse the existing bot-bubble components and styles.

### Claude's Discretion
- Research-recommended state fields (`round`, `snoozed_by`), counting today in `active_days`, app-level FeedbackModal host, and the shared GET/PUT profile builder are research recommendations the planner may adopt; they are not owner-locked.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/seeds/SEED-191-milestone-feedback-ask.md` — locked design
- `.planning/phases/234-milestone-feedback-ask/234-RESEARCH.md` — code map, SQL transitions, pitfalls

</canonical_refs>
