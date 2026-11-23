from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="03_sensors_producer",
    schedule=None,
    catchup=False,
    is_paused_upon_creation=True,
    tags=["learning"],
    start_date=datetime(2026, 11, 1),
)
def producer():
    @task
    def generate(ds=None):
        from generator.generate_orders import generate as _gen

        _gen(ds=ds, rows=500)

    @task
    def extract(dt=None):
        from pipelines.bronze.extract_to_bronze import extract_to_bronze

        extract_to_bronze(tables=["orders"], dt=dt)

    generate() >> extract()


producer()
