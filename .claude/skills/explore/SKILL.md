---
name: explore
description: Think a vague idea through with the user and, if it holds up, capture it as a seed in .planning/seeds/. Use when the user wants to explore, brainstorm, think through or kick around an idea, hunch or "what if" that has no seed yet (e.g. "let's explore X", "I have a vague idea about Y"). Not for stress-testing an existing seed or plan (that is /grill-me) and not for implementing anything.
---

# Explore an idea

A conversation that takes a hunch to the point where it is either a seed worth keeping or an idea knowingly dropped. Nothing is implemented, and nothing is written to disk until the user says so.

This is the step before `/grill-me`. Explore widens first and asks what the idea even is. Grilling takes a seed that already has shape and settles every open decision in it.

## How to run the conversation

1. **Start from what the user said.** Restate the idea in one or two sentences and ask the first question. No preamble, no plan of the session.

2. **Check for prior art first.** Before going deep, search `.planning/seeds/` (including `closed/`), `.planning/phases/` and `ROADMAP.md` for the same idea. If a seed already covers it, say so and continue from that seed. Never start a second document for the same idea.

3. **Widen before narrowing.** Early on, the useful questions are about the problem, not the solution:
   - What is the user-visible problem, and who has it?
   - What would be different if this existed? How would we notice?
   - What are two or three different shapes this could take, including the smallest one?
   - What happens if we do nothing?

4. **One or two questions per turn.** This is a conversation, not a questionnaire. Follow the thread the user's answer opens instead of working through a list. Give your own view: propose alternatives, say which one you would pick and why, and say so plainly when the idea looks weak, already solved, or more expensive than it is worth.

5. **Look facts up yourself.** When a question turns on a fact (how the code works today, how often something happens in prod, what the benchmark says, whether users touch a feature), find it instead of asking. Database, Umami and Sentry lookups run in the main session, because subagents do not get the project MCP servers. Use a subagent only for a broad code read that would flood this context. A feature that shipped recently has no usage data worth reading: argue from first principles there.

6. **Notice when it has converged.** The idea is ready when you can state the problem, the proposed shape, the rough size, and what is still unknown. Say that you think it is ready and summarise it in a few lines. Do not push for convergence early, and do not keep asking once the user has what they need.

## Ending the session

Offer the outcome that fits, and let the user choose:

- **A new seed** (the usual case). Write it as described below.
- **An addition to an existing seed**, when step 2 found one. Edit that file in place.
- **Small work**: the idea turned out to be a fix or tweak that needs no phase. Say so; it becomes a direct commit when the user asks for it.
- **Nothing**: the idea did not hold up. That is a good result. Write nothing unless the user wants the reasoning kept, in which case a short seed with `status: rejected` and the reason saves the same discussion next time.

Do not promote the seed to a phase, create a branch, or start planning from this skill. Close by naming the next step: `/grill-me SEED-<id>` to settle the open questions, then promotion.

## Writing the seed

File: `.planning/seeds/SEED-<YYMMDD>-<xxx>-<kebab-slug>.md`, where `<YYMMDD>` is today's date and `<xxx>` is three random lowercase letters or digits (check that the id is unused).

```markdown
---
id: SEED-<YYMMDD>-<xxx>
status: dormant
planted: <YYYY-MM-DD>
planted_during: <what prompted it, e.g. "explore session, no active phase">
trigger_when: <the concrete condition under which this should be picked up>
scope: <rough size, and what would have to be learned to size it properly>
---

# SEED-<YYMMDD>-<xxx>: <title, phrased as the question or the outcome>

<Two or three sentences: the idea and why it is worth keeping.>
```

Then the sections the idea actually needs. Match the existing seeds; the usual ones are:

- **Why This Matters**: the problem, with the concrete case or number that motivated it.
- **What Was Established**: facts looked up during the session, dated, with where they came from.
- **The Idea**: the proposed shape, and the alternatives considered with the reason each was set aside.
- **Open Questions**: what must be answered before this becomes a phase. These are what `/grill-me` works through.
- **Cost Notes** or **Constraints**: anything that bounds the solution.
- **Related**: other seeds, phases, files.

Write what was actually discussed and decided. Record the user's decisions as theirs and dated; mark your own suggestions as suggestions. Leave out sections that would be empty.
