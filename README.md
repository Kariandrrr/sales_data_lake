# Sales Data Lake

A data pipeline for the Olist e-commerce dataset: **Python for EL, dbt for transformations, ClickHouse as the analytical store, Airflow for orchestration, Metabase for BI.**

The project started as a pure-pandas pipeline where ClickHouse was only used as a file viewer over Parquet in MinIO. It has been rebuilt so that the columnar database actually does its job — storing and serving analytical tables — while dbt owns the transformation layer.

---

## Why this exists

The original pipeline did everything in pandas:

```
CSV → Postgres → Parquet in MinIO → pandas transforms → Parquet → ClickHouse VIEW over s3() → Metabase
```

Three problems with that:


| Problem                                                    | Consequence                                                                    |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------ |
| ClickHouse was a`SELECT * FROM s3(...)` wrapper            | every Metabase query re-read the Parquet file; the columnar engine did no work |
| All transformations ran in pandas memory                   | does not scale past a single machine                                           |
| Validation was a standalone`validate_order_data.py` script | easy to forget, no schema contract, no history                                 |

The rebuild splits **EL from T**:

- **EL stays in Python** — it is good at talking to Postgres and S3.
- **T moves to dbt** — declarative SQL, dependency graph inferred from `ref()`, tests living next to models, generated lineage.
- **ClickHouse stores silver and gold as `MergeTree` tables** — Metabase reads from disk, not from object storage.

---

## Architecture

```
┌──────────────┐
│  data_csv/   │   9 Olist CSV files
└──────┬───────┘
       │  python: load_data.py
       ▼
┌──────────────────────────────┐
│  Postgres  sales_db.public   │   9 tables
└──────┬───────────────────────┘
       │  python: extract_to_bronze.py  (read_sql_table → to_parquet → upload)
       ▼
┌──────────────────────────────┐
│  MinIO   bronze/*.parquet    │   immutable raw copies
└──────┬───────────────────────┘
       │
       │  ClickHouse  ENGINE = S3(url, key, secret, 'Parquet')
       │  raw.* holds no data — it is a window into bronze
       ▼
┌──────────────────────────────┐
│  ClickHouse  raw             │   8 S3-engine tables
└──────┬───────────────────────┘
       │  dbt:  source('ch_raw', ...)
       ▼
┌──────────────────────────────┐
│  ClickHouse  silver          │   stg_ch__* ×8  +  int_sales_base
│  MergeTree                   │   26 data tests
└──────┬───────────────────────┘
       │  dbt:  ref('int_sales_base')
       ▼
┌──────────────────────────────┐
│  ClickHouse  gold            │   mart_sales_by_category
│  MergeTree                   │   mart_geo_analytics
│                              │   mart_seller_performance
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Metabase  "Olist analytics" │
└──────────────────────────────┘

Orchestration: Airflow 3
  bronze (python) → dbt build --select tag:silver → --select tag:gold → dbt docs
```

Each layer reads only from the layer above it. Any layer can be rebuilt without touching the others.

---

## Stack


| Layer          | Technology                          | Role                                    |
| -------------- | ----------------------------------- | --------------------------------------- |
| Extraction     | Python 3.12, pandas, SQLAlchemy     | CSV → Postgres, Postgres → Parquet    |
| Object storage | MinIO (S3-compatible)               | bronze archive                          |
| File format    | Parquet                             | columnar, schema-carrying, compressible |
| Warehouse      | ClickHouse 26.9                     | silver + gold,`MergeTree`, S3 engine    |
| Transformation | dbt-core 1.12 + dbt-clickhouse 1.10 | models, tests, seeds, macros            |
| Orchestration  | Apache Airflow 3.3 (Celery)         | scheduling, retries, history            |
| BI             | Metabase                            | dashboards                              |
| Infra          | Docker Compose, uv                  | local environment                       |

---

## Repository layout

```
data_lakehouse/
├── docker-compose.yml              root stack: postgres_source, minio, clickhouse, metabase
├── data_csv/                       raw Olist CSV files
├── src/                            EL layer (Python)
│   ├── config.py
│   ├── clients/                    boto3 / parquet helpers
│   ├── utils/load_data.py          CSV → Postgres
│   └── pipelines/
│       └── bronze/
│           └── extract_to_bronze.py   Postgres → Parquet in MinIO
│
├── dbt_lake/                       transformation layer
│   ├── dbt_project.yml
│   ├── profiles.yml                (git-ignored — contains credentials)
│   ├── packages.yml
│   ├── macros/
│   │   ├── hash_pii.sql            adapter.dispatch: SHA256 on CH, digest() on PG
│   │   └── generate_schema_name.sql
│   ├── seeds/
│   │   └── category_translations_extra.csv
│   ├── sql/
│   │   └── clickhouse_raw_s3_tables.sql   DDL: raw/silver/gold + 8 S3-engine tables
│   └── models/
│       ├── staging/clickhouse/     8 stg_ch__* models + sources + tests
│       ├── intermediate/clickhouse/
│       │   └── int_sales_base.sql  join of 5 staging models (replaces df_sales_base)
│       └── marts/clickhouse/       3 mart_* models + tests
│
├── airflow-docker/                 orchestrator
│   ├── docker-compose.yaml
│   ├── Dockerfile                  Airflow + dbt + uv
│   ├── requirements.txt            generated, fully pinned with hashes
│   ├── requirements-dbt.txt        hand-maintained dbt pins
│   └── dags/
│       └── medallion_pipeline.py   bronze → dbt silver → dbt gold → docs
│
└── security/
    ├── roots/postgres_roles.sql
    └── views/clickhouse_views.sql  (legacy, replaced by dbt mart tables)
```

