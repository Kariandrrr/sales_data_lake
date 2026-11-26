#!/usr/bin/env bash
# Apply the checked-in raw.* DDL, substituting MinIO credentials from .env.
#
#   bash src/scripts/apply-raw-ddl.sh                       # into the raw schema
#   bash src/scripts/apply-raw-ddl.sh --schema raw_check    # into a throwaway schema
#   bash src/scripts/apply-raw-ddl.sh --dry-run             # print SQL, change nothing
#
# The __MINIO_ACCESS_KEY__ / __MINIO_SECRET_KEY__ placeholders are replaced with
# MINIO_ACCESS_KEY / MINIO_SECRET_KEY, or MINIO_ROOT_USER / MINIO_ROOT_PASSWORD.
# Values are taken from the environment first, then from .env in the repo root.
#
# Note: the DDL uses CREATE TABLE IF NOT EXISTS, so an existing table with a
# different definition is left untouched. To force a rebuild, drop the table
# first — see src/scripts/reset-raw-facts.sh.
set -euo pipefail

CH_CONTAINER="${CH_CONTAINER:-clickhouse-lakehouse}"
CH_PASSWORD="${CH_PASSWORD:-clickhouse}"
FILE="${FILE:-dbt_lake/sql/clickhouse_raw_s3_tables.sql}"
SCHEMA="raw"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --schema)  SCHEMA="$2";  shift 2 ;;
    --file)    FILE="$2";    shift 2 ;;
    --dry-run) DRY_RUN=1;    shift ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$FILE" ]] || { echo "missing $FILE — run src/scripts/dump-raw-ddl.sh first" >&2; exit 1; }

env_value() {
  grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- |
    sed "s/^[\"']//; s/[\"']\$//"
}

pick() {
  local name v
  for name in "$@"; do
    if [[ -n "${!name:-}" ]]; then printf '%s' "${!name}"; return 0; fi
    v=$(env_value "$name" || true)
    if [[ -n "$v" ]]; then printf '%s' "$v"; return 0; fi
  done
  return 1
}

ACCESS=$(pick MINIO_ACCESS_KEY MINIO_ROOT_USER) || {
  echo "MINIO_ACCESS_KEY (or MINIO_ROOT_USER) not found in the environment or .env" >&2
  exit 1
}
SECRET=$(pick MINIO_SECRET_KEY MINIO_ROOT_PASSWORD) || {
  echo "MINIO_SECRET_KEY (or MINIO_ROOT_PASSWORD) not found in the environment or .env" >&2
  exit 1
}

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

python3 - "$FILE" "$ACCESS" "$SECRET" "$SCHEMA" >"$tmp" <<'PY'
import sys
import pathlib

path, access, secret, schema = sys.argv[1:5]
sql = pathlib.Path(path).read_text()
sql = sql.replace("__MINIO_ACCESS_KEY__", access)
sql = sql.replace("__MINIO_SECRET_KEY__", secret)
if schema != "raw":
    sql = sql.replace("raw.", f"{schema}.")
sys.stdout.write(sql)
PY

tables=$(grep -c 'CREATE TABLE' "$tmp" || true)
echo "file:   $FILE"
echo "schema: $SCHEMA"
echo "access: ${ACCESS:0:3}***  secret: *** (${#SECRET} chars)"
echo "tables: $tables"

if [[ $DRY_RUN -eq 1 ]]; then
  sed "s/$(printf '%s' "$SECRET" | sed 's/[&/\]/\\&/g')/***/g" "$tmp"
  exit 0
fi

docker exec -i "$CH_CONTAINER" clickhouse-client --password "$CH_PASSWORD" --multiquery <"$tmp"
echo "applied"
