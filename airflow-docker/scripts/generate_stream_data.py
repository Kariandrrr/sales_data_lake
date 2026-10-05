import random
import time
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:postgrespassword@postgres_source:5432/sales_db"


def get_engine():
    return create_engine(DB_URL)


def generate_live_orders(engine):
    with engine.connect() as conn:
        customer_id = conn.execute(
            text("SELECT customer_id FROM customers ORDER BY RANDOM() LIMIT 1")
        ).scalar()
        seller_id = conn.execute(
            text("SELECT seller_id FROM sellers ORDER BY RANDOM() LIMIT 1")
        ).scalar()
        product_id = conn.execute(
            text("SELECT product_id FROM products ORDER BY RANDOM() LIMIT 1")
        ).scalar()

        if not all([customer_id, seller_id, product_id]):
            print(
                "⚠️ База данных пуста! Сначала заполните справочники customers, sellers, products."
            )
            return

        order_id = str(uuid.uuid4()).replace("-", "")
        now = datetime.now()

        insert_order = text("""
                            INSERT INTO orders (
                                order_id, customer_id, order_status,
                                order_purchase_timestamp, order_approved_at
                            ) VALUES (:order_id, :customer_id, 'delivered', :now, :now)
                            """)
        conn.execute(
            insert_order, {"order_id": order_id, "customer_id": customer_id, "now": now}
        )

        # 2. Вставляем запись в order_items
        price = round(random.uniform(15.0, 350.0), 2)
        freight_value = round(random.uniform(5.0, 30.0), 2)

        insert_item = text("""
                           INSERT INTO order_items (
                               order_id, order_item_id, product_id, seller_id,
                               shipping_limit_date, price, freight_value
                           ) VALUES (:order_id, 1, :product_id, :seller_id, :now, :price, :freight_value)
                           """)
        conn.execute(
            insert_item,
            {
                "order_id": order_id,
                "product_id": product_id,
                "seller_id": seller_id,
                "now": now,
                "price": price,
                "freight_value": freight_value,
            },
        )

        conn.commit()
        print(
            f"[{now.strftime('%H:%M:%S')}] ✅ Добавлен заказ {order_id[:8]}... на сумму ${price}"
        )


def run_generator(interval_seconds=20):
    print("Start generator in sales_db..")
    engine = get_engine()
    try:
        while True:
            generate_live_orders(engine)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("Generator was interrupted by user ")


if __name__ == "__main__":
    run_generator(interval_seconds=20)
