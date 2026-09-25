"""Airflow schedules for the custom Dremio-to-OpenMetadata integration."""

from pathlib import Path
import subprocess
import sys

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator


SCRIPT = Path("/opt/airflow/dremio_sync/dremio_openmetadata_sync.py")


def run(operation):
    subprocess.run([sys.executable, str(SCRIPT), operation], check=True)


def build_dag(name, schedule, operation, description):
    with DAG(
        dag_id=name,
        description=description,
        start_date=pendulum.datetime(2026, 9, 25, tz="America/El_Salvador"),
        schedule_interval=schedule,
        catchup=False,
        max_active_runs=1,
        default_args={"retries": 1},
        tags=["openmetadata", "dremio"],
    ) as dag:
        PythonOperator(task_id=operation, python_callable=run, op_args=[operation])
    return dag


Dremio_Federation_lineage = build_dag(
    "Dremio_Federation_lineage",
    "30 4 * * *",
    "lineage",
    "Publica el lineage de la VDS Student_360 desde su SQL en Dremio.",
)
Dremio_Federation_usage = build_dag(
    "Dremio_Federation_usage",
    "45 4 * * *",
    "usage",
    "Sincroniza el delta de uso diario de Student_360 desde sys.jobs_recent.",
)
