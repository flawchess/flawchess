---
name: deploy
description: Deploy FlawChess to production end-to-end (open the main → production release PR, fix whatever CI flags, squash-merge, run bin/deploy.sh, and verify the server SHA on flawchess.com). Use when the user asks to deploy, ship, release, go live, promote main to production, or run bin/deploy.sh; not for questions about how deploying works.
---

# Deploy to Production

End-to-end production deploy for FlawChess. Runs the full `main → production` release flow autonomously, including fixing whatever CI complains about along the way. Stream status updates so the user can see what's happening, but don't pause for approval unless something is genuinely ambiguous (see *When to halt*).

## When to use

- The user explicitly asks to deploy, ship, release, or push to production.
- A milestone closes and they want it live.
- A hotfix on `main` (or a fast-follow fix) needs to reach prod.

If the user is asking about deploy *mechanics* (how it works, what the script does) without asking to actually run it, don't trigger — answer the question instead.

## Mental model

FlawChess uses GitLab Flow:
- `main` = integration trunk
- `production` = exactly what's deployed
- A deploy = `main → production` PR, squash-merged, then `bin/deploy.sh` (which deploys the `production` branch via GitHub Actions).

The full pipeline is: **preflight → open PR → CI green (fix anything that fails; "no checks reported" = conflicted PR, see Step 3) → squash-merge → announce → bin/deploy.sh → monitor → verify**.

This is **set-and-forget**: run the whole pipeline end-to-end without asking for approval at intermediate steps. CI babysitting, Dependabot bumps, formatter fixes, ty errors, merge conflicts, branch divergence — handle autonomously, stream a one-line status update at each milestone, and keep moving. Stop only for situations described under *When to halt* below. Never wait for a "go ahead" between merge and deploy — that defeats the purpose of the skill.

## Step 1: Preflight

Run these in parallel and report any blockers before doing anything else:

```bash
git status --porcelain                        # working tree must be clean
git rev-parse --abbrev-ref HEAD               # should be main
git fetch origin main production --quiet      # sync refs
git rev-list --left-right --count main...origin/main  # local-ahead<TAB>origin-ahead — MUST be 0<TAB>0
git log --oneline origin/production..origin/main  # what's about to ship
```

**Don't check `.prod.env` from Bash.** Any Bash command naming the file (`ls`, `cat`, indirect `grep` probes) is refused by the secret-file protection. That is the protection working as intended; do not route around it.

Two consequences for this step:

- **Never chain preflight checks with `&&`.** Permission is evaluated over the whole command string, so one denied element aborts every check in the chain and makes a single blocked test look like a blanket deploy failure. Run the git checks as one call and anything else separately.
- **Treat `.prod.env` presence as unverifiable here and let the deploy script be the gate.** `bin/deploy.sh` fails fast and loudly at its `scp` step if the file is missing, before anything is dispatched to the server. If it does, tell the user to run `bin/download_1password.sh` and re-run. Do not halt the release preemptively on a check you cannot perform.

Blockers and how to resolve:

