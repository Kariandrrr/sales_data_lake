import argparse
import os
import tempfile
from datetime import date
from itertools import chain

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import create_engine, text

from clients import ensure_bucket_exists, s3_client
from config import settings

CHUNK_SIZE = 50_000
ROW_GROUP_SIZE = 100_000


ALL_TABLES = [
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


def _incremental_tables(engine) -> set[str]:
    """Tables that have an _ingested_at column -> loaded as daily deltas.

    Detected from the database, not hardcoded: to make a table incremental,
    add an _ingested_at column to it in Postgres and the extract picks it
    up automatically. Tables without the column are dumped in full.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND column_name = '_ingested_at'"
            )
        ).all()
    return {row[0] for row in rows}


def _write_table_chunked(
    engine, table: str, dt: str | None = None, incremental: bool = False
) -> tuple[str | None, int]:
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        with engine.connect().execution_options(stream_results=True) as conn:
            if incremental:
                query = text(
                    f'SELECT * FROM "{table}" WHERE _ingested_at::date = CAST(:dt AS date)'
                )
                params: dict | None = {"dt": dt}
            else:
                query = text(f'SELECT * FROM "{table}"')
                params = None

            chunks = pd.read_sql(
                query,
                conn,
                params=params,
                chunksize=CHUNK_SIZE,
            )

            first = next(chunks, None)
            if first is None:
                if incremental:
                    print(f"  no new rows for '{table}' on {dt} — skipping")
                    os.unlink(tmp_path)
                    return None, 0
                raise RuntimeError(f"Table '{table}' is empty — nothing to write")

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
                    print(f"  chunk {i}: +{len(chunk)} rows (total {total})")
            finally:
                writer.close()
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return tmp_path, total


def extract_to_bronze(tables: list[str] | None = None, dt: str | None = None) -> None:
    if dt is None:
        dt = date.today().isoformat()

    if tables is None:
        tables = ALL_TABLES
    else:
        unknown = set(tables) - set(ALL_TABLES)
        if unknown:
            raise ValueError(f"Unknown table(s): {', '.join(sorted(unknown))}")

    tables = tables or ALL_TABLES

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
    incremental = _incremental_tables(engine)

    print("--- Starting extraction pipeline to MinIO (Bronze layer) ---")
    print(f"Incremental tables (daily deltas): {sorted(incremental) or 'none'}")

    ensure_bucket_exists(settings.BRONZE_BUCKET)

    for table in tables:
        print(f"Extracting table '{table}' from Postgres...")

        is_incremental = table in incremental
        tmp_path, rows = _write_table_chunked(
            engine, table, dt=dt, incremental=is_incremental
        )

        if tmp_path is None:
            continue

        if is_incremental:
            s3_key = f"bronze/dt={dt}/{table}/{table}.parquet"
        else:
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
    parser = argparse.ArgumentParser(
        description="Extract tables from Postgres into Bronze layer as Parquet"
    )
    parser.add_argument(
        "--table",
        action="append",
        help="tables to extract from Postgres tables",
    )
    parser.add_argument(
        "--dt",
        help="logical date for incremental tables, YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args()

    extract_to_bronze(args.table, dt=args.dt)
