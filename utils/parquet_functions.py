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
