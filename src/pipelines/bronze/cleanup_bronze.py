"""Delete stale objects from the bronze bucket before reloading the facts.

Run BEFORE extract_to_bronze, never after: it removes *every* dt=... partition
and the flat copies of the four fact tables, because the layer is being rebuilt
from scratch under the mixed scheme:

    facts (orders, order_items, order_payments, order_reviews)
        -> bronze/dt=<YYYY-MM-DD>/<table>/<table>.parquet
    dimensions (the other 5 tables)
        -> bronze/<table>/<table>.parquet

Dimension files are never touched: they are full snapshots and will simply be
rewritten (same key) by the next extract.

Usage, from the repo root:

    docker compose exec -w /opt/airflow/src airflow-worker \
        python -m pipelines.bronze.cleanup_bronze              # dry run
    docker compose exec -w /opt/airflow/src airflow-worker \
        python -m pipelines.bronze.cleanup_bronze --delete     # for real
"""

import argparse
import re
from collections import defaultdict

from clients import s3_client
from config import settings

FACT_TABLES = ("orders", "order_items", "order_payments", "order_reviews")
PARTITION_RE = re.compile(r"dt=\d{4}-\d{2}-\d{2}/")
BATCH = 500

MIB = 1024 * 1024


def list_objects(bucket: str):
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            yield obj["Key"], obj["Size"]


def table_of(key: str) -> str:
    parts = key.split("/")
    if len(parts) >= 4 and parts[0] == "bronze":
        return parts[2]
    return parts[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--delete", action="store_true", help="really delete (default: dry run)"
    )
    ap.add_argument(
        "--keep",
        nargs="*",
        default=[],
        metavar="YYYY-MM-DD",
        help="partition dates to keep, e.g. --keep 2026-01-01",
    )
    args = ap.parse_args()

    bucket = settings.BRONZE_BUCKET
    keep = set(args.keep)
    print(f"bucket: {bucket}")

    doomed: dict[str, list[tuple[str, int]]] = defaultdict(list)
    kept: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    for key, size in list_objects(bucket):
        m = PARTITION_RE.search(key)
        if m:
            dt = m.group(0)[3:-1]
            reason = None if dt in keep else f"partition dt={dt}"
        elif table_of(key) in FACT_TABLES:
            reason = "flat fact file"
        else:
            reason = None

        if reason:
            doomed[reason].append((key, size))
        else:
            stats = kept[table_of(key)]
            stats[0] += 1
            stats[1] += size

    if not doomed:
        print("nothing to delete — bucket already clean")
    for reason in sorted(doomed):
        items = doomed[reason]
        total = sum(s for _, s in items)
        print(f"\n[{reason}] {len(items)} objects, {total / MIB:.1f} MiB")
        for key, size in items[:5]:
            print(f"  {key}  {size / MIB:.1f} MiB")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")

    print("\nkept:")
    for table in sorted(kept):
        n, b = kept[table]
        print(f"  {table:<40} {n:>4} objects  {b / MIB:>8.1f} MiB")

    to_delete = [key for items in doomed.values() for key, _ in items]
    if not args.delete:
        print(
            f"\ndry run: {len(to_delete)} objects would be deleted. Re-run with --delete."
        )
        return

    for i in range(0, len(to_delete), BATCH):
        chunk = to_delete[i : i + BATCH]
        s3_client.delete_objects(
            Bucket=bucket, Delete={"Objects": [{"Key": k} for k in chunk]}
        )
        print(f"deleted {min(i + BATCH, len(to_delete))}/{len(to_delete)}")

    print("done — now run extract_to_bronze for the four fact tables")


if __name__ == "__main__":
    main()