---

## Data model

### Sources (`raw`, ClickHouse, S3 engine)

`orders`, `order_items`, `customers`, `products`, `sellers`, `order_payments`, `order_reviews`, `product_category_name_translation`.

Each is declared once:

````
name: ch_raw
schema: raw          # in ClickHouse
tables:
name: ordersname: ch_raw
````

### Staging (`silver`)

One model per source table, prefixed with the source: `stg_ch__orders`, `stg_ch__order_items`, and so on. These models:

- rename columns to consistent snake_case
- cast types (`String` dates → `DateTime`, `Float64` money → `Decimal(18,2)`)
- trim and normalise text (`initcapUTF8`, `lower`, `trimBoth`)
- hash PII (`zip_code_prefix` → SHA256, first 16 chars)
- deduplicate (`GROUP BY key` + `argMax`, or `LIMIT 1 BY`)

No joins, no aggregation — staging only makes sources usable.

### Intermediate (`silver`)

`int_sales_base` — one row per order line, joined with customer, product, and category translation. Materialised as a table (not ephemeral) because three marts read it and the join is the most expensive operation in the project.

### Marts (`gold`)


| Mart                      | Rows  | Grain        | Columns                                                                                                                 |
| ------------------------- | ----- | ------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `mart_sales_by_category`  | 74    | category     | `product_category_name_english`, `total_orders`, `total_items_sold`, `total_revenue`, `total_freight`, `avg_item_price` |
| `mart_geo_analytics`      | 4 300 | state + city | `customer_state`, `customer_city`, `total_orders`, `unique_customers`, `total_spent`, `avg_freight_cost`                |
| `mart_seller_performance` | 3 095 | seller       | `seller_id`, `total_orders_fulfilled`, `total_items_sold`, `total_gross_revenue`, `first_order_at`, `last_order_at`     |

---

## Quickstart

### Prerequisites

- Docker + Docker Compose
- `uv` (optional, for the Python EL layer)

### 1. Start the infrastructure

```bash
docker compose up -d                      # root stack
docker compose -f airflow-docker/docker-compose.yaml up -d
```

Services:


| Service           | URL                   | Credentials                         |
| ----------------- | --------------------- | ----------------------------------- |
| MinIO console     | http://localhost:9001 | `minioadmin` / `minioadminpassword` |
| Airflow           | http://localhost:8080 | generated admin password            |
| Metabase          | http://localhost:3000 | setup on first run                  |
| ClickHouse        | `localhost:8123`      | `default` / `clickhouse`            |
| Postgres (source) | `localhost:5433`      | `postgres` / `postgrespassword`     |

### 2. Load CSV into Postgres, then into bronze

```bash
uv run python -m src.utils.load_data
uv run python -m src.pipelines.bronze.extract_to_bronze
```

### 3. Create the ClickHouse layers and raw tables

```bash
docker exec -i clickhouse-lakehouse clickhouse-client --password clickhouse --multiquery \
  --query "CREATE DATABASE IF NOT EXISTS raw; CREATE DATABASE IF NOT EXISTS silver; CREATE DATABASE IF NOT EXISTS gold;"

docker exec -i clickhouse-lakehouse clickhouse-client --password clickhouse --multiquery \
  < dbt_lake/sql/clickhouse_raw_s3_tables.sql
```

Verify ClickHouse can read bronze:

```sql
SELECT count() FROM raw.orders;   -- expect ~99 441
```

### 4. Build the dbt project

```bash
cd dbt_lake
dbt deps --profiles-dir .
dbt seed --target ch_prod --profiles-dir .
dbt build --target ch_prod --select tag:silver --profiles-dir .
dbt build --target ch_prod --select tag:gold   --profiles-dir .
```

Or the whole thing at once:

```bash
dbt build --target ch_prod --select +tag:gold --profiles-dir .
```

The leading `+` matters: it selects **ancestors** too. `--select tag:gold` alone would skip `int_sales_base` and read whatever happens to be in the database.

### 5. Point Metabase at `gold`

