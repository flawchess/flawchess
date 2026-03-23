#!/usr/bin/env bash
set -euo pipefail

# Deploy to production via GitHub Actions (runs CI tests first, then deploys).
# Usage: bin/deploy.sh

echo "Triggering deploy workflow on main..."
gh workflow run CI --ref main --field deploy=true

echo "Waiting for workflow to start..."
sleep 3

# Get the latest run ID
RUN_ID=$(gh run list --workflow=CI --branch=main --event=workflow_dispatch --limit=1 --json databaseId --jq '.[0].databaseId')

if [ -z "$RUN_ID" ]; then
  echo "Could not find workflow run. Check manually: gh run list --workflow=CI"
  exit 1
fi

echo "Watching run $RUN_ID..."
echo "  https://github.com/$(gh repo view --json nameWithOwner --jq '.nameWithOwner')/actions/runs/$RUN_ID"
echo ""

gh run watch "$RUN_ID"
