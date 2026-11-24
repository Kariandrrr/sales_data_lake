import argparse
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text

from config import settings

HERE = Path(__file__).parent

CLEANUP = [
    "DELETE FROM order_reviews WHERE _ingested_at::date = CAST(:ds AS date)",
    "DELETE FROM order_payments WHERE _ingested_at::date = CAST(:ds AS date)",
    "DELETE FROM order_items WHERE _ingested_at::date = CAST(:ds AS date)",
    "DELETE FROM orders WHERE _ingested_at::date = CAST(:ds AS date)",
]

SCRIPTS = [
    "generate_orders.sql",
    "generate_order_items.sql",
    "generate_order_payments.sql",
    "generate_order_reviews.sql",
]


def generate(ds: str | None = None, rows: int = 10, allow_future: bool = False) -> str:
    ds = ds or date.today().isoformat()
    if not allow_future and ds > date.today().isoformat():
        raise SystemExit(
            f"refusing to generate future date {ds} (today is {date.today().isoformat()}); "
            "pass --allow-future if you really mean it"
        )
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.begin() as conn:
            for stmt in CLEANUP:
                conn.execute(text(stmt), {"ds": ds})
            for name in SCRIPTS:
                conn.execute(text((HERE / name).read_text()), {"ds": ds, "rows": rows})
                print(f"  ran {name}")
    finally:
        engine.dispose()
    print(f"generated ~{rows} orders (+items/payments/reviews) for ds={ds}")
    return ds


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ds", help="logical date, YYYY-MM-DD (default: today)")
    p.add_argument("--rows", type=int, default=10)
    p.add_argument("--allow-future", action="store_true")
    a = p.parse_args()
    generate(ds=a.ds, rows=a.rows, allow_future=a.allow_future)
