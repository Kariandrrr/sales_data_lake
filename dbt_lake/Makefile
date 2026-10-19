SHELL := /bin/bash

DBT      ?= dbt
PG_TGT   ?= pg_dev
CH_TGT   ?= ch_dev

.PHONY: help deps debug build-pg build-ch build-all test-pg test-ch docs freshness lint clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

deps: ## install packages (dbt deps) + commit package-lock.yml
	$(DBT) deps

debug: ## check both connections
	$(DBT) debug --target $(PG_TGT)
	$(DBT) debug --target $(CH_TGT)

build-pg: ## tests for postgres-models
	$(DBT) build --target $(PG_TGT) --select tag:postgres

build-ch: ## tests for ClickHouse-models
	$(DBT) build --target $(CH_TGT) --select tag:clickhouse

build-all: build-pg
	$(DBT) build --target $(CH_TGT) --select tag:clickhouse

test-pg: ## test for only PG
	$(DBT) test --target $(PG_TGT) --select tag:postgres

test-ch: ## tests for only CH
	$(DBT) test --target $(CH_TGT) --select tag:clickhouse

freshness: ## source freshness
	$(DBT) source freshness --target $(PG_TGT)
	$(DBT) source freshness --target $(CH_TGT)

docs: ## generate documentation (localhost:8080)
	$(DBT) docs generate --target $(PG_TGT)
	$(DBT) docs serve

clean:
	$(DBT) clean
