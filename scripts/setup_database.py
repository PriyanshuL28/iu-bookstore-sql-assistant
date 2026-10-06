"""Create the bookstore schema, load synthetic data and (optionally) a read-only role.

Usage:
    python -m scripts.setup_database                       # uses ADMIN_DATABASE_URL from .env
    python -m scripts.setup_database --readonly-password S3cret!
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

from scripts.synthetic_data import COLUMNS, LOAD_ORDER, generate
from sql_assistant.db import normalize_url

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT / "database" / "schema.sql"
READONLY_ROLE = "bookstore_reader"

SERIAL_COLUMNS = {
    "categories": "category_id",
    "products": "product_id",
    "product_variants": "variant_id",
    "customers": "customer_id",
    "promotions": "promotion_id",
    "orders": "order_id",
    "order_items": "order_item_id",
}


def load_data(conn: psycopg.Connection, seed: int) -> dict[str, int]:
    data = generate(seed)
    counts = {}
    with conn.cursor() as cur:
        for table in LOAD_ORDER:
            rows = getattr(data, table)
            cols = COLUMNS[table]
            copy_sql = sql.SQL("COPY bookstore.{} ({}) FROM STDIN").format(
                sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, cols))
            )
            with cur.copy(copy_sql) as copy:
                for row in rows:
                    copy.write_row(row)
            counts[table] = len(rows)
        for table, col in SERIAL_COLUMNS.items():
            cur.execute(
                sql.SQL("SELECT setval(pg_get_serial_sequence({}, {}), (SELECT MAX({}) FROM bookstore.{}))").format(
                    sql.Literal(f"bookstore.{table}"), sql.Literal(col), sql.Identifier(col), sql.Identifier(table)
                )
            )
    return counts


def create_readonly_role(conn: psycopg.Connection, password: str) -> None:
    role = sql.Identifier(READONLY_ROLE)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (READONLY_ROLE,))
        if cur.fetchone():
            cur.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(role, sql.Literal(password)))
        else:
            cur.execute(sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(role, sql.Literal(password)))
        statements = [
            "GRANT USAGE ON SCHEMA bookstore TO {role}",
            "GRANT SELECT ON ALL TABLES IN SCHEMA bookstore TO {role}",
            "ALTER ROLE {role} SET default_transaction_read_only = on",
            "ALTER ROLE {role} SET statement_timeout = '10s'",
            "ALTER ROLE {role} SET search_path = bookstore",
        ]
        for stmt in statements:
            cur.execute(sql.SQL(stmt).format(role=role))


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", default=os.getenv("ADMIN_DATABASE_URL"), help="Admin connection string (defaults to ADMIN_DATABASE_URL).")
    parser.add_argument("--readonly-password", default=os.getenv("READONLY_DB_PASSWORD"), help=f"If set, create/update the '{READONLY_ROLE}' login role.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.database_url:
        print("Set ADMIN_DATABASE_URL in .env or pass --database-url.", file=sys.stderr)
        return 1

    with psycopg.connect(normalize_url(args.database_url), prepare_threshold=None) as conn:
        print("Creating schema...")
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        print("Loading synthetic data...")
        counts = load_data(conn, args.seed)
        for table, n in counts.items():
            print(f"  {table:<18} {n:>7,} rows")
        if args.readonly_password:
            create_readonly_role(conn, args.readonly_password)
            print(f"Read-only role '{READONLY_ROLE}' is ready.")
        conn.commit()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
