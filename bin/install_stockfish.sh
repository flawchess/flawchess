#!/usr/bin/env bash
# Idempotent Stockfish installer for local dev.
#
# Mirrors the install steps in the prod Dockerfile (same release tag, same
# AVX2 binary, same SHA-256 verification) so dev and prod run an identical
# engine. Keep STOCKFISH_TAG / STOCKFISH_ASSET / STOCKFISH_SHA256 in sync
# with the ARG defaults at the top of ./Dockerfile when bumping versions.
#
# Re-running is safe: if the pinned version is already installed, this
# script exits without re-downloading.

set -euo pipefail

STOCKFISH_TAG="sf_18"
STOCKFISH_ASSET="stockfish-ubuntu-x86-64-avx2"
STOCKFISH_SHA256="536c0c2c0cf06450df0bfb5e876ef0d3119950703a8f143627f990c7b5417964"

INSTALL_DIR="${STOCKFISH_INSTALL_DIR:-$HOME/.local/stockfish}"
BIN_PATH="$INSTALL_DIR/sf"
VERSION_FILE="$INSTALL_DIR/.version"

# Prod ships the Linux x86_64 AVX2 build. To keep dev == prod we install the
# same binary; other platforms get a clear pointer rather than the wrong build.
if [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "x86_64" ]; then
  cat >&2 <<EOF
bin/install_stockfish.sh downloads the Linux x86_64 AVX2 build to match prod.
Detected $(uname -s)/$(uname -m), which is not supported by this script.

Install Stockfish manually and set STOCKFISH_PATH in your environment:
  macOS:   brew install stockfish && export STOCKFISH_PATH=\$(command -v stockfish)
  Other:   https://stockfishchess.org/download/
EOF
  exit 1
fi

if [ -x "$BIN_PATH" ] && [ -f "$VERSION_FILE" ] && [ "$(cat "$VERSION_FILE")" = "$STOCKFISH_TAG" ]; then
  echo "Stockfish $STOCKFISH_TAG already installed at $BIN_PATH"
  exit 0
fi

for cmd in wget tar sha256sum; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: required command '$cmd' not found in PATH." >&2
    exit 1
  fi
done

mkdir -p "$INSTALL_DIR"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "Downloading Stockfish $STOCKFISH_TAG ($STOCKFISH_ASSET)..."
wget -q "https://github.com/official-stockfish/Stockfish/releases/download/${STOCKFISH_TAG}/${STOCKFISH_ASSET}.tar" -O "$tmp/stockfish.tar"

# Supply-chain integrity check — must match the hash pinned in ./Dockerfile.
echo "${STOCKFISH_SHA256}  $tmp/stockfish.tar" | sha256sum -c -

tar -xf "$tmp/stockfish.tar" -C "$tmp"
mv "$tmp/stockfish/${STOCKFISH_ASSET}" "$BIN_PATH"
chmod +x "$BIN_PATH"
echo "$STOCKFISH_TAG" > "$VERSION_FILE"

echo "Installed Stockfish $STOCKFISH_TAG at $BIN_PATH"
