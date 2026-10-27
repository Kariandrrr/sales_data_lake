CREATE TABLE IF NOT EXISTS raw.orders
(
    order_id                      String,
    customer_id                   String,
    order_status                  Nullable(String),
    order_purchase_timestamp      Nullable(String),
    order_approved_at             Nullable(String),
    order_delivered_carrier_date  Nullable(String),
    order_delivered_customer_date Nullable(String),
    order_estimated_delivery_date Nullable(String)
)
    ENGINE = S3('http://minio-lakehouse:9000/bronze/bronze/orders/orders.parquet',
                'minioadmin', 'minioadminpassword', 'Parquet');

CREATE TABLE IF NOT EXISTS raw.order_items
(
    order_id            String,
    order_item_id       Nullable(Int32),
    product_id          Nullable(String),
    seller_id           Nullable(String),
    shipping_limit_date Nullable(String),
    price               Nullable(Float64),
    freight_value       Nullable(Float64)
)
    ENGINE = S3('http://minio-lakehouse:9000/bronze/bronze/order_items/order_items.parquet',
                'minioadmin', 'minioadminpassword', 'Parquet');

CREATE TABLE IF NOT EXISTS raw.customers
(
    customer_id              String,
    customer_unique_id       Nullable(String),
    customer_zip_code_prefix Nullable(Int32),
    customer_city            Nullable(String),
    customer_state           Nullable(String)
)
    ENGINE = S3('http://minio-lakehouse:9000/bronze/bronze/customers/customers.parquet',
                'minioadmin', 'minioadminpassword', 'Parquet');

CREATE TABLE IF NOT EXISTS raw.products
(
    product_id                 String,
    product_category_name      Nullable(String),
    product_name_lenght        Nullable(Int32),
    product_description_lenght Nullable(Int32),
    product_photos_qty         Nullable(Int32),
    product_weight_g           Nullable(Int32),
    product_length_cm          Nullable(Int32),
    product_height_cm          Nullable(Int32),
    product_width_cm           Nullable(Int32)
)
    ENGINE = S3('http://minio-lakehouse:9000/bronze/bronze/products/products.parquet',
                'minioadmin', 'minioadminpassword', 'Parquet');

CREATE TABLE IF NOT EXISTS raw.sellers
(
    seller_id              String,
    seller_zip_code_prefix Nullable(Int32),
    seller_city            Nullable(String),
    seller_state           Nullable(String)
)
    ENGINE = S3('http://minio-lakehouse:9000/bronze/bronze/sellers/sellers.parquet',
                'minioadmin', 'minioadminpassword', 'Parquet');

CREATE TABLE IF NOT EXISTS raw.order_payments
(
    order_id             String,
    payment_sequential   Nullable(Int32),
    payment_type         Nullable(String),
    payment_installments Nullable(Int32),
    payment_value        Nullable(Float64)
)
    ENGINE = S3('http://minio-lakehouse:9000/bronze/bronze/order_payments/order_payments.parquet',
                'minioadmin', 'minioadminpassword', 'Parquet');

CREATE TABLE IF NOT EXISTS raw.order_reviews
(
    review_id               String,
    order_id                Nullable(String),
    review_score            Nullable(Int32),
    review_comment_title    Nullable(String),
    review_comment_message  Nullable(String),
    review_creation_date    Nullable(String),
    review_answer_timestamp Nullable(String)
)
    ENGINE = S3('http://minio-lakehouse:9000/bronze/bronze/order_reviews/order_reviews.parquet',
                'minioadmin', 'minioadminpassword', 'Parquet');

CREATE TABLE IF NOT EXISTS raw.product_category_name_translation
(
    product_category_name         String,
    product_category_name_english Nullable(String)
)
    ENGINE = S3(
            'http://minio-lakehouse:9000/bronze/bronze/product_category_name_translation/product_category_name_translation.parquet',
            'minioadmin', 'minioadminpassword', 'Parquet');
