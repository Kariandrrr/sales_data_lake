import subprocess

from airflow.sdk import dag, task

DBT_DIR = "/opt/airflow/dbt_lake"
DBT_ARGS = ["--target", "ch_prod", "--profiles-dir", DBT_DIR, "--no-use-colors"]

TASK_REBUILD = "rebuild_all"
TASK_VERIFY = "verify_only"


@dag(
    dag_id="02_branching_and_trigger_rules",
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["learning", "branching"],
)
def branching_02():

    @task.branch
    def choose_path(changed=True) -> str:
        if isinstance(changed, str):
            is_changed = changed.strip().lower() in ("1", "true", "yes", "y")
        else:
            is_changed = bool(changed)

        return TASK_REBUILD if is_changed else TASK_VERIFY

    @task(retries=1, retry_delay=30, pool="dbt")
    def rebuild_all():
        subprocess.run(
            ["dbt", "build", "--select", "+tag:gold", *DBT_ARGS],
            check=True,
            cwd=DBT_DIR,
        )

    @task(retries=1, retry_delay=30, pool="dbt")
    def verify_only():
        subprocess.run(
            ["dbt", "test", "--select", "+tag:gold", *DBT_ARGS],
            check=True,
            cwd=DBT_DIR,
        )

    @task(trigger_rule="none_failed_min_one_success")
    def finish():
        print("Finished")

    @task(trigger_rule="one_failed")
    def notify_failure():
        print("failed")

    chosen = choose_path("{{ dag_run.conf.get('changed', true) }}")

    rebuild = rebuild_all()
    verify = verify_only()

    chosen >> [rebuild, verify]
    [rebuild, verify] >> finish()
    [rebuild, verify] >> notify_failure()


branching_02()
