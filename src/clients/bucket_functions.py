from src.clients.create_s3_client import s3_client


def ensure_bucket_exists(bucket_name: str):
    response = s3_client.list_buckets()
    buckets = [b["Name"] for b in response.get("Buckets", [])]
    if bucket_name not in buckets:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"✓ Created S3 Bucket: '{bucket_name}'")
