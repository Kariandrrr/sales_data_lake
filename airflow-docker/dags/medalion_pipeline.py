import sys
from datetime import datetime, timedelta

import pendulum
from airflow.decorators import dag, task

if "/opt/airflow/src" not in sys.path:
    sys.path.append("/opt/airflow/src")


local_tz = pendulum.timezone("Europe/Moscow")

default_args = {
    "owner": "karina",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="medallion_pipeline",
    description="Bronze -> Silver -> Gold marts",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=local_tz),
    catchup=False,
    tags=["medallion", "lakehouse"],
)
def medallion_pipeline():

    @task()
    def bronze():
        from pipelines.bronze.extract_to_bronze import extract_to_bronze

        extract_to_bronze()

    @task()
    def silver():
        from pipelines.silver.extract_to_silver import extract_to_silver

        extract_to_silver()

    @task()
    def load_base_data():
        from pipelines.gold.load_silver_datasets import load_sales_base

        return load_sales_base()

    @task()
    def mart_category(df_sales_base):
        from pipelines.gold.mart_sales_by_category import build_mart_sales_by_category

        build_mart_sales_by_category(df_sales_base)

    @task()
    def mart_sellers(df_sales_base):
        from pipelines.gold.mart_seller_performance import (
            build_mart_by_seller_performance,
        )

        build_mart_by_seller_performance(df_sales_base)

    @task()
    def mart_geo(df_sales_base):
        from pipelines.gold.mart_geo_analytics import build_mart_by_geo

        build_mart_by_geo(df_sales_base)

    b = bronze()
    s = silver()
    base_df = load_base_data()

    b >> s >> base_df
    base_df >> [mart_category(base_df), mart_sellers(base_df), mart_geo(base_df)]


medallion_pipeline()
