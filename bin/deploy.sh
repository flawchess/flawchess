#!/usr/bin/env bash
set -euo pipefail

# Deploy to production via GitHub Actions (runs CI tests first, then deploys).
# GitLab Flow: deploys the `production` branch, NOT `main`. Promote releases by
# merging main (or a hotfix) into `production` first, then run this.
# Usage: bin/deploy.sh

echo "Uploading .prod.env to server..."
scp .prod.env flawchess:/opt/flawchess/.env

echo "Triggering deploy workflow on production..."
gh workflow run CI --ref production --field deploy=true

echo "Waiting for workflow to start..."
sleep 3

# Get the latest run ID
RUN_ID=$(gh run list --workflow=CI --branch=production --event=workflow_dispatch --limit=1 --json databaseId --jq '.[0].databaseId')

if [ -z "$RUN_ID" ]; then
  echo "Could not find workflow run. Check manually: gh run list --workflow=CI"
  exit 1
fi

echo "Watching run $RUN_ID..."
echo "  https://github.com/$(gh repo view --json nameWithOwner --jq '.nameWithOwner')/actions/runs/$RUN_ID"
echo ""

gh run watch "$RUN_ID"
