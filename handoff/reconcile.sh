# Run on the host:  bash handoff/reconcile.sh

set -u

CH() { docker exec -i clickhouse-lakehouse clickhouse-client --password clickhouse --query "$1"; }

S3() {
  echo "s3('http://minio-lakehouse:9000/lakehouse/gold/marts/$1.parquet','minioadmin','minioadminpassword','Parquet')"
}

printf '%-30s %-12s %8s %16s\n' "MART" "SOURCE" "ROWS" "METRIC"
printf '%s\n' "--------------------------------------------------------------------------"

compare() {
  local table="$1" metric="$2"
  local old new

  old=$(CH "SELECT concat(toString(count()), '|', toString(round(sum($metric), 2))) FROM $(S3 "$table")" 2>/dev/null)
  new=$(CH "SELECT concat(toString(count()), '|', toString(round(sum($metric), 2))) FROM gold.$table" 2>/dev/null)

  printf '%-30s %-12s %8s %16s\n' "$table" "old_parquet" "${old%%|*}" "${old##*|}"
  printf '%-30s %-12s %8s %16s\n' "" "new_dbt" "${new%%|*}" "${new##*|}"

  if [ "$old" = "$new" ]; then
    printf '%-30s %s\n\n' "" "MATCH"
  else
    printf '%-30s %s\n\n' "" "!!! MISMATCH"
  fi
}

compare mart_sales_by_category    total_revenue
compare mart_geo_analytics        total_spent
compare mart_seller_performance   total_gross_revenue

echo "=== Columns: old (parquet) vs new (dbt) ==="
for t in mart_sales_by_category mart_geo_analytics mart_seller_performance; do
  echo "--- $t"
  echo "old: $(CH "DESCRIBE TABLE $(S3 "$t")" 2>/dev/null | cut -f1 | sort | tr '\n' ' ')"
  echo "new: $(CH "SELECT name FROM system.columns WHERE database='gold' AND table='$t' ORDER BY name" 2>/dev/null | sort | tr '\n' ' ')"
  echo
done