---
id: SEED-261122-v4c
status: dormant
planted: 2026-11-22
planted_during: Phase 261 planning (blunder-check exploration arm), a workflow review session with the owner
trigger_when: after Phase 261 is merged to main and no phase is mid-flight. Do not switch workflows in the middle of a phase
scope: small. No app code. CLAUDE.md, docs, two vendored skill files, GSD config or uninstall. One trial of two or three phases before the uninstall
---

# SEED-261122-v4c: Replace Open GSD with vanilla Claude Code, documentation directives in CLAUDE.md and the grill-me skill

Stop running the Open GSD pipeline (research, pattern mapping, planner, plan checker, executor
subagents, Nyquist validation, state tooling). Keep the written record of what was done and why,
in the same places it lives today, enforced by a short set of rules in `CLAUDE.md`. Use Matt
Pocock's `grill-me` skill to refine seeds in place of `/gsd-explore`.

## Why This Matters

- The owner values the record (seeds, decisions, summaries) and does not want to lose it. The
  owner doubts the rest of the machinery still earns its place with Opus 5.5 and Fable 5.2.
- Most of `.planning` is scaffolding, not record. Measured 2026-11-22: CONTEXT + SUMMARY files
  are about 267k lines (26% of the main artifacts); PLAN + RESEARCH + PATTERNS + VALIDATION are
  about 673k lines (66%). The directory is 96 MB and 5,769 files.
- 538 of 1,464 commits in the last 90 days touch only `.planning` (37%).
- About 15 of roughly 110 memory notes are workarounds for GSD machinery: executors dying on
  long plans, subagents without the project MCPs, the commit helper recreating the phase branch,
  `phase.insert` misbehaving, `gsd-health --repair` pruning the backlog, sentinel TTLs.
- Outside evidence points the same way, though it is mostly practitioner opinion and none of it
  measures GSD on current models. Anthropic's harness post: every harness component "encodes an
  assumption about what the model can't do on its own", and those go stale; they dropped context
  resets and the sprint construct as models improved, and kept a planner and one final evaluator
  pass. One independent benchmark (akitaonrails, August 2026) found no multi-agent setup beating
  a single strong model in a simple loop.
- None of this shows GSD-run phases came out worse. The numbers are cost and friction. The trial
  below is the real test.

## Owner Decisions (2026-11-22)

1. **Keep the record.** Documentation of what was done and why stays, in the places Open GSD
   uses today.
2. **Seeds stay.** The owner likes capturing and refining an idea in a seed document before
   implementing it.
3. **Direction: vanilla Claude Code with documentation directives plus grill-me.** Chosen over
   the Superpowers plugin after comparing the two. The owner proposed grill-me.

Everything under "Recommended Design" is a recommendation from the session, not yet confirmed
by the owner.

## Alternatives Considered

- **Stay on GSD, configured down** (`plan_check`, `nyquist_validation` and default `research`
  off). Cheapest step and fully reversible. It is the first stage of the trial below, not a
  separate option.
- **Superpowers plugin.** Rejected. It is by Jesse Vincent (obra) and Prime Radiant, not by
  Anthropic; Anthropic only lists it in the official marketplace. Its default flow is still a
  plan handed to one subagent per task, with strict TDD and a worktree per feature. The rules
  this project needs would switch off most of it, and it has no seed lifecycle, no SUMMARY, no
  roadmap. What remains after overriding is three or four skills that plain Claude Code covers.

## Recommended Design

### Rules for CLAUDE.md (replace the "Project Management" section)

1. **Seeds** live in `.planning/seeds/` with the current frontmatter (`id`, `status`, `planted`,
   `planted_during`, `trigger_when`, `scope`). Refine a seed in place; never start a parallel
   document for the same idea.
2. **Promotion.** A promoted seed gets `.planning/phases/NNN-slug/`, an entry in `ROADMAP.md`,
   and a "Promoted" line in the seed.
3. **`CONTEXT.md` before code.** Locked decisions with their reasons, and what is deferred.
   Written to disk before any `/clear` (memory: persist discuss decisions before /clear).
4. **One plan per phase, executed inline.** Plan in the session (plan mode); save the plan in
   the phase folder only when the phase spans sessions. No planner or executor subagents by
   default. Subagents only for independent parallel work.
5. **Research on demand,** only for phases with real unknowns (a new library, an algorithm
   choice), saved as `RESEARCH.md`.
6. **`SUMMARY.md` at the end.** Short: what shipped, deviations from CONTEXT, what was learned,
   what is deferred.
7. **One independent review before the squash-merge** (`/code-review`, or a fresh reviewer given
   named claims to attack; memory: self-review misses load-bearing defects). Then the existing
   pre-merge gate.
8. **Scope rule stays.** No unplanned features or refactors outside the current phase; flag
   them, or capture a seed.

### Quality safeguards (what GSD's checker, verifier and validation agents did, kept in light form)

Code review finds bugs in the diff. It does not check that the phase built the right thing, or
all of it. These rules cover that gap without bringing the agents back.

1. **Acceptance criteria in `CONTEXT.md`.** A short numbered list of observable outcomes,
   written before code. This replaces the plan checker: a plan is good if it reaches them.
2. **Goal check at the end, with evidence.** `SUMMARY.md` lists each criterion with how it was
   proven: a test name, a command and its output, a query result, or a screenshot. "Implemented"
   is not evidence. This replaces the verifier.
