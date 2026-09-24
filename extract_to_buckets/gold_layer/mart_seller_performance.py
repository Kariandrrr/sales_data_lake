from load_silver_datasets import df_sales_base
from utils.parquet_functions import write_parquet

mart_sellers = (
    df_sales_base.groupby("seller_id")
    .agg(
        total_orders_fulfilled=("order_id", "nunique"),
        total_items_sold=("order_item_id", "count"),
        total_gross_revenue=("price", "sum"),
        avg_order_value=("order_purchase_timestamp", "min"),
        active_to_date=("order_purchase_timestamp", "max"),
    )
    .reset_index()
    .sort_values(by="total_gross_revenue", ascending=False)
)

write_parquet("gold/marts/mart_seller_performance.parquet", mart_sellers)
print(f"✓ Saved 'mart_seller_performance' ({len(mart_sellers)} rows).")
