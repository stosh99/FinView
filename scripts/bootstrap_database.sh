#!/usr/bin/env bash
# Bring the database named in DATABASE_URL (.env) up to the latest schema.
#
# The finview_prod / finview_dev databases and roles are created once on the
# VPS (see README "Databases"); this script only applies Alembic migrations.
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

alembic_bin="${project_dir}/.venv/bin/alembic"
[ -x "$alembic_bin" ] || alembic_bin="alembic"

"$alembic_bin" upgrade head
"$alembic_bin" current
