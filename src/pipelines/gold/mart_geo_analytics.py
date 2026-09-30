from . import load_sales_base
from ...clients import write_parquet


def build_mart_by_geo() -> None:
    mart_geo = (
        load_sales_base()
        .groupby(["customer_state", "customer_city"])
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


if __name__ == "__main__":
    build_mart_by_geo()
