import pytest

from sql_assistant.sql_guard import UnsafeSQLError, extract_sql, validate_sql

TABLES = {"orders", "order_items", "products", "product_variants", "customers", "categories"}


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM orders",
        "SELECT p.name FROM bookstore.products p WHERE p.name ILIKE '%hoodie%'",
        "WITH t AS (SELECT order_id FROM orders) SELECT COUNT(*) FROM t",
        "SELECT order_date::date, SUM(line_total) FROM orders JOIN order_items USING (order_id) GROUP BY 1",
        "SELECT name FROM products UNION SELECT name FROM categories",
        "SELECT * FROM generate_series(1, 3)",
    ],
)
def test_allows_read_only_queries(sql):
    assert validate_sql(sql, TABLES) == sql


@pytest.mark.parametrize(
    "sql, reason",
    [
        ("DELETE FROM orders", "SELECT"),
        ("UPDATE products SET unit_price = 0", "SELECT"),
        ("DROP TABLE orders", "SELECT"),
        ("SELECT 1; DROP TABLE orders", "single"),
        ("INSERT INTO orders SELECT * FROM orders", "SELECT"),
        ("SELECT * INTO stolen FROM customers", "not allowed"),
        ("SELECT * FROM auth.users", "schema"),
        ("SELECT * FROM pg_catalog.pg_roles", "schema"),
        ("SELECT * FROM pg_shadow", "disallowed table"),
        ("SELECT pg_sleep(60)", "pg_sleep"),
        ("SELECT pg_read_file('/etc/passwd')", "pg_read_file"),
        ("SELECT * FROM orders FOR UPDATE", "locking"),
        ("WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d", "not allowed"),
        ("", "Empty"),
    ],
)
def test_rejects_unsafe_queries(sql, reason):
    with pytest.raises(UnsafeSQLError, match=reason):
        validate_sql(sql, TABLES)


def test_extract_sql_from_markdown_fence():
    reply = "Here you go:\n```sql\nSELECT 1;\n```\nHope that helps"
    assert extract_sql(reply) == "SELECT 1"


def test_extract_sql_without_fence():
    assert extract_sql("  SELECT 2 ;  ") == "SELECT 2"
