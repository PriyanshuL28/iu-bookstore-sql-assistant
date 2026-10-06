"""Live summary of what's in the database, so users know what they can ask about."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sql_assistant.db import Database

SIZE_ORDER = ["YS", "YM", "YL", "XS", "S", "M", "L", "XL", "2XL", "3XL", "12x18 in", "2x3 ft", "3x5 ft"]


@dataclass
class DataGuide:
    first_order: object
    last_order: object
    product_types: pd.DataFrame
    brands: list[str]
    sizes: list[str]
    colors: list[str]
    schools: pd.DataFrame
    customer_types: pd.DataFrame
    channels: list[str]
    payment_methods: list[str]
    promotions: pd.DataFrame
    tables: pd.DataFrame


def _values(db: Database, sql: str) -> list:
    return db.run_query(sql).dataframe.iloc[:, 0].tolist()


def load_data_guide(db: Database) -> DataGuide:
    dates = db.run_query("SELECT MIN(order_date)::date, MAX(order_date)::date FROM orders").dataframe.iloc[0]
    sizes = _values(db, "SELECT DISTINCT size FROM product_variants WHERE size IS NOT NULL")
    docs = db.column_docs()
    tables = docs.groupby("table", sort=True).agg(description=("table_comment", "first"), columns=("column", list)).reset_index()
    return DataGuide(
        first_order=dates.iloc[0],
        last_order=dates.iloc[1],
        product_types=db.run_query(
            """SELECT c.name AS category, STRING_AGG(DISTINCT p.product_type, ', ') AS product_types
               FROM products p JOIN categories c ON c.category_id = p.category_id
               GROUP BY c.category_id, c.name ORDER BY c.category_id"""
        ).dataframe,
        brands=_values(db, "SELECT DISTINCT brand FROM products ORDER BY brand"),
        sizes=sorted(sizes, key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else len(SIZE_ORDER)),
        colors=_values(db, "SELECT DISTINCT color FROM product_variants WHERE color IS NOT NULL ORDER BY color"),
        schools=db.run_query(
            """SELECT school, STRING_AGG(course_code, ', ' ORDER BY course_code) AS courses
               FROM courses GROUP BY school ORDER BY school"""
        ).dataframe,
        customer_types=db.run_query(
            "SELECT customer_type, COUNT(*) AS customers FROM customers GROUP BY customer_type ORDER BY customers DESC"
        ).dataframe,
        channels=_values(db, "SELECT DISTINCT channel FROM orders ORDER BY channel"),
        payment_methods=_values(db, "SELECT DISTINCT payment_method FROM orders ORDER BY payment_method"),
        promotions=db.run_query(
            """SELECT pr.name, pr.discount_pct::int || '%' AS discount, COALESCE(c.name, 'Store-wide') AS applies_to,
                      pr.start_date, pr.end_date
               FROM promotions pr LEFT JOIN categories c ON c.category_id = pr.category_id
               ORDER BY pr.start_date"""
        ).dataframe,
        tables=tables,
    )
