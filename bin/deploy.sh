#!/usr/bin/env bash
set -euo pipefail

# Deploy to production via GitHub Actions.
#
# Tests are not re-run when a successful CI run already exists for the exact
# tree being deployed (normally the main → production release PR's run, see
# bin/ci_green_for_tree.sh). Otherwise this runs CI (ci.yml) on production
# first and only deploys if it passes. The deploy itself is deploy.yml, which
# re-checks the same green-tree gate server-side before touching the server.
#
# GitLab Flow: this ALWAYS deploys the `production` branch, regardless of which
# branch your working tree is currently on. `main` is the integration trunk and
# is never deployed directly. Promote a release by merging main (or a hotfix)
# into `production` first, then run this.
#
# History: on 2026-05-16 an earlier version hardcoded `--ref main`. Because this
# script runs from the operator's local working tree (usually a `main`
# checkout), the GitLab-Flow fix that lived only on the `production` branch
# never executed, and a deploy silently shipped unreleased `main` to prod. The
# hard assertion below makes that class of mistake impossible to repeat
# silently: it aborts unless the dispatched run is actually on `production` at
# the expected commit.
#
# Usage: bin/deploy.sh

DEPLOY_BRANCH="production"

echo "Fetching origin/${DEPLOY_BRANCH}..."
git fetch origin --quiet "$DEPLOY_BRANCH"
TARGET_SHA=$(git rev-parse "origin/${DEPLOY_BRANCH}")
echo "  target commit: $(git log -1 --format='%h %s' "origin/${DEPLOY_BRANCH}")"

# Dispatch a workflow on production@TARGET_SHA and watch it to completion.
# Waits for a run NEWER than any existing one: matching on SHA alone would pick
# up an earlier run at the same commit (e.g. a retry) before the new one registers.
dispatch_and_watch() {
  local workflow="$1"
  local prev_id run_id="" run_branch run_sha
  prev_id=$(gh run list --workflow="$workflow" --limit=1 --json databaseId --jq '.[0].databaseId // 0')

  echo "Triggering ${workflow} on ${DEPLOY_BRANCH}..."
  # Reference the workflow by filename (not display name) and pass an explicit
  # --ref so dispatch targets the production branch deterministically.
  gh workflow run "$workflow" --ref "$DEPLOY_BRANCH"

  echo "Waiting for the run to register..."
  for _ in $(seq 1 15); do
    sleep 2
    run_id=$(gh run list --workflow="$workflow" --branch="$DEPLOY_BRANCH" \
      --event=workflow_dispatch --limit=5 \
      --json databaseId,headSha --jq \
      "[.[] | select(.headSha == \"${TARGET_SHA}\" and .databaseId > ${prev_id})][0].databaseId // empty")
    [ -n "$run_id" ] && break
  done

  if [ -z "$run_id" ]; then
    echo "ERROR: no ${workflow} workflow_dispatch run found on '${DEPLOY_BRANCH}' at ${TARGET_SHA:0:7}." >&2
    echo "       Aborting rather than risk deploying the wrong branch." >&2
    echo "       Check manually: gh run list --workflow=${workflow}" >&2
    exit 1
  fi

  # Hard guard: never watch/trust a run that isn't production@TARGET_SHA.
  run_branch=$(gh run view "$run_id" --json headBranch --jq '.headBranch')
  run_sha=$(gh run view "$run_id" --json headSha --jq '.headSha')
  if [ "$run_branch" != "$DEPLOY_BRANCH" ] || [ "$run_sha" != "$TARGET_SHA" ]; then
    echo "ERROR: dispatched run is ${run_branch}@${run_sha:0:7}, expected" >&2
    echo "       ${DEPLOY_BRANCH}@${TARGET_SHA:0:7}. Aborting deploy." >&2
    exit 1
  fi

  echo "Watching ${workflow} run $run_id (${DEPLOY_BRANCH}@${TARGET_SHA:0:7})..."
  echo "  https://github.com/$(gh repo view --json nameWithOwner --jq '.nameWithOwner')/actions/runs/$run_id"
  echo ""
  gh run watch "$run_id" --exit-status
}

echo "Looking for a green CI run on the same tree..."
if GREEN_SHA=$(bin/ci_green_for_tree.sh "$TARGET_SHA"); then
  echo "  CI already passed on ${GREEN_SHA:0:7} (identical tree). Skipping the test run."
else
  echo "  none found (e.g. a hotfix, or production diverged from main). Running CI first."
  dispatch_and_watch ci.yml
fi

echo "Uploading .prod.env to server..."
scp .prod.env flawchess:/opt/flawchess/.env

dispatch_and_watch deploy.yml

# Final safety net: confirm the server actually landed on the expected commit.
echo ""
echo "Verifying production server commit..."
SERVER_SHA=$(ssh flawchess "cd /opt/flawchess && git rev-parse HEAD")
if [ "$SERVER_SHA" != "$TARGET_SHA" ]; then
  echo "ERROR: server is at ${SERVER_SHA:0:7}, expected ${TARGET_SHA:0:7}." >&2
  echo "       Deploy did not converge — investigate before relying on prod." >&2
  exit 1
fi
echo "Production is at $(ssh flawchess "cd /opt/flawchess && git log -1 --format='%h %s'")"

# Forward-port: record the release squash commit as merged into main so the
# NEXT release PR doesn't conflict. Without this, GitHub can't even start the
# pull_request CI run on the next release PR ("no checks reported"), because a
# conflicted PR has no buildable merge ref. See CLAUDE.md § Version Control.
#
# `-s ours` keeps main's tree byte-for-byte and only records ancestry. That is
# only unconditionally safe when main's tree is IDENTICAL to production's —
# the normal case when deploying right after merging the release PR. If the
# trees differ (main moved ahead, or a hotfix landed on production that main
# doesn't have), an automatic `-s ours` could silently bury real differences,
# so we skip and tell the operator what to verify and run.
echo ""
echo "Forward-porting ${DEPLOY_BRANCH} merge commit into main..."
git fetch origin main --quiet
if git merge-base --is-ancestor "origin/${DEPLOY_BRANCH}" origin/main; then
  echo "  already reconciled (${DEPLOY_BRANCH} is an ancestor of main)."
elif [ "$(git rev-parse "origin/${DEPLOY_BRANCH}^{tree}")" != "$(git rev-parse "origin/main^{tree}")" ]; then
  echo "  SKIPPED: main and ${DEPLOY_BRANCH} trees differ (main moved ahead, or a"
  echo "  hotfix landed on ${DEPLOY_BRANCH} that main lacks). Verify ${DEPLOY_BRANCH}"
  echo "  has no unique code, then run on a clean main checkout:"
  echo "    git merge -s ours origin/${DEPLOY_BRANCH} && git push origin main"
elif [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ] || [ -n "$(git status --porcelain)" ]; then
  echo "  SKIPPED: need a clean working tree on main. Run manually:"
  echo "    git merge -s ours origin/${DEPLOY_BRANCH} && git push origin main"
else
  git pull --ff-only --quiet origin main
  git merge -s ours "origin/${DEPLOY_BRANCH}" \
    -m "chore(release): forward-port ${DEPLOY_BRANCH} merge commit (keep main's tree)"
  git push origin main
  echo "  forward-port pushed to main."
fi
