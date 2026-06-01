#!/usr/bin/env bash
# Idempotent Stockfish installer for local dev.
#
# Installs the pinned sf_18 release binary for the host platform (SHA-256
# verified) to ~/.local/stockfish/sf. Prod bakes the Linux x86_64 AVX2 build
# into the backend image (see ./Dockerfile), so on Linux this installs that
# identical binary and dev == prod. On macOS it installs the matching sf_18
# macOS build (Apple Silicon or Intel AVX2); eval_cp is not bit-for-bit
# reproducible across CPUs anyway (see the note in app/services/engine.py), so
# a platform-specific binary is fine for dev.
#
# Keep STOCKFISH_TAG and the asset+SHA table below in sync with the ARG defaults
# at the top of ./Dockerfile and the CI install step (.github/workflows/ci.yml)
# when bumping versions.
#
# Re-running is safe: if the pinned version is already installed for this
# platform, the script exits without re-downloading.

set -euo pipefail

STOCKFISH_TAG="sf_18"

# Pick the release asset + its SHA-256 for the host platform. SHAs are of the
# downloaded .tar; recompute with `sha256sum <asset>.tar` after a version bump.
os="$(uname -s)"
arch="$(uname -m)"
case "$os/$arch" in
  Linux/x86_64)
    STOCKFISH_ASSET="stockfish-ubuntu-x86-64-avx2"
    STOCKFISH_SHA256="536c0c2c0cf06450df0bfb5e876ef0d3119950703a8f143627f990c7b5417964"
    ;;
  Darwin/arm64)
    STOCKFISH_ASSET="stockfish-macos-m1-apple-silicon"
    STOCKFISH_SHA256="4d77c4aa3ad9bd1ea8111f2ac5a4620fe7ebf998d6893bf828d49ccd579c8cb0"
    ;;
  Darwin/x86_64)
    STOCKFISH_ASSET="stockfish-macos-x86-64-avx2"
    STOCKFISH_SHA256="41d30e0860ad924a6ceb422c3a36eba43bbe5ae87d3310840da50e71c53f35d9"
    ;;
  *)
    cat >&2 <<EOF
bin/install_stockfish.sh has no pinned Stockfish $STOCKFISH_TAG build for $os/$arch.
Automatically supported: Linux x86_64, macOS (Apple Silicon or Intel).

Install Stockfish manually and set STOCKFISH_PATH in your environment:
  https://stockfishchess.org/download/
EOF
    exit 1
    ;;
esac

INSTALL_DIR="${STOCKFISH_INSTALL_DIR:-$HOME/.local/stockfish}"
BIN_PATH="$INSTALL_DIR/sf"
VERSION_FILE="$INSTALL_DIR/.version"

# Stamp records tag AND asset so switching platforms on the same checkout (or a
# version bump) forces a re-download instead of reusing a wrong-arch binary.
VERSION_STAMP="$STOCKFISH_TAG $STOCKFISH_ASSET"
if [ -x "$BIN_PATH" ] && [ -f "$VERSION_FILE" ] && [ "$(cat "$VERSION_FILE")" = "$VERSION_STAMP" ]; then
  echo "Stockfish $STOCKFISH_TAG ($STOCKFISH_ASSET) already installed at $BIN_PATH"
  exit 0
fi

# Portable download + hash helpers: macOS ships curl + shasum, Linux ships both
# curl/wget and sha256sum. Prefer whichever is present.
if command -v curl >/dev/null 2>&1; then
  download() { curl -fsSL "$1" -o "$2"; }
elif command -v wget >/dev/null 2>&1; then
  download() { wget -q "$1" -O "$2"; }
else
  echo "Error: need 'curl' or 'wget' in PATH." >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  sha256_check() { echo "$1  $2" | sha256sum -c -; }
elif command -v shasum >/dev/null 2>&1; then
  sha256_check() { echo "$1  $2" | shasum -a 256 -c -; }
else
  echo "Error: need 'sha256sum' or 'shasum' in PATH." >&2
  exit 1
fi

if ! command -v tar >/dev/null 2>&1; then
  echo "Error: required command 'tar' not found in PATH." >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "Downloading Stockfish $STOCKFISH_TAG ($STOCKFISH_ASSET)..."
download "https://github.com/official-stockfish/Stockfish/releases/download/${STOCKFISH_TAG}/${STOCKFISH_ASSET}.tar" "$tmp/stockfish.tar"

# Supply-chain integrity check — must match the pinned hash above.
sha256_check "$STOCKFISH_SHA256" "$tmp/stockfish.tar"

tar -xf "$tmp/stockfish.tar" -C "$tmp"
mv "$tmp/stockfish/${STOCKFISH_ASSET}" "$BIN_PATH"
chmod +x "$BIN_PATH"
echo "$VERSION_STAMP" > "$VERSION_FILE"

echo "Installed Stockfish $STOCKFISH_TAG ($STOCKFISH_ASSET) at $BIN_PATH"
