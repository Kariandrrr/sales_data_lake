import os
import subprocess
from datetime import datetime

from airflow.sdk import dag, Asset, task

from clients.create_s3_client import s3_client

BRONZE_ORDERS_ASSET = Asset(
    name="bronze_orders",
    uri="s3://bronze/dt=*/orders/orders.parquet",
    group="bronze",
)


@dag(
    dag_id="03_2_assets_consumer",
    schedule=[BRONZE_ORDERS_ASSET],
    catchup=False,
    is_paused_upon_creation=False,
    tags=["learning", "asset-driven"],
    start_date=datetime(2026, 11, 1),
)
def consumer_asset():

    @task(pool="dbt")
    def run_dbt_local(ds=None):

        file_key = f"bronze/dt={ds}/orders/orders.parquet"
        print(f"Validating data for dt={ds}...")

        try:
            response = s3_client.head_object(Bucket="bronze", Key=file_key)
            file_size = response["ContentLength"]

            if file_size == 0:
                raise ValueError(f"File {file_key} is empty (o bytes)")
            print(f"File validated: {file_key}, Size: {file_size} bytes")

        except s3_client.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                raise FileNotFoundError(f"File not found: {file_key}")
            elif error_code == "403":
                raise PermissionError(f"Access denied to: {file_key}")
            else:
                raise RuntimeError(f"S3 Error [{error_code}]: {e}")

        project_dir = "/opt/airflow/dbt_lake"
        profiles_dir = "/opt/airflow/dbt_lake"

        selector = "models/staging/clickhouse models/intermediate/clickhouse models/marts/clickhouse"

        cmd = [
            "dbt",
            "run",
            "--project-dir",
            project_dir,
            "--profiles-dir",
            profiles_dir,
            "--target",
            "ch_dev",
            "--select",
            selector,
        ]
        print(f" Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env={
                    **os.environ,
                    "DBT_PROFILES_DIR": profiles_dir,
                    "CH_HOST": "clickhouse",
                },
            )

            print("=== DBT STDOUT ===")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)

            if result.returncode != 0:
                raise RuntimeError(f"dbt failed with exit code {result.returncode}")

            return "dbt run completed successfully"

        except FileNotFoundError:
            raise RuntimeError(
                f"dbt executable not found! Is it installed? Path: {cmd[0]}"
            )

    run_dbt_local()


consumer_asset()
