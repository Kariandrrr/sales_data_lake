from datetime import datetime

from airflow.sdk import dag, task, Asset

BRONZE_ORDERS_ASSET = Asset(
    name="bronze_orders",
    uri="s3://bronze/dt=*/orders/orders.parquet",
    group="bronze",
)


@dag(
    dag_id="03_2_assets_producer",
    schedule=None,
    catchup=False,
    is_paused_upon_creation=True,
    tags=["learning"],
    start_date=datetime(2026, 11, 1),
)
def asset_producer():
    @task
    def asset_generate(ds=None):
        from generator.generate_orders import generate as _gen

        _gen(ds=ds, rows=500)

    @task(outlets=[BRONZE_ORDERS_ASSET])
    def asset_extract(dt=None):
        from pipelines.bronze.extract_to_bronze import extract_to_bronze

        return extract_to_bronze(tables=["orders"], dt=dt)

    asset_generate() >> asset_extract()


asset_producer()
