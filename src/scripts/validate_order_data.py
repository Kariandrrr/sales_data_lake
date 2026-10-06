def validate_silver_data(dfs: dict):
    pk_checks = [
        ("orders", "order_id"),
        ("customers", "customer_id"),
        ("products", "product_id"),
        ("sellers", "seller_id"),
    ]
    for table_name, pk_col in pk_checks:
        null_count = dfs[table_name][pk_col].isna().sum()
        if null_count > 0:
            raise ValueError(
                f"[DQ FAIL] В таблице {table_name} найдено {null_count} NULL-значений в PK {pk_col}"
            )

    invalid_items = dfs["items"][
        (dfs["items"]["price"] < 0 | (dfs["items"]["freight_value"] < 0))
    ].shape[0]
    if invalid_items > 0:
        raise ValueError(
            f"[DQ FAIL] В order_items найдено {invalid_items} строк с некорректной ценой/доставкой"
        )

    unmatched_cust = (
        ~dfs["orders"]["customer_id"].isin(dfs["customers"]["customer_id"])
    ).sum()
    if unmatched_cust > 0:
        raise ValueError(
            f"[DQ FAIL] Найдено {unmatched_cust} заказов с несуществующим customer_id"
        )

    unmatched_prod = (
        ~dfs["items"]["product_id"].isin(dfs["products"]["product_id"])
    ).sum()
    if unmatched_prod > 0:
        raise ValueError(
            f"[DQ FAIL] Найдено {unmatched_prod} позиций с несуществующим product_id"
        )

    unmatched_seller = (
        ~dfs["items"]["seller_id"].isin(dfs["sellers"]["seller_id"])
    ).sum()
    if unmatched_seller > 0:
        raise ValueError(
            f"[DQ FAIL] Найдено {unmatched_seller} позиций с несуществующим seller_id"
        )

    print("[DQ SUCCESS] Проверки качества пройдены для всех сущностей!")
