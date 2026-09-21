import hashlib
import io

import pandas as pd
from dotenv import load_dotenv

from utils.create_s3_client import s3_client, BUCKET_NAME

load_dotenv()


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

print("2. Deduplicating customers...")
