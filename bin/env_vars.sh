#!/bin/bash

# Shared environment variables for the other bash scripts

# Application information
APP_NAME="FlawChess"

# Environment files
DEV_ENV_FILE=".env"
PROD_ENV_FILE=".prod.env"

# 1Password configuration
ONEPASSWORD_VAULT="FlawChess"
ONEPASSWORD_DEV_TITLE="$APP_NAME $DEV_ENV_FILE"
ONEPASSWORD_PROD_TITLE="$APP_NAME $PROD_ENV_FILE"

