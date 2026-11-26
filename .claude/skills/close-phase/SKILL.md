---
name: close-phase
description: Close a FlawChess phase and integrate it into main (browser UAT, independent code review, SUMMARY.md with evidence, STATE.md, changelog bullet, full pre-merge gate, local squash-merge). Use when the user asks to close, finish, wrap up, merge or ship a phase (e.g. "close phase 264", "ship phase 264"). Not for production deploys (that is /deploy) and not for small direct-commit work.
---

# Close a phase

Runs the closing sequence from the "Project Management" section of the root `CLAUDE.md`. That section holds the rules; this skill fixes the order so no step is skipped. Work through the steps in order, in the main session, and do not merge until every one is done.

The phase is the one named in the request, or else the current `phase/NNN-slug` branch. Its folder is `.planning/phases/NNN-slug/`.

## Steps

1. **Preflight.** Confirm the branch is `phase/NNN-slug`, the working tree is clean (commit pending phase work first), and `CONTEXT.md` exists with numbered acceptance criteria. If there are no criteria, stop and say so: there is nothing to close against.

2. **Run the real thing.** For user-facing changes, exercise them in the running app with browser UAT, driven by you. Legs that need hardware or the owner go into `UAT.md` in the phase folder and do not block the merge.

3. **Independent review.** Invoke `/code-review` on the phase diff against `main`.
   - Ordinary phase: the default level.
   - Migrations, eval or scoring logic, anything that writes prod data: `high`, or a fresh reviewer agent given the phase's named claims to attack.
   - Never `max` or `ultra` unless the user asked for it.

   Fix the real findings and commit. A bug fix gets a test that is proven by reverting the fix and watching the test fail.

4. **Owner spot-check.** If the phase produces judgement outputs (labels, tags, scores, copy), put a sample in front of the user and wait for their answer before merging. This is the one step that pauses the sequence.

5. **`SUMMARY.md`** in the phase folder: what shipped, every acceptance criterion with its evidence (a test name, a command and its output, a query result, a screenshot; "implemented" is not evidence), deviations from `CONTEXT.md` with the reason, what was learned, what is deferred. A criterion without evidence is reported as open, not passed.

6. **`STATE.md`**: update the current position and the open threads carried forward. Mark the phase done in `ROADMAP.md`.

7. **`CHANGELOG.md`**: add the user-facing bullets under `## [Unreleased]`.

8. **Pre-merge gate.** Run the full gate from the root `CLAUDE.md`, every command, after the last code change. If a step modifies files, commit with a `style(...)` or `chore(...)` prefix. A subset run is not acceptable here.

9. **Squash-merge.**
   ```bash
   git checkout main
   git merge --squash phase/NNN-slug
   git commit            # one conventional commit describing the phase
   git branch -D phase/NNN-slug
   git push origin main
   ```
   Pushing `main` never deploys. If the phase lived in a dedicated worktree, remove the worktree too.

10. **Report.** State the squash commit, the criteria and their status, the review outcome, and anything left open (`UAT.md` legs, deferred items, new seeds). Do not deploy: that is a separate decision and a separate skill.

## When to stop instead of merging

- An acceptance criterion fails or has no evidence, and the user has not agreed to defer it.
- The review found a defect that is not fixed.
- The gate is red.
- The owner spot-check in step 4 is outstanding.

In each case, report what is blocking and leave the branch unmerged.
