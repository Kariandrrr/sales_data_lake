import hashlib
import io

import pandas as pd

from utils.create_s3_client import BUCKET_NAME, s3_client


def read_parquet(key: str) -> pd.DataFrame:
    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    return pd.read_parquet(io.BytesIO(obj["Body"].read()))


def write_parquet(key: str, df: pd.DataFrame):
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)
    s3_client.upload_fileobj(buffer, BUCKET_NAME, key)


def hash_pii(val: str) -> str:
    if pd.isna(val):
        return val
    return hashlib.sha256(str(val).encode()).hexdigest()[:16]


print("--- Starting silver layer transformation ---")

# 1. Orders
print("1. Cleaning orders...")
# FIX: Исправлена опечатка в имени файла (orders.parquet)
df_orders = read_parquet("bronze/orders/orders.parquet")

timestamp_cols = ["order_purchase_timestamp", "order_approved_at"]
for col in timestamp_cols:
    df_orders[col] = pd.to_datetime(df_orders[col], errors="coerce")

df_orders = df_orders.dropna(subset=["order_purchase_timestamp"])
write_parquet("silver/orders/orders.parquet", df_orders)

# 2. Customers
print("2. Deduplicating and masking PII...")
df_customers = read_parquet("bronze/customers/customers.parquet")

df_customers = df_customers.drop_duplicates(subset=["customer_id"])

df_customers["customer_zip_code_prefix"] = df_customers[
    "customer_zip_code_prefix"
].apply(hash_pii)
df_customers["customer_city"] = df_customers["customer_city"].str.title().str.strip()

write_parquet("silver/customers/customers.parquet", df_customers)

# 3. Order Items
print("3. Deduplicating order items...")
df_items = read_parquet("bronze/order_items/order_items.parquet")
df_items = df_items.drop_duplicates(subset=["order_id", "order_item_id"])

# FIX: Исправлено условие для freight_value с <= 0 на >= 0
df_items = df_items[(df_items["price"] >= 0) & (df_items["freight_value"] >= 0)]

write_parquet("silver/order_items/order_items.parquet", df_items)

# 4. Order Payments
print("4. Deduplicating order payments...")
df_payments = read_parquet("bronze/order_payments/order_payments.parquet")
df_payments = df_payments.drop_duplicates(subset=["order_id", "payment_sequential"])
write_parquet("silver/order_payments/order_payments.parquet", df_payments)

# 5. Order Reviews
print("5. Deduplicating order reviews...")
df_reviews = read_parquet("bronze/order_reviews/order_reviews.parquet")
df_reviews = df_reviews.drop_duplicates(subset=["review_id"])

write_parquet("silver/order_reviews/order_reviews.parquet", df_reviews)

# 6. Category Translation
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

# FIX: Выровнен целевой путь S3 с подпапкой
write_parquet(
    "silver/product_category_name_translation/product_category_name_translation.parquet",
    df_trans,
)

print("--- Silver transformation completed successfully! ---")
