import io

import pandas as pd
from sqlalchemy import create_engine

from ...clients import ensure_bucket_exists, s3_client
from ...config import settings

if not all(
    [
        settings.DB_USER,
        settings.DB_PASSWORD,
        settings.DB_HOST,
        settings.DB_PORT,
        settings.DB_NAME,
        settings.MINIO_ENDPOINT,
        settings.MINIO_ACCESS_KEY,
        settings.MINIO_SECRET_KEY,
    ]
):
    raise ValueError("Error: Missing required environment variables in .env file.")

engine = create_engine(settings.DATABASE_URL)

print("--- Starting extraction pipeline to MinIO (Bronze layer) ---")

ensure_bucket_exists(settings.BRONZE_BUCKET)

tables = [
    "customers",
    "geolocation",
    "order_items",
    "order_payments",
    "order_reviews",
    "orders",
    "products",
    "sellers",
    "product_category_name_translation",
]

for table in tables:
    print(f"Extracting table '{table}' from Postgres...")
    df = pd.read_sql_table(table_name=table, con=engine)

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    parquet_buffer.seek(0)

    s3_key = f"bronze/{table}/{table}.parquet"

    print(
        f"Uploading {len(df)} records to MinIO S3 path: '{settings.BRONZE_BUCKET}/{s3_key}'..."
    )
    s3_client.upload_fileobj(parquet_buffer, settings.BRONZE_BUCKET, s3_key)
    print(f"✓ Successfully stored '{table}' in Bronze layer.\n")

print("=== Extraction to Bronze Layer Completed Successfully! ===")
