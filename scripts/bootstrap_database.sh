#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
database_name="${FINVIEW_DB_NAME:-finview}"
database_owner="${FINVIEW_DB_OWNER:-$(id -un)}"

if ! sudo -n -u postgres psql -p 5432 -Atqc \
    "SELECT 1 FROM pg_roles WHERE rolname = '${database_owner}'" | grep -qx 1; then
    sudo -n -u postgres createuser -p 5432 "$database_owner"
fi

if ! sudo -n -u postgres psql -p 5432 -Atqc \
    "SELECT 1 FROM pg_database WHERE datname = '${database_name}'" | grep -qx 1; then
    sudo -n -u postgres createdb -p 5432 --owner="$database_owner" "$database_name"
fi

psql -p 5432 -d "$database_name" -v ON_ERROR_STOP=1 \
    -f "$project_dir/backend/schema.sql"

echo "Database ${database_name} is ready for ${database_owner}."
