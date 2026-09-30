FROM apache/airflow:3.3.2

USER root

USER airflow

COPY requirements.txt /

RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    -r /requirements.txt