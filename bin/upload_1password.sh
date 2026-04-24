#!/bin/bash

# This script uploads the env files to 1Password if they exist locally.

# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

# Source shared environment variables
source "$(dirname "$0")/env_vars.sh"

# Upload .dev.env if file exists
if [ -f "$DEV_ENV_FILE" ]; then
  DEV_ENV_ID=$(op item list --vault "$ONEPASSWORD_VAULT" --format json | jq -r --arg title "$ONEPASSWORD_DEV_TITLE" '.[] | select(.title == $title) | .id')
  [ -n "$DEV_ENV_ID" ] && op item delete "$DEV_ENV_ID"
  op document create "$DEV_ENV_FILE" --vault "$ONEPASSWORD_VAULT" --title "$ONEPASSWORD_DEV_TITLE"
  echo "Uploaded $DEV_ENV_FILE to 1Password."
else
  echo "Warning: $DEV_ENV_FILE does not exist. Skipping upload."
fi

# Upload .prod.env if file exists
if [ -f "$PROD_ENV_FILE" ]; then
  PROD_ENV_ID=$(op item list --vault "$ONEPASSWORD_VAULT" --format json | jq -r --arg title "$ONEPASSWORD_PROD_TITLE" '.[] | select(.title == $title) | .id')
  [ -n "$PROD_ENV_ID" ] && op item delete "$PROD_ENV_ID"
  op document create "$PROD_ENV_FILE" --vault "$ONEPASSWORD_VAULT" --title "$ONEPASSWORD_PROD_TITLE"
  echo "Uploaded $PROD_ENV_FILE to 1Password."
else
  echo "Warning: $PROD_ENV_FILE does not exist. Skipping upload."
fi
