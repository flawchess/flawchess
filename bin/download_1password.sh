#!/bin/bash

# This script downloads the env files from 1Password if they don't exist locally.

# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

# Source shared environment variables
source "$(dirname "$0")/env_vars.sh"

# Download .dev.env if file doesn't exist
if [ ! -f "$DEV_ENV_FILE" ]; then
  echo "Fetching $DEV_ENV_FILE from 1Password..."
  op document get "$ONEPASSWORD_DEV_TITLE" --vault "$ONEPASSWORD_VAULT" > "$DEV_ENV_FILE"
  echo "Downloaded $DEV_ENV_FILE from 1Password."
else
  echo "$DEV_ENV_FILE already exists. Skipping download."
fi

# Download .prod.env if file doesn't exist
if [ ! -f "$PROD_ENV_FILE" ]; then
  echo "Fetching $PROD_ENV_FILE from 1Password..."
  op document get "$ONEPASSWORD_PROD_TITLE" --vault "$ONEPASSWORD_VAULT" > "$PROD_ENV_FILE"
  echo "Downloaded $PROD_ENV_FILE from 1Password."
else
  echo "$PROD_ENV_FILE already exists. Skipping download."
fi
