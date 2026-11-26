#!/usr/bin/env bash
# Dump the actual DDL of raw.* tables from the running ClickHouse into the repo.
#
# Why: the live tables were rebuilt by a one-off script while the checked-in
# clickhouse_raw_s3_tables.sql kept pointing at flat parquet paths. A fresh
# clone would recreate broken tables (Code: 499 / HTTP 404).
#
# What it does:
#   * runs SHOW CREATE TABLE for every raw table;
#   * adds IF NOT EXISTS so the file can be re-applied safely;
#   * drops the dead hive_partitioning flag (not supported on ENGINE = S3);
#   * replaces MinIO credentials with __MINIO_ACCESS_KEY__ / __MINIO_SECRET_KEY__
#     placeholders, so no passwords end up in git;
#   * writes everything to dbt_lake/sql/clickhouse_raw_s3_tables.sql.
#
# Apply the result with src/scripts/apply-raw-ddl.sh.
#
# Run from the repository root:
#   bash src/scripts/dump-raw-ddl.sh            # rewrite the file
#   bash src/scripts/dump-raw-ddl.sh --stdout   # print to stdout only

set -euo pipefail

CH_CONTAINER="${CH_CONTAINER:-clickhouse-lakehouse}"
CH_PASSWORD="${CH_PASSWORD:-clickhouse}"
OUT="${OUT:-dbt_lake/sql/clickhouse_raw_s3_tables.sql}"

TABLES="orders order_items order_payments order_reviews customers products sellers product_category_name_translation"

STDOUT=0
[[ "${1:-}" == "--stdout" ]] && STDOUT=1

ch() {
  docker exec -i "$CH_CONTAINER" clickhouse-client --password "$CH_PASSWORD" -q "$1"
}

emit() {
  cat <<'HEADER'
-- raw.* are windows onto the parquet files in MinIO. No data is copied into ClickHouse.
--
-- GENERATED from the live database by src/scripts/dump-raw-ddl.sh
-- Do not edit by hand: change the live table, then regenerate.
--
-- Facts (orders, order_items, order_payments, order_reviews) read the
-- bronze/dt=*/<table>/<table>.parquet partition tree; dimensions read flat
-- bronze/<table>/<table>.parquet snapshots.
--
-- Credentials are placeholders. Apply this file with
--   bash src/scripts/apply-raw-ddl.sh
HEADER
  echo
  for t in $TABLES; do
    ddl=$(ch "SHOW CREATE TABLE raw.$t FORMAT TSVRaw")
    printf '%s\n' "$ddl" |
      sed -E \
        -e 's/^CREATE TABLE raw\./CREATE TABLE IF NOT EXISTS raw./' \
        -e 's/, hive_partitioning = 1//' \
        -e "s/, '[^']*', '\[HIDDEN\]'/, '__MINIO_ACCESS_KEY__', '__MINIO_SECRET_KEY__'/" \
        -e 's/;[[:space:]]*$//'
    echo ';'
    echo
  done
}

if [[ $STDOUT -eq 1 ]]; then
  emit
  exit 0
fi

mkdir -p "$(dirname "$OUT")"
emit >"$OUT.tmp"
mv "$OUT.tmp" "$OUT"

echo "written: $OUT"
grep -c 'CREATE TABLE' "$OUT" | sed 's/^/tables: /'
echo
echo "review the diff:"
echo "  git diff --stat $OUT"
echo
echo "verify against a throwaway schema:"
echo "  bash src/scripts/apply-raw-ddl.sh --schema raw_check"
