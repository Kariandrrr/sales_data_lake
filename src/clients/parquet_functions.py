import io

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.fs as pafs

from config import settings
from . import s3_client


def read_parquet(key: str) -> pd.DataFrame:
    obj = s3_client.get_object(Bucket=settings.BUCKET_NAME, Key=key)
    return pd.read_parquet(io.BytesIO(obj["Body"].read()))


def write_parquet(key: str, df: pd.DataFrame, partition_cols: list[str] | None = None):
    bucket_name = getattr(settings, "BUCKET_NAME", "lakehouse")
    if partition_cols:
        table = pa.Table.from_pandas(df=df)

        s3_fs = pafs.S3FileSystem(
            endpoint_override=settings.MINIO_ENDPOINT.replace("http://", "").replace(
                "https://", ""
            ),
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            scheme="http",
        )

        target_path = f"{bucket_name}/{key.rstrip('/')}"

        ds.write_dataset(
            table,
            base_dir=target_path,
            partitioning=partition_cols,
            format="parquet",
            filesystem=s3_fs,
            existing_data_behavior="overwrite_or_ignore",
        )
    else:
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow")
        buffer.seek(0)
        s3_client.upload_fileobj(buffer, settings.BUCKET_NAME, key)
