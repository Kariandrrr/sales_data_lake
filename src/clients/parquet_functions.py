import io

import pandas as pd

from . import s3_client
from ..config import settings


def read_parquet(key: str) -> pd.DataFrame:
    obj = s3_client.get_object(Bucket=settings.BUCKET_NAME, Key=key)
    return pd.read_parquet(io.BytesIO(obj["Body"].read()))


def write_parquet(key: str, df: pd.DataFrame):
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)
    s3_client.upload_fileobj(buffer, settings.BUCKET_NAME, key)