- **Dirty working tree** — stop and ask the user. Don't stash or commit on their behalf (might destroy in-progress work).
- **Not on `main`** — switch (`git checkout main && git pull --ff-only`) only if the working tree is clean; otherwise stop.
- **Local `main` ahead of `origin/main`** (left count > 0) — STOP and resolve before anything else. **The release PR is cut from `origin/main`, so any unpushed local commit is silently excluded from the release** (this shipped a release missing a mobile-auth fix on 2026-06-23: the fix was a local-only commit, the PR built from `origin/main` didn't include it, and it never reached production). Push the local commits first (`git push origin main`, running the relevant gates), then re-run preflight. Only skip the push if the user explicitly says a local commit should NOT ship — then confirm exactly which commits are intended for the release.
- **`main` behind `origin/main`** — `git pull --ff-only origin main` (resolve autonomously).
- **`main` and `origin/main` diverged** (non-fast-forward) — see `references/ci-fixes.md` § *Git: divergence and merge conflicts*. Resolve autonomously when the fix is mechanical (rebase clean, conflict only in lockfiles or CHANGELOG); stop and report otherwise.
- **Nothing to deploy** (`origin/production..origin/main` is empty) — tell the user, stop. Don't open an empty PR.
- **`.prod.env` missing locally** — you cannot detect this at preflight (see above); `bin/deploy.sh` surfaces it at the `scp` step. When it does, tell the user to fetch the file (`bin/download_1password.sh`) and re-run the deploy.

Then run the pre-PR gates locally so CI doesn't have to bounce them back. Run **all five**, exactly as written:

```bash
uv run ruff format app/ tests/ scripts/ analysis/
uv run ruff check . --fix
uv run ty check app/ tests/ scripts/
uv run --project analysis --with ty ty check analysis/
npm --prefix frontend run lint
```

**`analysis/` is not optional, and the pre-push hook does NOT cover it.** The hook runs ruff format, ruff check and ty over `app/ tests/ scripts/` only, so a clean "✓ pre-push gates passed" says nothing about `analysis/` — while CI gates it in two separate steps ("Format check (ruff)" over `analysis/`, and "Type check (ty, analysis project)" in `analysis/`'s own venv). Treating the hook as a substitute for this block cost two full CI round-trips on 2026-09-02: first a ruff format drift in `analysis/game_review_study/`, then a `not-iterable` ty error on an unguarded `fetchone()` in `analysis/tilt_study/`. Note the analysis ty check uses `--project analysis` because that directory has its own venv; running plain `ty check analysis/` from the root venv gives phantom unresolved-import errors.

Use `npm --prefix frontend ...` for every frontend command in this skill, never `cd frontend && ...`. The Bash tool's working directory persists across calls, so a bare `cd frontend` leaks into the next step (it once landed `bin/deploy.sh` in `frontend/` → "no such file or directory"). `--prefix` runs the npm script against `frontend/` without ever changing directory, so cwd can't leak even if the line is run on its own. If you ever do need a `cd`, wrap it in a subshell — `( cd frontend && ... )` — so the change is scoped to that one command.

If any of these modify files, commit with a `chore(release):` or `style(release):` prefix and push to `main` before opening the release PR. Skip the test suites here — CI runs them and that's faster than running locally for a release-prep step.

## Step 2: Open the release PR

Compose the PR body from the squashed commit log between `production` and `main`. Group by Conventional Commit type when possible (feat / fix / refactor / chore / docs). Keep it skimmable — this becomes the squash-merge commit message and lands in `git log` on the `production` branch.

```bash
gh pr create --base production --head main \
  --title "Release: <one-line summary of biggest change(s)>" \
  --body "$(cat <<'EOF'
## What's shipping

<grouped bullet list from git log production..main, terse and user-facing>

## Phases / PRs included

<list of phase numbers or PR refs if identifiable from commit messages>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Capture the PR number — you'll need it for the merge step.

## Step 3: Watch CI, fix anything red

```bash
gh pr checks <PR#> --watch
```

`--watch` exits 0 even when a check fails, so judge the result from the per-check states it prints (re-run `gh pr checks <PR#>` for a final table), never from the exit code.

**Gotcha (cost a hung deploy on 2026-06-11): if this reports "no checks reported", the PR is almost certainly unmergeable.** CI triggers on `pull_request`, and GitHub cannot build the `refs/pull/N/merge` ref for a conflicted PR — so the workflow never starts and there is nothing to wait for. Check `gh pr view <PR#> --json mergeable`. The usual cause is a missing forward-port of the previous release (production's last squash commit not reachable from main). Fix:

```bash
git merge -s ours origin/production -m "chore(release): forward-port production merge commit (keep main's tree)"
git push origin main
```

The push resolves the conflict and the `pull_request` check starts immediately. Do NOT wait in a polling loop on a conflicted PR.

When checks complete, if anything is failing, diagnose and fix. **Do not wake the user for this** — that's the whole point of this skill running autonomously through CI. See `references/ci-fixes.md` for the common failure modes (Dependabot vulnerabilities, ruff/ty drift, frontend test flakes, etc.) and how to resolve each.

For every fix:
1. Apply the fix on `main` (not on a side branch — the release PR tracks `main`).
2. Commit with a focused prefix: `fix(deps):`, `chore(ci):`, `style:`, etc.
3. `git push origin main` — this updates the open PR automatically.
4. `gh pr checks <PR#> --watch` again.

If you've tried 3 distinct fixes for the same failure and it's still red, stop and report what you've tried. Don't churn indefinitely.

## Step 4: Squash-merge

Once all checks are green:

```bash
gh pr merge <PR#> --squash --delete-branch=false
```

`--delete-branch=false` is critical: deleting `main` would be catastrophic. The squash merge writes one commit onto `production` with the PR title + body as the message.

After merging, sync local refs so the next `bin/deploy.sh` sees the right commit:

```bash
git fetch origin production
```

## Step 5: Announce the deploy (do not wait)

Print a one-block status message so the user knows the deploy is starting, then proceed directly to step 6 in the same turn. **Do not ask "should I deploy?" — the user invoked this skill to deploy.** They can interrupt if they need to.

The announcement should be terse, just enough to let the user scan and intervene if something is wrong:

```
✅ Merged PR #<N>  (<merge-sha>  →  origin/production)
   <one-line summary of what's shipping>
   <K> phases / <M> commits since last release
   Caveats: <any non-obvious CI fixes applied, e.g. "bumped axios 1.7.2→1.7.9 for CVE-2025-XXXX">

→ Running bin/deploy.sh now...
```

Then immediately run `bin/deploy.sh`. No question, no pause.

## Step 6: Deploy

```bash
bin/deploy.sh
```

This script already does the right things: it checks for a green CI run on the identical tree (normally the release PR's run from Step 3, so no second test run), runs `ci.yml` on `production` first if there is none, then dispatches `deploy.yml`, asserts each dispatched run is on `production@TARGET_SHA`, watches it via `gh run watch --exit-status`, and SSHes to the server to verify `HEAD` matches. It self-monitors. **Don't background it** — let its output stream so the user can see progress.

If `bin/deploy.sh` exits non-zero:

- **`scp .prod.env` failed** — usually network or SSH. Retry once. If it fails again, stop and report.
- **`no ci.yml/deploy.yml workflow_dispatch run found`** — race condition (rare). Re-run `bin/deploy.sh`.
- **`Require green CI for this tree` fails in `deploy.yml`** — the tree has no successful `ci.yml` run. `bin/deploy.sh` normally prevents this; re-run it and it will run CI first.
- **Dispatched run is on wrong branch / SHA** — abort and investigate. Do NOT bypass the assertion.
- **CI failure in the fallback `ci.yml` run on `production`** — check `gh run view <run-id> --log-failed`. If it's a transient flake, `gh run rerun <run-id> --failed` then re-run `bin/deploy.sh`. If it's a real failure, halt and report — fixing this is one of the few situations that needs the user to decide between forward-fix-via-main and hotfix-to-production.
- **Server SHA mismatch at the end** — server didn't converge. Check `ssh flawchess "cd /opt/flawchess && docker compose ps"` and the deploy logs. Don't claim success.
- **`Deploy via SSH` fails with `could not read Username for 'https://github.com'`** — the server's `git fetch` cannot authenticate. The server pulls over SSH with a read-only deploy key (`~/.ssh/id_ed25519_github`, `~/.ssh/config` entry for github.com, remote `git@github.com:flawchess/flawchess.git`); first verify the key is still on the repo (`gh repo deploy-key list`).

  **Diagnose by reading the 401's body first** (`GIT_TRACE_CURL=1 git ls-remote origin <branch>` on the server, then the `Recv data:` line). GitHub refuses anonymous fetches: if an anonymous `git ls-remote https://github.com/git/git.git` fails from BOTH the server and the local machine while an authenticated fetch succeeds, that is the cause, not this server. A green `git ls-remote` under `protocol.version=0` is NOT evidence the deploy will work: it only issues `GET /info/refs`, while a fetch needs the `POST /git-upload-pack` GitHub refuses.

- **Forward-port step reports `SKIPPED: need a clean working tree on main`** — `bin/deploy.sh` treats **untracked** files as dirty, not just modified ones, so stray reports or another session's new planning docs are enough to skip it. Don't leave it skipped: per `docs/git-workflow.md` the next release then conflicts on PR #2. Run the merge manually (`git merge -s ours origin/production && git push origin main`). If `main` carries commits from a concurrently running session, that push publishes them too — surface this and let the user decide before pushing, and never `git reset` main to tidy it, which would destroy the other session's work in progress.

## Step 7: Post-deploy verification

After `bin/deploy.sh` exits 0, do a quick liveness check and report:

```bash
curl -sS -o /dev/null -w "HTTP %{http_code} in %{time_total}s\n" https://flawchess.com/
ssh flawchess "cd /opt/flawchess && docker compose ps --format 'table {{.Service}}\t{{.Status}}'"
ssh flawchess "cd /opt/flawchess && docker compose logs --tail=20 backend"
```

Report: deploy succeeded, server is on `<sha>`, backend container is up, site responded 200. If the backend tail shows errors, surface them — the deploy script doesn't catch logical failures, only that containers came up.

## When to halt (and when NOT to)

This skill is set-and-forget. The default is: keep going, stream status, recover from anything mechanical. Halt only for these specific situations, and when you halt, surface the exact state and what you tried so the user can take over without re-investigating:

**Halt — genuinely ambiguous:**
- Dirty working tree at preflight (could be in-progress work — don't stash, don't commit on the user's behalf).
- `main` and `origin/main` diverged with conflicts outside lockfiles / CHANGELOG / generated files (anything in `app/` or `frontend/src/` that requires semantic judgment).
- `origin/production..origin/main` is empty (nothing to deploy — don't open an empty PR).
- `bin/deploy.sh` fails at the `scp` step because `.prod.env` is missing locally (it cannot be detected earlier — see Step 1).
- Same CI check has failed 3 times after distinct fix attempts — you're churning, escalate.
- `bin/deploy.sh` reports server SHA mismatch at the end — deploy did not converge, do NOT claim success.
- Deploy script aborts with "dispatched run is on wrong branch / SHA" — this is the 2026-05-16 incident's safety net firing; investigate, don't bypass.

**Do NOT halt — handle autonomously:**
- CI red because of Dependabot CVE — bump the dep (see `references/ci-fixes.md`).
- CI red because of ruff format drift — run formatter, commit, push.
- CI red because of ty error in code you just touched — fix and push.
- Branch behind `origin/main` — `git pull --ff-only`.
- Branch diverged but conflict is only in `package-lock.json` / `uv.lock` / `CHANGELOG.md` / generated files — resolve mechanically (see `references/ci-fixes.md`).
- Frontend test that's a known flake — retry once via `gh run rerun --failed`.
- Pre-push hook reformatting files — accept the reformat, commit, push again.
- `bin/deploy.sh` `scp` fails on a network blip — retry once.

When in doubt: prefer continuing with a noted caveat over halting. Halting wastes the "set and forget" property the user explicitly asked for.

## Hard rules (never break, even in auto-mode)

- **Never bypass `bin/deploy.sh`'s safety assertions** (branch check, SHA check, server SHA verify). They exist because of a 2026-05-16 incident where a deploy silently shipped unreleased `main` to prod.
- **Never deploy via direct SSH** (also a root `CLAUDE.md` rule). `bin/deploy.sh` is the only sanctioned path — it never deploys a tree without a green CI run.
- **Never force-push `main` or `production`.** Forward-fix instead. If a rebase would require force-push, halt and ask.
- **Never `git push --no-verify`** unless the pre-push hook itself is broken (then fix the hook, don't skip it). The hook catches the most common preventable CI failure on this project.
- **Never delete the `main` or `production` branch.** `gh pr merge` defaults to deleting the head branch — always pass `--delete-branch=false`.
- **Never edit `production` directly** outside of an approved hotfix flow. Releases go `main → PR → squash-merge to production`.
- **Hotfix path is separate.** If the user says "hotfix", route to the `hotfix/*` flow in `CLAUDE.md` (branch off `production`, PR into `production`, deploy, then forward-port to `main`). This skill is for the normal `main → production` release path.

## References

- `references/ci-fixes.md` — playbook for common CI failures (Dependabot, ruff, ty, frontend, etc.) that you'll resolve autonomously between steps 3 and 4.
