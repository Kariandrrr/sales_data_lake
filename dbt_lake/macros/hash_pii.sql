{% macro hash_pii(column) -%}
{{ return(adapter.dispatch('hash_pii', 'dbt_lake')(column)) }}
{%- endmacro %}

{% macro default__hash_pii(column) -%}
substring(encode(digest({{ column }}, 'sha256'), 'hex'), 1, 16)
{%- endmacro %}

{% macro clickhouse__hash_pii(column) -%}
    substring(hex(SHA256({{ column }})), 1, 16)
{%- endmacro %}