from airflow.sdk import dag, task


@dag(
    dag_id="01_mapping",
    tags=["learning"],
    is_paused_upon_creation=True,
    catchup=False,
    schedule=None,
)
def mapping_01():

    @task
    def get_tables() -> list[str]:
        from pipelines.bronze.extract_to_bronze import ALL_TABLES

        return ALL_TABLES

    @task(max_active_tis_per_dagrun=2)
    def extract_table(table: str) -> str:
        from pipelines.bronze.extract_to_bronze import extract_to_bronze

        extract_to_bronze(tables=[table])
        return table

    extract_table.expand(table=get_tables())


mapping_01()