Admin → Databases → ClickHouse → **Database name**: `gold` → Save → Sync database schema.

---

## Running dbt inside Airflow

The DAG uses `@task.bash`, so the exact command is visible in the task log:

```python
@task.bash()
def dbt_silver() -> str:
    return f"cd {DBT_DIR} && {DBT} build --target ch_prod --select tag:silver {COMMON}"
```

Task order: `bronze` (Python) → `dbt_silver` → `dbt_gold`.

Adding a new mart does not require touching the DAG — put the `.sql` file under `models/marts/clickhouse/`, it inherits `tag:gold`, and the existing task picks it up.

> **Naming rule:** no file under `dags/` may start with `dbt_`. dbt 1.12 treats every importable `dbt_*` module as a plugin and will try to import it, which breaks the CLI in surprising ways.

---

## Data quality

26 tests replace the old `validate_order_data.py`.


| Test                            | Where                                                         | What it protects                               |
| ------------------------------- | ------------------------------------------------------------- | ---------------------------------------------- |
| `not_null`, `unique`            | keys of every staging model                                   | no duplicate or missing order/customer/product |
| `relationships`                 | `order_items → orders/products/sellers`                      | referential integrity                          |
| `accepted_values`               | `order_status`                                                | only the 8 known statuses                      |
| `accepted_range`                | `item_price`, `freight_amount` ≥ 0                           | no negative money                              |
| `unique_combination_of_columns` | `(order_id, order_item_id)`, `(order_id, payment_sequential)` | composite keys                                 |
| `unique_combination_of_columns` | `(customer_state, customer_city)` in `mart_geo_analytics`     | mart grain                                     |

```bash
dbt test --target ch_prod --profiles-dir .      # all tests
dbt test --target ch_prod --select stg_ch__orders --profiles-dir .
```

Data tests are also the contract for the marts: `mart_geo_analytics` will fail if a state/city pair ever appears twice.

---

## Engineering notes

### Why `staging` is materialised as a table, not a view

A view over `raw.*` is a view over an S3-engine table, which is a view over a Parquet file. Metabase would then read from MinIO on every query — exactly the problem this migration set out to fix. `table` reads the Parquet once and stores a `MergeTree` copy.

### Memory

ClickHouse runs with a small memory budget in this environment, so the pipeline is tuned for it:

- `max_bytes_before_external_sort` / `max_bytes_before_external_group_by` — spill to disk instead of OOM
- `join_algorithm: grace_hash` — hash join that can spill
- `argMax` instead of `ORDER BY … LIMIT 1 BY` — streaming aggregation instead of a full sort
- mart SQL avoids `ORDER BY` in the subquery; ordering is expressed via the table's `order_by`

Per-query `max_memory_usage` is kept **below** the server-wide `max_server_memory_usage`. If it were above, the per-query limit would never fire and the server would die instead of the query.

### Business-logic bugs found during the migration

The pandas version had three defects. All are fixed in dbt, in a way that keeps downstream column names stable except where the old name described the wrong thing.


| Old                                                    | New                                     | Why                              |
| ------------------------------------------------------ | --------------------------------------- | -------------------------------- |
| `avg_order_value` held `min(order_purchase_timestamp)` | `first_order_at` + `last_order_at`      | the column was a date, not money |
| `avg_freiht_cost`                                      | `avg_freight_cost`                      | typo                             |
| `customer_zip_code_prefix` overwritten by its hash     | `zip_code_hash` alongside the original  | destroyed the source value       |
| two hard-coded category translations in Python         | `seeds/category_translations_extra.csv` | data belongs in data             |

### Compatibility for BI

Renaming columns breaks dashboards. Two options were considered:

1. Fix the Metabase cards (fine for three cards).
2. Keep a compatibility view in the `default` database that re-aliases the new columns to the old names.

Both are documented in `handoff/MEMORY.md`. The compatibility layer keeps dashboards working while `gold` stays clean.

---

## Verification

After a build, three things should hold:

```bash
# 1. Object counts and row counts
docker exec clickhouse-lakehouse clickhouse-client --password clickhouse --query "
SELECT database, count() AS tables, sum(total_rows) AS rows
FROM system.tables WHERE database IN ('silver','gold') GROUP BY database"

# 2. No columns with a dot in the name (a sign of a stale model version)
docker exec clickhouse-lakehouse clickhouse-client --password clickhouse --query "
SELECT database, table, name FROM system.columns
WHERE database IN ('silver','gold') AND name LIKE '%.%'"

# 3. Idempotency — run twice, row counts must not change
```

Row counts reconciled against the legacy Parquet marts to within 0.001%; the residual difference comes from deduplication (`argMax` picks the row with the highest price, pandas kept the first row — same row count, different values).

---



## Dataset

[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — ~100 000 orders, 2016–2018, 9 relational CSV files.
