import hashlib

import pandas as pd

from clients import write_parquet, read_parquet


def hash_pii(val: str) -> str:
    if pd.isna(val):
        return val
    return hashlib.sha256(str(val).encode()).hexdigest()[:16]


print("--- Starting silver layer transformation ---")

print("1. Cleaning orders...")
df_orders = read_parquet("bronze/orders/orders.parquet")

timestamp_cols = ["order_purchase_timestamp", "order_approved_at"]
for col in timestamp_cols:
    df_orders[col] = pd.to_datetime(df_orders[col], errors="coerce")

df_orders = df_orders.dropna(subset=["order_purchase_timestamp"])
write_parquet("silver/orders/orders.parquet", df_orders)

print("2. Deduplicating and masking PII...")
df_customers = read_parquet("bronze/customers/customers.parquet")

df_customers = df_customers.drop_duplicates(subset=["customer_id"])

df_customers["customer_zip_code_prefix"] = df_customers[
    "customer_zip_code_prefix"
].apply(hash_pii)
df_customers["customer_city"] = df_customers["customer_city"].str.title().str.strip()

write_parquet("silver/customers/customers.parquet", df_customers)

print("3. Deduplicating order items...")
df_items = read_parquet("bronze/order_items/order_items.parquet")
df_items = df_items.drop_duplicates(subset=["order_id", "order_item_id"])

df_items = df_items[(df_items["price"] >= 0) & (df_items["freight_value"] >= 0)]

write_parquet("silver/order_items/order_items.parquet", df_items)

print("4. Deduplicating order payments...")
df_payments = read_parquet("bronze/order_payments/order_payments.parquet")
df_payments = df_payments.drop_duplicates(subset=["order_id", "payment_sequential"])
write_parquet("silver/order_payments/order_payments.parquet", df_payments)

print("5. Deduplicating order reviews...")
df_reviews = read_parquet("bronze/order_reviews/order_reviews.parquet")
df_reviews = df_reviews.drop_duplicates(subset=["review_id"])

write_parquet("silver/order_reviews/order_reviews.parquet", df_reviews)

print("6. Processing category translation...")
df_trans = read_parquet(
    "bronze/product_category_name_translation/product_category_name_translation.parquet"
)

missing_translations = pd.DataFrame(
    [
        {
            "product_category_name": "pc_gamer",
            "product_category_name_english": "pc_gamer",
        },
        {
            "product_category_name": "portateis_cozinha_e_preparadores_de_alimentos",
            "product_category_name_english": "portable_kitchen_and_food_preparers",
        },
    ]
)

df_trans = pd.concat([df_trans, missing_translations]).drop_duplicates(
    subset=["product_category_name"]
)

write_parquet(
    "silver/product_category_name_translation/product_category_name_translation.parquet",
    df_trans,
)

print("7. Cleaning products...")
df_products = read_parquet("bronze/products/products.parquet")
df_products = df_products.drop_duplicates(subset=["product_id"])
df_products["product_category_name"] = df_products["product_category_name"].fillna(
    "unknown"
)

write_parquet("silver/products/products.parquet", df_products)

print("8. Cleaning sellers...")
df_sellers = read_parquet("bronze/sellers/sellers.parquet")
df_sellers = df_sellers.drop_duplicates(subset=["seller_id"])
df_sellers["seller_city"] = df_sellers["seller_city"].str.title().str.strip()

write_parquet("silver/sellers/sellers.parquet", df_sellers)

print("--- Silver transformation completed successfully! ---")
