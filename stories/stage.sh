#!/usr/bin/env bash
# Stage the publishable part of the stories site: every root file plus the story
# directories listed in stories/published.txt. Used by .github/workflows/pages.yml and
# runnable locally to preview exactly what a push to main would deploy:
#
#     bash stories/stage.sh stories /tmp/site && python3 -m http.server -d /tmp/site
#
# Exits non-zero when index.html or sitemap.xml references a story that is not
# published, so an unlisted story can never be linked from the live site either.
set -euo pipefail

src=${1:?source directory (stories)}
dst=${2:?staging directory}
allowlist="$src/published.txt"

mapfile -t published < <(grep -v '^\s*#' "$allowlist" | sed 's/\s*$//' | grep -v '^$')

rm -rf "$dst"
mkdir -p "$dst"
find "$src" -maxdepth 1 -type f ! -name 'CLAUDE.md' ! -name 'README.md' ! -name 'stage.sh' ! -name 'published.txt' \
  -exec cp {} "$dst/" \;

status=0
for dir in "$src"/*/; do
  slug=$(basename "$dir")
  listed=0
  for p in "${published[@]}"; do [[ "$p" == "$slug" ]] && listed=1; done
  if [[ $listed -eq 1 ]]; then
    [[ -f "$dir/index.html" ]] || { echo "published story '$slug' has no index.html" >&2; status=1; }
    cp -r "$dir" "$dst/$slug"
    echo "publish  $slug"
  else
    if grep -q "$slug/" "$src/index.html" "$src/sitemap.xml"; then
      echo "ERROR: '$slug' is linked from index.html or sitemap.xml but not in published.txt" >&2
      status=1
    fi
    echo "skip     $slug (not in published.txt)"
  fi
done
for p in "${published[@]}"; do
  [[ -d "$src/$p" ]] || { echo "ERROR: published.txt lists '$p' but stories/$p/ does not exist" >&2; status=1; }
done
exit $status
