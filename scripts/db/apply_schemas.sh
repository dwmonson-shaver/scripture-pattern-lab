#!/usr/bin/env bash
# Apply every data/schemas/*.sql file to the database in lexical order.
# Idempotent: each schema uses CREATE ... IF NOT EXISTS so re-running is a no-op.
# Exits non-zero if DATABASE_URL is unset (loud failure beats a silent fallback).

set -euo pipefail

# Run from repo root regardless of where the script is invoked from.
cd "$(git rev-parse --show-toplevel)"

# Load .env if present so DATABASE_URL is available when the user has not exported it.
if [ -f .env ] && [ -z "${DATABASE_URL:-}" ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required (export it or set it in .env)." >&2
  exit 1
fi

SCHEMA_DIR="data/schemas"
shopt -s nullglob
schema_files=("$SCHEMA_DIR"/*.sql)
shopt -u nullglob

if [ "${#schema_files[@]}" -eq 0 ]; then
  echo "No schema files found in $SCHEMA_DIR/." >&2
  exit 1
fi

for sql_file in "${schema_files[@]}"; do
  echo "Applying $sql_file ..."
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$sql_file"
done

echo
echo "Schemas applied: ${#schema_files[@]} file(s)."
