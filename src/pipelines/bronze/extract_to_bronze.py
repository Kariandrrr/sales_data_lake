import os
import tempfile
from itertools import chain

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import create_engine, text

from clients import ensure_bucket_exists, s3_client
from config import settings

CHUNK_SIZE = 10_000
ROW_GROUP_SIZE = 50_000


def _write_table_chunked(engine, table: str) -> tuple[str, int]:
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        with engine.connect().execution_options(stream_results=True) as conn:
            chunks = pd.read_sql(
                text(f'SELECT * FROM "{table}"'),
                conn,
                chunksize=CHUNK_SIZE,
            )

            first = next(chunks, None)
            if first is None:
                raise RuntimeError(f"таблица '{table}' пустая — писать нечего")

            schema = pa.Table.from_pandas(first, preserve_index=False).schema
            writer = pq.ParquetWriter(tmp_path, schema, compression="snappy")

            try:
                total = 0
                for i, chunk in enumerate(chain([first], chunks), start=1):

                    arrow = pa.Table.from_pandas(chunk, preserve_index=False).cast(
                        schema
                    )
                    writer.write_table(arrow, row_group_size=ROW_GROUP_SIZE)

                    total += len(chunk)
                    print(f"  chunk {i}: +{len(chunk)} rows (всего {total})")
            finally:
                writer.close()
    except Exception:
        os.unlink(tmp_path)
        raise

    return tmp_path, total


def extract_to_bronze() -> None:
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

        tmp_path, rows = _write_table_chunked(engine, table)

        s3_key = f"bronze/{table}/{table}.parquet"

        try:
            print(
                f"Uploading {rows} records to MinIO S3 path: "
                f" '{settings.BRONZE_BUCKET}/{s3_key}'..."
            )
            with open(tmp_path, "rb") as f:
                s3_client.upload_fileobj(f, settings.BRONZE_BUCKET, s3_key)
        finally:
            os.unlink(tmp_path)

        print(f"✓ Successfully stored '{table}' in Bronze layer.\n")

    engine.dispose()
    print("=== Extraction to Bronze Layer Completed Successfully! ===")


if __name__ == "__main__":
    extract_to_bronze()
