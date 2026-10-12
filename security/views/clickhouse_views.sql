CREATE VIEW IF NOT EXISTS mart_sales_by_category AS
SELECT *
FROM s3(
    'http://minio-lakehouse:9000/lakehouse/gold/marts/mart_sales_by_category.parquet',
    'minioadmin',
    'minioadminpassword',
    'Parquet'
);

CREATE VIEW IF NOT EXISTS mart_geo_analytics AS
SELECT *
FROM s3(
    'http://minio-lakehouse:9000/lakehouse/gold/marts/mart_geo_analytics.parquet',
    'minioadmin',
    'minioadminpassword',
    'Parquet'
);

CREATE VIEW IF NOT EXISTS mart_seller_performance AS
SELECT *
FROM s3(
    'http://minio-lakehouse:9000/lakehouse/gold/marts/mart_seller_performance.parquet',
    'minioadmin',
    'minioadminpassword',
    'Parquet'
);