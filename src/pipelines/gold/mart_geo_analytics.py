from clients import write_parquet
from load_silver_datasets import df_sales_base

mart_geo = (
    df_sales_base.groupby(["customer_state", "customer_city"])
    .agg(
        total_orders=("order_id", "nunique"),
        unique_customers=("customer_id", "nunique"),
        total_spent=("total_value", "sum"),
        avg_freiht_cost=("freight_value", "mean"),
    )
    .reset_index()
    .sort_values(by="total_spent", ascending=False)
)

write_parquet("gold/marts/mart_geo_analytics.parquet", mart_geo)
print(f"✓ Saved 'mart_geo_analytics' ({len(mart_geo)} rows).")
