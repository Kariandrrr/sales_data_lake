#!/usr/bin/env bash
# Recreate the four fact "windows" in ClickHouse so that they read the whole
# dt=*/<table>/<table>.parquet tree instead of a single flat file.
#
#   raw.orders, raw.order_items, raw.order_payments, raw.order_reviews
#
# The DDL is taken from SHOW CREATE TABLE, the URL is rewritten from
#   <base>/<table>/<table>.parquet  ->  <base>/dt=*/<table>/<table>.parquet
# and hive_partitioning = 1 is appended.
#
# IMPORTANT: ClickHouse masks the S3 secret key in SHOW CREATE TABLE output as
# '[HIDDEN]'. Copying that DDL verbatim produces a table with the literal
# password "[HIDDEN]" and every query fails with SignatureDoesNotMatch.
# So the secret is re-read from .env and substituted back.
#
# Run from the repo root:
#
#   bash src/scripts/reset-raw-facts.sh                  # dry run, prints DDL
#   bash src/scripts/reset-raw-facts.sh --apply          # drop + recreate
#   bash src/scripts/reset-raw-facts.sh --apply --force  # also redo already-partitioned tables
#
set -euo pipefail

CH_PASSWORD="${CH_PASSWORD:-clickhouse}"
FACT_TABLES="orders order_items order_payments order_reviews"
APPLY=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --force) FORCE=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

ch() {
  docker exec -i clickhouse-lakehouse \
    clickhouse-client --password "$CH_PASSWORD" "$@"
}

# --- MinIO secret: .env first, then environment -----------------------------
env_value() {
  grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- |
    sed "s/^[\"']//; s/[\"']$//"
}

SECRET=""
for key in MINIO_SECRET_KEY MINIO_ROOT_PASSWORD MINIO_PASSWORD; do
  [[ -n "${!key:-}" ]] && { SECRET="${!key}"; break; }
  val=$(env_value "$key" || true)
  [[ -n "$val" ]] && { SECRET="$val"; break; }
done

if [[ -z "$SECRET" ]]; then
  echo "!! cannot find the MinIO secret key (looked for MINIO_SECRET_KEY /" >&2
  echo "   MINIO_ROOT_PASSWORD / MINIO_PASSWORD in .env and in the environment)" >&2
  echo "   run: MINIO_SECRET_KEY=... bash $0 $*" >&2
  exit 1
fi
if [[ "$SECRET" == *"|"* || "$SECRET" == *"&"* ]]; then
  echo "!! secret contains | or &, sed would mangle it. Set MINIO_SECRET_KEY and" >&2
  echo "   edit the script to use python instead of sed." >&2
  exit 1
fi

for t in $FACT_TABLES; do
  echo "=== raw.$t ==="

  ddl=$(ch --query "SHOW CREATE TABLE raw.$t FORMAT TSVRaw" | tr -d '\r')
  url=$(printf '%s' "$ddl" | grep -oE "http://[^']+" | head -1)
  echo "old url: $url"

  already=0
  case "$url" in
    */dt=*/"$t"/"$t".parquet) base="${url%/dt=*/"$t"/"$t".parquet}"; already=1 ;;
    */"$t"/"$t".parquet)      base="${url%/"$t"/"$t".parquet}" ;;
    *)
      echo "!! unexpected url, refusing to guess. Fix raw.$t by hand." >&2
      exit 1
      ;;
  esac

  if [[ $already -eq 1 && $FORCE -eq 0 ]]; then
    echo "already partitioned, skipping (use --force to rebuild)"
    continue
  fi

  new_url="$base/dt=*/$t/$t.parquet"
  echo "new url: $new_url"

  new_ddl=$(printf '%s' "$ddl" |
    sed -E "s#${url}#${new_url}#; s#'Parquet'\)#'Parquet', hive_partitioning = 1)#" |
    sed "s|'\[HIDDEN\]'|'${SECRET}'|g")

  if [[ $APPLY -eq 0 ]]; then
    # never print the real secret
    printf '%s\n\n' "${new_ddl//$SECRET/[HIDDEN]}"
    continue
  fi

  ch --query "DROP TABLE IF EXISTS raw.$t"
  printf '%s\n' "$new_ddl" | ch --multiquery
  # Before the re-extract there is nothing to read yet, so a 404 here is fine
  # and must not abort the loop.
  ch --query "SELECT '$t' AS table, count() AS rows FROM raw.$t FORMAT PrettyCompact" \
    || echo "   (no parquet at this path yet — expected until the extract runs)"
done

if [[ $APPLY -eq 0 ]]; then
  echo "dry run — secret resolved from .env ($(printf '%s' "$SECRET" | wc -c) chars)"
  echo "re-run with --apply to drop and recreate"
fi
