import os
from datetime import datetime, timedelta

import pendulum
from airflow.sdk import dag, task

local_tz = pendulum.timezone("Europe/Moscow")

DBT_DIR = "/opt/airflow/dbt_lake"
COMMON = f"--profiles-dir {DBT_DIR} --no-use-colors"
DBT = os.environ.get("DBT_BIN", "dbt")

default_args = {
    "owner": "karina",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="medallion_pipeline",
    description="Postgres -> bronze -> dbt: silver -> gold in ClickHouse",
    # schedule="0 3 * * *",
    # for tests
    schedule="*/5 * * * *",
    start_date=datetime(2026, 1, 1, tzinfo=local_tz),
    catchup=False,
    max_active_runs=1,
    tags=["medallion", "lakehouse", "dbt"],
    default_args=default_args,
)
def medallion_pipeline():

    @task()
    def bronze():
        from pipelines.bronze.extract_to_bronze import extract_to_bronze

        extract_to_bronze()

    @task.bash()
    def dbt_silver() -> str:
        return (
            f"cd {DBT_DIR} && {DBT} build --target ch_prod --select tag:silver {COMMON}"
        )

    @task.bash()
    def dbt_gold() -> str:
        return (
            f"cd {DBT_DIR} && {DBT} build --target ch_prod --select tag:gold {COMMON}"
        )

    @task.bash()
    def dbt_docs() -> str:
        return f"cd {DBT_DIR} && {DBT} docs generate --target ch_prod {COMMON}"

    bronze() >> dbt_silver() >> dbt_gold() >> dbt_docs()


medallion_pipeline()
