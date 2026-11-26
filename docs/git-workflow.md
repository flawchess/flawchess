# Git Workflow Reference

Lookup detail for GitLab Flow in this repo. The branch model, squash-merge rule, and pre-merge gate live in the root `CLAUDE.md` because they fire on every merge; everything here is consulted on demand.

## Branch model recap

`main` is the integration trunk (pushing to it never deploys); `production` tracks the exact commit running in prod. Adopted 2026-05-16.

- The `main` squash-merge route relies on branch protection with `enforce_admins: false`. If that flips to `true`, revert to the PR route.
- CodeQL runs post-merge on `main`.
- CI (`ci.yml`) runs on PRs into `main` and `production` as three parallel jobs (backend, frontend, docker) plus a `test` aggregator, which is the required status check. Deploying is a separate workflow (`deploy.yml`).
- `bin/deploy.sh` only deploys a `production` tree that already has a green CI run (`bin/ci_green_for_tree.sh`, matched by tree, so the release PR's run counts for the squash commit). If none exists (hotfix, diverged branches) it runs `ci.yml` on `production` first. `deploy.yml` re-checks the same gate before touching the server.

## Release promotion

At a milestone boundary (or any approved release point): open a PR `main → production`, merge it, then run `bin/deploy.sh`. The `/deploy` skill automates the whole flow.

**Gotcha: `gh pr checks` reporting "no checks" on a release PR means it's unmergeable** — usually a missing forward-port of the previous release. Fix with `git merge -s ours origin/production` on `main`, push, and the check starts. Note "no checks reported" can also be a post-push race; check `mergeable` first.

**`gh pr checks --watch` is not a CI gate** — it exits 0 even on FAILED checks. Use `gh run watch <id> --exit-status`.

**Preflight: local `main` must equal `origin/main`.** The release PR is cut from `origin/main`, so unpushed local commits are silently dropped. Verify `git rev-list --left-right --count main...origin/main` returns `0 0`.

## Hotfix flow

Urgent prod fix without shipping unreleased `main`:

1. `git checkout -b hotfix/<slug> production`
2. Apply the minimal fix, PR into `production`, merge when approved.
3. `bin/deploy.sh` (deploys `production`).
4. **Forward-port**: merge `production` back into `main` (or cherry-pick the fix) so it isn't lost at the next release. Expect conflicts when `main` has diverged — resolve in favour of the prod-safe value.

Forward-port after **every** release, not just the last one: back-to-back releases conflict otherwise, and `bin/deploy.sh` skips the step whenever you are not on a clean `main` checkout.

## Changelog

Releases are cut at the **milestone** boundary, not per phase. Changes accumulate in `CHANGELOG.md` under `## [Unreleased]` as phases merge, then get promoted to a versioned section when the milestone ships.

### Per-phase (when a phase merges to `main`)

Append bullets under `## [Unreleased]`, grouped into `### Added` / `### Changed` / `### Fixed` / `### Removed` / `### Security` / `### Tests`. Reference the phase number. Keep the tone terse and user-facing (what changed, not how). Skip for small direct-commit work that doesn't meaningfully change behavior (pure refactors, tooling tweaks, internal cleanup).

### Per-milestone (when a milestone label is written)

Milestones are not planned up front; a milestone is a label over a range of releases, written after the fact (see `CLAUDE.md` "Project Management"). When one is written, **all of the following are mandatory**:

1. In `CHANGELOG.md`, rename `## [Unreleased]` → `## [vX.Y] Milestone Title — YYYY-MM-DD`, reset `[Unreleased]` to empty, and update the compare links at the bottom.
2. Add the milestone to `.planning/MILESTONES.md` and the `ROADMAP.md` milestone list, naming its phases and release range. Phase directories stay in `.planning/phases/`; milestones up to v2.32 were archived under `.planning/milestones/vX.Y-phases/` and stay there as history.
3. Tag and push: `git tag vX.Y && git push origin vX.Y`.
4. **`gh release create vX.Y`** using the `CHANGELOG.md` section as the body — the tag alone is not a release. Verify with `gh release list` that vX.Y shows up; a lingering tag with no GitHub release means this step was skipped.

Never cut a release without a matching `CHANGELOG.md` entry. Never edit a released section retroactively — corrections go in a new `[Unreleased]` bullet.
