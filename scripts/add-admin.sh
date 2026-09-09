#!/usr/bin/env sh
set -eu

EMAIL="${1:-${ADMIN_EMAIL:-}}"
PASSWORD="${2:-${ADMIN_PASSWORD:-}}"

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: scripts/add-admin.sh <email> <password>"
  echo "   or: ADMIN_EMAIL=... ADMIN_PASSWORD=... scripts/add-admin.sh"
  exit 1
fi

docker compose --profile tools run --rm \
  -e ADMIN_EMAIL="$EMAIL" \
  -e ADMIN_PASSWORD="$PASSWORD" \
  create-admin
