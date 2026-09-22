import hashlib
import io

import pandas as pd

from utils.create_s3_client import s3_client, BUCKET_NAME


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

print("1. Cleaning orders...")
df_orders = read_parquet("bronze/orders/order.parquet")

timestamp_cols = ["order_purchase_timestamp", "order_approved_at"]
for col in timestamp_cols:
    df_orders[col] = pd.to_datetime(df_orders[col], errors="coerce")

df_orders = df_orders.dropna(subset=["order_purchase_timestamp"])
write_parquet("silver/orders/orders.parquet", df_orders)

print("2. Deduplicating  and masking PII...")
df_customers = read_parquet("bronze/customers/customers.parquet")

df_customers = df_customers.drop_duplicates(subset="customer_id")

df_customers["customer_zip_code_prefix"] = df_customers[
    "customer_zip_code_prefix"
].apply(hash_pii)
df_customers["customer_city"] = df_customers["customer_city"].str.title().str.strip()

write_parquet("silver/customers/customers.parquet", df_customers)

print("3. Deduplicating order items...")
df_items = read_parquet("bronze/order_items/order_items.parquet")
df_items = df_items.drop_duplicates(subset=["order_id", "order_item_id"])
df_items = df_items[(df_items["price"] >= 0) & (df_items["freight_value"] <= 0)]

write_parquet("silver/order_items/order_items.parquet", df_items)

print("4. Deduplicating order payments...")
df_payments = read_parquet("bronze/order_payments/order_payments.parquet")
df_payments = df_payments.drop_duplicates(subset=["order_id", "payment_sequential"])
write_parquet("silver/order_payments/order_payments.parquet", df_payments)
