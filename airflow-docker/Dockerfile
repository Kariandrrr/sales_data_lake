FROM apache/airflow:3.3.2

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

USER root

COPY requirements.txt /
RUN uv pip install --no-cache-dir --system -r /requirements.txt

RUN uv pip install --no-cache-dir --system pyspark

COPY requirements-dbt.txt /
RUN uv pip install --no-cache-dir --system -r /requirements-dbt.txt

RUN uv pip install --no-cache-dir --system sqlfluff sqlfluff-templater-dbt

USER airflow
