from datetime import datetime, timedelta

from airflow.decorators import dag, task


@dag(
    dag_id="medallion_pipeline",
    description="Bronze -> Silver -> Gold marts",
    schedule="0 3 * * *",
    start_date=datetime(2020, 1, 1),
    catchup=False,
    default_args={
        "owner": "karina",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
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
    def mart_category():
        from pipelines.gold.mart_sales_by_category import build_mart_sales_by_category

        build_mart_sales_by_category()

    @task()
    def mart_sellers():
        from pipelines.gold.mart_seller_performance import (
            build_mart_by_seller_performance,
        )

        build_mart_by_seller_performance()

    @task()
    def mart_geo():
        from pipelines.gold.mart_geo_analytics import build_mart_by_geo

        build_mart_by_geo()

    bronze() >> silver() >> [mart_category(), mart_sellers(), mart_geo()]


medallion_pipeline()
