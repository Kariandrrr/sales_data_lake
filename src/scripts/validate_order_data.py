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
                f"[DQ FAIL] In table {table_name} found {null_count} NULL-values in PK {pk_col}"
            )

    invalid_items = dfs["items"][
        (dfs["items"]["price"] < 0 | (dfs["items"]["freight_value"] < 0))
    ].shape[0]
    if invalid_items > 0:
        raise ValueError(
            f"[DQ FAIL] In order_items found {invalid_items} strings with incorrect price/delivery"
        )

    unmatched_cust = (
        ~dfs["orders"]["customer_id"].isin(dfs["customers"]["customer_id"])
    ).sum()
    if unmatched_cust > 0:
        raise ValueError(
            f"[DQ FAIL] Found {unmatched_cust} orders with unrealistic customer_id"
        )

    unmatched_prod = (
        ~dfs["items"]["product_id"].isin(dfs["products"]["product_id"])
    ).sum()
    if unmatched_prod > 0:
        raise ValueError(
            f"[DQ FAIL] Found {unmatched_prod} positions with unrealistic product_id"
        )

    unmatched_seller = (
        ~dfs["items"]["seller_id"].isin(dfs["sellers"]["seller_id"])
    ).sum()
    if unmatched_seller > 0:
        raise ValueError(
            f"[DQ FAIL] Found {unmatched_seller} positions with unrealistic seller_id"
        )

    print("[DQ SUCCESS] Checks of data quality are done!")
