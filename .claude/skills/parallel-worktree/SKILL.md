---
name: parallel-worktree
description: Create a git worktree and spin up a second Vite dev server for a parallel Claude Code session on FlawChess. Use this skill whenever the user wants to work on UI tweaks, small frontend fixes, or a side branch while another Claude session is busy with a long-running task (e.g., a GSD phase implementation). Trigger on phrases like "parallel worktree", "second worktree", "side branch", "run a second frontend", "work in parallel on another branch", "spin up another dev server", "/parallel-worktree", or any request to set up an isolated working copy alongside the current one. Frontend-only — deliberately does NOT start a second backend, because `bin/run_local.sh` would kill the primary session's processes.
---

# Parallel Worktree

Set up a second working copy of FlawChess in a git worktree and run a second Vite dev server alongside the primary session. Useful when one Claude session is running a long task (e.g., a GSD phase) and you want an independent session on a separate branch to work on UI tweaks or small fixes without disturbing it.

## When to use

The user has a long-running task in one terminal and wants a second Claude session in a separate branch to work on something independently. The second session shares the primary session's backend on `:8000` and the shared Docker Postgres on `:5432`. Only the frontend is duplicated.

If the user needs a fully isolated stack (separate backend, separate DB, migration testing in isolation), this skill is **not** the right tool — tell them so. They'd need a different setup (alt ports for uvicorn, a separate Docker compose project name for Postgres, Vite proxy override). Flag it rather than half-solving it.

## Why frontend-only

`bin/run_local.sh` begins with `pkill -f "uvicorn app.main:app"`, `pkill -f vite`, `fuser -k 8000/tcp`, and `fuser -k 5173/tcp`. Running it in a second worktree would kill the primary session's backend and frontend. So this skill avoids `run_local.sh` entirely and only starts Vite.

The Vite proxy in `frontend/vite.config.ts` forwards `/api` requests to `localhost:8000`, so the second frontend automatically hits the backend the primary session is already running. The database is shared through Docker Postgres on `:5432` — both sessions see the same data.

## Arguments

- `<branch-name>` (required) — the new branch name (created from `origin/main`). Also used as the directory name under `.claude/worktrees/`.
- `[port]` (optional, default `5174`) — port for the second Vite dev server. Must not collide with the primary `5173`.

If the user invokes the skill without a branch name, ask for one. Suggest something short and task-scoped (`ui-tweaks`, `fix-bookmark-icons`, `tighten-spacing`).

## Preconditions

Check these before touching anything — fail fast with a clear message if any fails.

### 1. Primary backend is live on :8000

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health
```

If not `200`, warn the user: the second frontend will load, but every API call will 502 until the primary session's `bin/run_local.sh` is running. Ask whether to proceed anyway or abort.

### 2. Target port is free

```bash
lsof -ti :<port> -sTCP:LISTEN 2>/dev/null && echo occupied || echo free
```

If occupied, ask the user for a different port. Don't silently pick the next one — they may have something intentional running there.

### 3. Branch name is not already a worktree

```bash
git worktree list | grep -F ".claude/worktrees/<branch-name>"
```

If the branch already exists as a worktree, offer to reuse it (skip step 2, go straight to npm install + Vite) or pick a different name.

### 4. Branch name is free

```bash
git show-ref --verify --quiet refs/heads/<branch-name> && echo exists || echo ok
```

If the branch exists but is not checked out anywhere, offer to check it out instead of creating a new one (use `git worktree add .claude/worktrees/<branch-name> <branch-name>` without `-b`).

## Steps

Run from the primary worktree root (the main checkout, typically `/home/aimfeld/Projects/Python/flawchess`).

### 1. Fetch origin/main

```bash
git fetch origin main
```

So the new branch starts from the latest remote state, not a stale local main.

### 2. Create the worktree

```bash
git worktree add -b <branch-name> .claude/worktrees/<branch-name> origin/main
```

The new branch tracks `origin/main`. The worktree lives under `.claude/worktrees/` so it's scoped to this project and hidden from normal directory listings.

### 3. Install frontend dependencies

```bash
cd .claude/worktrees/<branch-name>/frontend && npm install
```

`node_modules` is NOT shared across worktrees — each worktree needs its own. This takes ~10-30s with a warm npm cache.

### 4. Start Vite on the alt port (detached)

```bash
cd .claude/worktrees/<branch-name>/frontend
nohup npm run dev -- --port <port> --strictPort > /tmp/vite-<branch-name>.log 2>&1 &
disown
```

Detached so it outlives the current shell. Use `--strictPort` so Vite fails loudly if the port is taken instead of silently picking `5175` (which would leave the user confused about which URL to open). Logs go to `/tmp/vite-<branch-name>.log` for later tailing.

### 5. Verify it's serving and proxying

```bash
sleep 3
curl -s -o /dev/null -w "html:%{http_code} api:%{http_code}\n" http://localhost:<port>/ http://localhost:<port>/api/health
```

Both should return `200`. If `html` is not 200, read `/tmp/vite-<branch-name>.log` and surface the error. If `api` is not 200, the backend on `:8000` is down — tell the user.

### 6. Report to the user

Use this exact template so all the information they need is in one place:

> Worktree ready at `.claude/worktrees/<branch-name>/` on branch `<branch-name>` (tracking `origin/main`).
>
> - **Second frontend:** http://localhost:`<port>`/
> - **Backend (shared with primary):** http://localhost:8000
> - **Logs:** `tail -f /tmp/vite-<branch-name>.log`
>
> **To start a second Claude session in it**, open a new terminal and run:
>
> ```
> cd /home/aimfeld/Projects/Python/flawchess/.claude/worktrees/<branch-name>
> claude
> ```
>
> **When you're done**, clean up from the primary worktree:
>
> ```
> fuser -k <port>/tcp
> git worktree remove .claude/worktrees/<branch-name>
> git branch -d <branch-name>   # only after merging
> rm -f /tmp/vite-<branch-name>.log
> ```

## Common issues

- **`fatal: a branch named 'X' already exists`** — handled in preconditions (check #4). Either pick a different name or reuse without `-b`.
- **Vite exits immediately** — `--strictPort` refuses fallback when the port is taken. Check the log and pick another port (5175, 5176, ...).
- **Second frontend loads but `/api` returns 502** — the primary session's backend on `:8000` isn't running. Start `bin/run_local.sh` there.
- **`npm install` complains about peer deps** — run with `--legacy-peer-deps` as a fallback. But first confirm with the user — surprising dependency issues may indicate the primary worktree is on a different branch than `origin/main`.
- **Shared DB gotcha** — both sessions write to the same Docker Postgres. If the primary session runs a migration or a heavy import, the secondary session sees those changes. If they need isolated DB state, this skill is the wrong tool; flag it.
- **You opened Claude in the wrong directory** — both worktrees share the same `CLAUDE.md` through git, but file edits happen in whichever directory Claude was launched. Always `cd` into the worktree before running `claude`.

## Cleanup checklist

When parallel work is done:

1. `fuser -k <port>/tcp` — stop the second Vite
2. `git worktree remove .claude/worktrees/<branch-name>` — remove the working copy (fails if there are uncommitted changes; investigate before using `--force`)
3. `git branch -d <branch-name>` — delete the branch (only after merging; use `-D` only if you're sure the branch contents are disposable)
4. `rm -f /tmp/vite-<branch-name>.log` — drop the log file

Never use `--force` or `-D` as a shortcut past unexpected state — investigate what's there first. The user may have in-progress work you haven't seen.
