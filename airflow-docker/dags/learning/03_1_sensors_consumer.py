from datetime import datetime

from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.sdk import dag, task


@dag(
    dag_id="03_1_sensors_consumer",
    schedule=None,
    catchup=False,
    is_paused_upon_creation=True,
    tags=["learning"],
    start_date=datetime(2026, 11, 1),
)
def consumer():
    wait = S3KeySensor(
        task_id="wait_partition",
        bucket_name="bronze",
        bucket_key="bronze/dt={{ ds }}/orders/orders.parquet",
        aws_conn_id="minio",
        poke_interval=15,
        timeout=600,
        mode="reschedule",
        soft_fail=True,
    )

    @task
    def check(ds=None):
        print(f"Partition for {ds} is ready")

    wait >> check()


consumer()
