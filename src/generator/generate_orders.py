import argparse
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text

from config import settings

SQL = Path(__file__).with_name("generate_orders.sql")


def generate(ds: str | None = None, rows: int = 500) -> str:
    ds = ds or date.today().isoformat()
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.begin() as conn:
            conn.execute(text(SQL.read_text()), {"ds": ds, "rows": rows})
    finally:
        engine.dispose()
    print(f"generated {rows} orders for ds={ds}")
    return ds


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ds", help="логическая дата, YYYY-MM-DD (по умолчанию сегодня)")
    p.add_argument("--rows", type=int, default=500)
    a = p.parse_args()
    generate(ds=a.ds, rows=a.rows)
