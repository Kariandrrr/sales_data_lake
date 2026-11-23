import os
import subprocess
from datetime import datetime

from airflow.sdk import dag, Asset, task

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

    @task
    def run_dbt_local():
        project_dir = "/opt/airflow/dbt_lake"
        profiles_dir = "/opt/airflow/dbt_lake"

        selector = "tag:silver,tag:gold"

        cmd = [
            "dbt",
            "run",
            "--project-dir",
            project_dir,
            "--profiles-dir",
            profiles_dir,
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
                env={**os.environ, "DBT_PROFILES_DIR": profiles_dir},
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
