#!/usr/bin/env bash
set -euo pipefail

# Deploy to production via GitHub Actions (runs CI tests first, then deploys).
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

echo "Uploading .prod.env to server..."
scp .prod.env flawchess:/opt/flawchess/.env

echo "Triggering deploy workflow on ${DEPLOY_BRANCH}..."
# Reference the workflow by filename (not display name) and pass an explicit
# --ref so dispatch targets the production branch deterministically.
gh workflow run ci.yml --ref "$DEPLOY_BRANCH" --field deploy=true

echo "Waiting for the run to register..."
RUN_ID=""
for _ in $(seq 1 15); do
  sleep 2
  RUN_ID=$(gh run list --workflow=ci.yml --branch="$DEPLOY_BRANCH" \
    --event=workflow_dispatch --limit=1 \
    --json databaseId,headSha --jq \
    "[.[] | select(.headSha == \"${TARGET_SHA}\")][0].databaseId")
  [ -n "$RUN_ID" ] && break
done

if [ -z "$RUN_ID" ]; then
  echo "ERROR: no workflow_dispatch run found on '${DEPLOY_BRANCH}' at ${TARGET_SHA:0:7}." >&2
  echo "       Aborting rather than risk deploying the wrong branch." >&2
  echo "       Check manually: gh run list --workflow=ci.yml" >&2
  exit 1
fi

# Hard guard: never watch/trust a run that isn't production@TARGET_SHA.
RUN_BRANCH=$(gh run view "$RUN_ID" --json headBranch --jq '.headBranch')
RUN_SHA=$(gh run view "$RUN_ID" --json headSha --jq '.headSha')
if [ "$RUN_BRANCH" != "$DEPLOY_BRANCH" ] || [ "$RUN_SHA" != "$TARGET_SHA" ]; then
  echo "ERROR: dispatched run is ${RUN_BRANCH}@${RUN_SHA:0:7}, expected" >&2
  echo "       ${DEPLOY_BRANCH}@${TARGET_SHA:0:7}. Aborting deploy." >&2
  exit 1
fi

echo "Watching run $RUN_ID (${DEPLOY_BRANCH}@${TARGET_SHA:0:7})..."
echo "  https://github.com/$(gh repo view --json nameWithOwner --jq '.nameWithOwner')/actions/runs/$RUN_ID"
echo ""

gh run watch "$RUN_ID" --exit-status

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