3. **Every criterion maps to a test or a named manual check.** Decided when the criteria are
   written, not after. This replaces Nyquist validation.
4. **Run the real thing.** User-facing changes are exercised in the running app (browser UAT run
   by Claude; memory: run human-action checkpoints yourself), not only through unit tests.
   Hardware legs and the deploy call stay with the owner.
5. **Bug fixes are proven by reverting.** Revert the fix, watch the new test fail, restore
   (memory: mutation-test gap closures).
6. **Review effort scales with risk.** Default `/code-review` for ordinary phases. Higher effort,
   or a fresh reviewer with named claims to attack, for migrations, eval and scoring logic, and
   anything that writes prod data.
7. **Owner spot-check for judgement outputs.** Labels, tags, scores and copy get a human sample
   before merge; automated gates do not catch a wrong notion of "correct" (memory: D-05
   persistence drops real sacrifices).
8. **Deviations are written down.** Any departure from CONTEXT goes into SUMMARY with the reason,
   so the record stays true.
9. **Long phases checkpoint to disk.** Decisions and progress go into the phase folder before a
   `/clear` or a session end. GSD gave each plan a fresh context; without it, the files carry
   the continuity.

Unchanged and still required: the full pre-merge gate, the full serial suite before a release
(memory: serial CI hides isolation bugs), CI on the release PR.

### Enforcement

With no framework, the summary is the step that gets skipped. Add it to the pre-merge gate: no
squash-merge of a phase without `SUMMARY.md` (criteria with evidence), the independent review
and a `CHANGELOG.md` bullet.

### grill-me

- Source: `mattpocock/skills`. `grill-me` is a one-line wrapper around `grilling` (about 25
  lines); both are needed. It only runs when called (`disable-model-invocation: true`).
- It asks every currently answerable decision in one numbered round, each with a recommended
  answer, and stops when nothing is left assumed. It writes no files.
- **Vendor both folders into `.claude/skills/`** by hand instead of installing through the CLI,
  so two local edits are possible:
  - after a session on a seed, write the settled decisions into the seed file;
  - fact lookups that need the DB MCPs run from the main session, because subagents lack the
    project MCPs (the upstream skill dispatches a subagent per lookup).
- Do not install `grill-with-docs`. Its `domain-modeling` skill creates ADRs and a glossary,
  a second record system competing with seeds and CONTEXT.

### Migration steps

1. **Trial on GSD config first.** Set `plan_check` and `nyquist_validation` to false and
   `research` to false by default in `.planning/config.json`. Run two or three phases as
   discuss, one inline plan and execution, summary, one independent review.
2. **Judge the trial** on wall-clock time per phase, rework found by the review, and whether
   CONTEXT and SUMMARY still answer "why did we do this" a month later. For quality, count
   escaped defects per phase: `fix` commits and new Sentry issues that trace back to the phase
   in the weeks after its merge. Take the same count for the last few GSD-run phases first, so
   there is a baseline to compare against.
3. **If it holds:** rewrite the CLAUDE.md section, vendor the two skills, remove the GSD skills
   and agents, and update the docs that mention GSD (`docs/git-workflow.md` milestone-close
   checklist, `docs/dev-tooling.md`, the `/gsd-quick` and `/gsd-fast` mentions in CLAUDE.md
   "Coding Guidelines").
4. **Leave the archive alone.** Existing `.planning/milestones/` and phase folders stay as
   history. Stop producing PATTERNS, VALIDATION and per-plan PLAN files going forward.
5. **Prune memory.** Drop the GSD-machinery notes once the tooling is gone.

## Open for the Discuss Step

- Keep `STATE.md` and `state.json`, or let `ROADMAP.md` plus git carry the state? Both exist
  for GSD's tooling; a hand-kept `STATE.md` may drift.
- Milestones: keep the milestone grouping and `MILESTONES.md` by hand, or drop to phases plus
  release tags and the changelog?
- Phase numbering and branch naming (`branching_strategy: phase` today) without the helpers.
- What replaces `/gsd-quick` and `/gsd-fast` for small work: nothing (a direct commit on
  `main`), or a one-line log in `.planning/quick/`?
- `VERIFICATION.md` and `UAT.md`: fold into SUMMARY, or keep as separate files when a phase has
  real UAT?
- Whether the trial should include one phase run fully through GSD as a comparison arm.

## When to Surface

After Phase 261 is merged to main and before the next phase is planned. Surface earlier if GSD
tooling blocks work again.

## Scope Estimate

Small. The config change is minutes. The CLAUDE.md rewrite, the two vendored skills and the doc
updates are one short session. The trial runs alongside normal phase work and adds no work of
its own.

## Breadcrumbs

- `CLAUDE.md` "Project Management" section (the rule that all work goes through GSD phases).
- `.planning/config.json` (`workflow.research`, `plan_check`, `verifier`,
  `nyquist_validation`; `git.branching_strategy`).
- Anthropic, "Harness design for long-running apps":
  https://www.anthropic.com/engineering/harness-design-long-running-apps
- akitaonrails benchmark:
  https://akitaonrails.com/en/2026/08/18/hot-take-harness-loop-engineering-graph-engineering-are-bullshit/
- grilling skill source:
  https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity/grilling/SKILL.md
- Superpowers (rejected): https://github.com/obra/superpowers
