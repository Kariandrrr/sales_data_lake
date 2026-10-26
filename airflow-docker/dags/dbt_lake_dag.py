import os
from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

try:
    from airflow.sdk import DAG
except ImportError:
    from airflow import DAG


DBT_DIR = "/opt/airflow/dbt_lake"

COMMON = f"--profiles-dir {DBT_DIR} --no-use-colors"

DBT_BIN = os.environ.get("DBT_BIN", "dbt")
DBT = f"cd {DBT_DIR} && {DBT_BIN}"


LOADER_CMD = "python -m pipelines.load_pg_to_clickhouse"

default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "owner": "data",
}


@dag(
    dag_id="medallion_pipeline",
    description="Postgres -> bronze -> dbt: silver -> gold in ClickHouse",
    # schedule="0 3 * * *",
    # for tests
    schedule="*/5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["medallion", "lakehouse", "dbt"],
    default_args=default_args,
)
def dbt_lake_dag():

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{DBT} deps {COMMON}",
    )

    dbt_pg = BashOperator(
        task_id="dbt_build_postgres",
        bash_command=f"{DBT} build --target gp_prod --select tag:postgres {COMMON}",
    )

    load_ch = BashOperator(
        task_id="load_pg_to_clickhouse",
        bash_command=LOADER_CMD,
    )

    dbt_ch = BashOperator(
        task_id="dbt_build_clickhouse",
        bash_command=f"{DBT} build --target ch_prod --select tag:clickhouse {COMMON}",
    )

    dbt_docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"{DBT} docs generate --target ch_prod {COMMON}",
    )

    dbt_deps >> dbt_pg >> load_ch >> dbt_ch >> dbt_docs


dbt_lake_dag()
