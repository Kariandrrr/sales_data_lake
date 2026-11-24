import os
from datetime import datetime, timedelta

import pendulum
from airflow.sdk import TaskGroup, dag, task

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
    schedule="@daily",
    start_date=datetime(2026, 1, 1, tzinfo=local_tz),
    catchup=False,
    max_active_runs=1,
    tags=["medallion", "lakehouse", "dbt"],
    default_args=default_args,
    doc_md=__doc__,
)
def medallion_pipeline():

    @task
    def get_tables() -> list[str]:
        from pipelines.bronze.extract_to_bronze import ALL_TABLES

        return ALL_TABLES

    @task(max_active_tis_per_dagrun=3)
    def bronze(table: str, ds: str | None = None) -> str:
        from pipelines.bronze.extract_to_bronze import extract_to_bronze

        extract_to_bronze(tables=[table], dt=ds)
        return table

    @task.branch
    def check_data(ds: str | None = None) -> str:
        from sqlalchemy import create_engine, text

        from config import settings

        engine = create_engine(settings.DATABASE_URL)
        try:
            with engine.connect() as conn:
                new_orders = conn.execute(
                    text(
                        "SELECT count(*) FROM orders "
                        "WHERE _ingested_at::date = CAST(:ds AS date)"
                    ),
                    {"ds": ds},
                ).scalar_one()
        finally:
            engine.dispose()

        if new_orders:
            print(f"{new_orders} new orders for {ds} — rebuilding marts")
            return "dbt.build_silver"

        print(f"no new orders for {ds} — skipping dbt")
        return "notify_empty"

    @task
    def notify_empty(ds: str | None = None) -> None:
        print(f"[medallion] no new rows for {ds}; silver/gold left untouched")

    @task.bash(task_id="build_silver")
    def dbt_silver() -> str:
        return (
            f"cd {DBT_DIR} && {DBT} build --target ch_prod "
            f"--select tag:silver {COMMON}"
        )

    @task.bash(task_id="build_gold")
    def dbt_gold() -> str:
        return (
            f"cd {DBT_DIR} && {DBT} build --target ch_prod "
            f"--select tag:gold {COMMON}"
        )

    @task.bash(task_id="docs")
    def dbt_docs() -> str:
        return f"cd {DBT_DIR} && {DBT} docs generate --target ch_prod {COMMON}"

    @task(trigger_rule="none_failed_min_one_success")
    def finish(ds: str | None = None) -> None:
        print(f"[medallion] run for {ds} finished")

    tables = get_tables()

    with TaskGroup("bronze", default_args={"pool": "bronze_extract"}):
        bronze_tasks = bronze.expand(table=tables)

    branch = check_data()

    with TaskGroup("dbt", default_args={"pool": "clickhouse"}):
        silver = dbt_silver()
        gold = dbt_gold()
        docs = dbt_docs()
        silver >> gold >> docs

    empty = notify_empty()
    done = finish()

    bronze_tasks >> branch
    branch >> silver
    branch >> empty
    docs >> done
    empty >> done


medallion_pipeline()
