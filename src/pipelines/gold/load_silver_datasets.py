from ...clients import read_parquet

print("Loading silver datasets...")

df_orders = read_parquet("silver/orders/orders.parquet")
df_items = read_parquet("silver/order_items/order_items.parquet")
df_customers = read_parquet("silver/customers/customers.parquet")
df_products = read_parquet("silver/products/products.parquet")
df_trans = read_parquet(
    "silver/product_category_name_translation/product_category_name_translation.parquet"
)

df_products_enriched = df_products.merge(
    df_trans, on="product_category_name", how="left"
)

df_products_enriched["product_category_name_english"] = df_products_enriched[
    "product_category_name_english"
].fillna("other")

df_sales_base = (
    df_items.merge(df_orders, on="order_id", how="inner")
    .merge(df_customers, on="customer_id", how="left")
    .merge(df_products_enriched, on="product_id", how="left")
)

df_sales_base["total_value"] = df_sales_base["price"] + df_sales_base["freight_value"]


print("=== Data load finished successfully! ===")
