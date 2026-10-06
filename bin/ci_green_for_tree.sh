#!/usr/bin/env bash
set -euo pipefail

# Succeeds (prints the matching run's head SHA) when a successful CI run
# (.github/workflows/ci.yml) exists for a commit whose TREE is identical to the
# given commit's tree. Exits 1 otherwise.
#
# Why trees, not SHAs: a release is a squash-merge of the main → production PR,
# so the production commit is a NEW SHA that CI never saw — but its tree is the
# exact tree the release PR's CI run just tested (production is forward-ported
# into main after every release, so the PR merge ref equals main's tree).
# Matching on the tree lets the deploy skip a byte-identical second test run
# without ever shipping code that has not passed CI.
#
# Used by bin/deploy.sh (preflight, falls back to a full CI run) and by
# .github/workflows/deploy.yml (the authoritative gate before SSH).
#
# Usage: bin/ci_green_for_tree.sh <commit-sha>

# How many recent successful CI runs to compare against. A release PR's run is
# at most a few dozen runs old (Renovate PRs included).
RUN_LOOKBACK=50

TARGET_SHA="${1:?usage: $0 <commit-sha>}"
REPO="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"

tree_of() {
  gh api "repos/${REPO}/commits/$1" --jq '.commit.tree.sha'
}

TARGET_TREE=$(tree_of "$TARGET_SHA")

# Newest first; dedupe SHAs (a commit can have several green runs) while keeping order.
CANDIDATES=$(gh run list --repo "$REPO" --workflow=ci.yml --status=success \
  --limit="$RUN_LOOKBACK" --json headSha --jq '.[].headSha' | awk '!seen[$0]++')

for sha in $CANDIDATES; do
  if [ "$(tree_of "$sha")" = "$TARGET_TREE" ]; then
    echo "$sha"
    exit 0
  fi
done

exit 1
