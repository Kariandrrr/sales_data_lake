import io
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from utils.create_s3_client import s3_client

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BRONZE_BUCKET = "lakehouse"

if not all(
    [
        DB_USER,
        DB_PASSWORD,
        DB_HOST,
        DB_PORT,
        DB_NAME,
        MINIO_ENDPOINT,
        MINIO_ACCESS_KEY,
        MINIO_SECRET_KEY,
    ]
):
    raise ValueError("Error: Missing required environment variables in .env file.")

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)


def ensure_bucket_exists(bucket_name: str):
    response = s3_client.list_buckets()
    buckets = [b["Name"] for b in response.get("Buckets", [])]
    if bucket_name not in buckets:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"✓ Created S3 Bucket: '{bucket_name}'")


print("--- Starting extraction pipeline to MinIO (Bronze layer) ---")

ensure_bucket_exists(BRONZE_BUCKET)

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
        f"Uploading {len(df)} records to MinIO S3 path: '{BRONZE_BUCKET}/{s3_key}'..."
    )
    s3_client.upload_fileobj(parquet_buffer, BRONZE_BUCKET, s3_key)
    print(f"✓ Successfully stored '{table}' in Bronze layer.\n")

print("=== Extraction to Bronze Layer Completed Successfully! ===")
