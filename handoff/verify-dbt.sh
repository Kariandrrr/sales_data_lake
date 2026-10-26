set -u
CH() { docker exec -i clickhouse-lakehouse clickhouse-client --password clickhouse --query "$1" 2>&1; }
ok() { printf '  [ OK ]  %s\n' "$1"; }
bad() { printf '  [FAIL]  %s\n' "$1"; }
hr() { printf '\n=== %s ===\n' "$1"; }

FAILS=0

hr "1. Columns with a dot in the name (sign of a stale old model version)"
DOTTED=$(CH "SELECT count() FROM system.columns
             WHERE database IN ('silver','gold') AND name LIKE '%.%'")
echo "  found: $DOTTED"
if [ "$DOTTED" = "0" ]; then ok "no dotted names"; else bad "columns like i.order_id exist — rebuild them with --full-refresh"; FAILS=$((FAILS+1)); fi

hr "2. Objects in silver and gold"
CH "SELECT database, count() AS tables, sum(total_rows) AS rows
    FROM system.tables WHERE database IN ('silver','gold')
    GROUP BY database ORDER BY database FORMAT PrettyCompact"

S=$(CH "SELECT count() FROM system.tables WHERE database='silver'")
G=$(CH "SELECT count() FROM system.tables WHERE database='gold'")
[ "$S" = "9" ] && ok "silver: 9 tables" || { bad "silver: $S tables, expected 9"; FAILS=$((FAILS+1)); }
[ "$G" = "3" ] && ok "gold: 3 tables"   || { bad "gold: $G tables, expected 3";   FAILS=$((FAILS+1)); }

hr "3. Rows in key tables (Olist order of magnitude)"
CH "SELECT 'stg_ch__orders'      t, count() n FROM silver.stg_ch__orders
    UNION ALL SELECT 'stg_ch__order_items', count() FROM silver.stg_ch__order_items
    UNION ALL SELECT 'stg_ch__customers',   count() FROM silver.stg_ch__customers
    UNION ALL SELECT 'int_sales_base',      count() FROM silver.int_sales_base
    UNION ALL SELECT 'gold_mart_category',  count() FROM gold.mart_sales_by_category
    UNION ALL SELECT 'gold_mart_geo',       count() FROM gold.mart_geo_analytics
    UNION ALL SELECT 'gold_mart_seller',    count() FROM gold.mart_seller_performance
    FORMAT PrettyCompact"

EMPTY=$(CH "SELECT count() FROM (
              SELECT count() c FROM silver.stg_ch__orders
              UNION ALL SELECT count() FROM silver.int_sales_base
              UNION ALL SELECT count() FROM gold.mart_sales_by_category) WHERE c = 0")
[ "$EMPTY" = "0" ] && ok "no empty tables" || { bad "empty tables found"; FAILS=$((FAILS+1)); }

hr "4. What the marts contain (eyeball check)"
CH "SELECT * FROM gold.mart_sales_by_category ORDER BY total_revenue DESC LIMIT 3 FORMAT PrettyCompact"

hr "5. Old VIEWs in default — still alive? (drop only after Metabase)"
CH "SELECT name FROM system.tables WHERE database='default' FORMAT PrettyCompact"

printf '\n=========================================\n'
if [ "$FAILS" = "0" ]; then
  printf 'RESULT: all good. Next — Metabase and reconciliation.\n'
else
  printf 'RESULT: problems: %s. See MEMORY.md.\n' "$FAILS"
fi
printf '=========================================\n'