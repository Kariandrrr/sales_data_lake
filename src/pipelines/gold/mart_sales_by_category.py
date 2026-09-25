from .load_silver_datasets import df_sales_base
from ...clients import write_parquet

print("Building data mart...")

mart_category = (
    df_sales_base.groupby("product_category_name_english")
    .agg(
        total_orders=("order_id", "nunique"),
        total_items_sold=("order_item_id", "count"),
        total_revenue=("price", "sum"),
        total_freight=("freight_value", "sum"),
        avg_item_price=("price", "mean"),
    )
    .reset_index()
    .sort_values(by="total_orders", ascending=False)
)
write_parquet("gold/marts/mart_sales_by_category.parquet", mart_category)
print(f"✓ Saved 'mart_sales_by_category' ({len(mart_category)} rows).")
