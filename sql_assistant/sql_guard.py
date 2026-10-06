"""Static checks on LLM-generated SQL before it reaches the database.

This is one layer of defense; the database connection is also read-only with a
statement timeout, so a query that slips past these checks still cannot write.
"""

from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

BLOCKED_FUNCTIONS = {
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file", "lo_import", "lo_export",
    "dblink", "dblink_exec", "set_config", "pg_terminate_backend", "pg_cancel_backend", "pg_reload_conf",
    "current_setting", "query_to_xml", "pg_advisory_lock",
}
WRITE_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter, exp.TruncateTable,
    exp.Command, exp.Grant, exp.Set, exp.Copy, exp.Into, exp.Lock,
)


class UnsafeSQLError(ValueError):
    pass


def extract_sql(text: str) -> str:
    """Pull the SQL out of an LLM reply that may include markdown fences or prose."""
    fenced = re.search(r"```(?:sql|postgresql)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    sql = fenced.group(1) if fenced else text
    return sql.strip().rstrip(";").strip()


def validate_sql(sql: str, allowed_tables: set[str], schema: str = "bookstore") -> str:
    """Return the query if it is a single read-only SELECT over allowed tables, else raise."""
    if not sql.strip():
        raise UnsafeSQLError("Empty query.")
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.ParseError as e:
        raise UnsafeSQLError(f"Could not parse SQL: {e}") from e

    if len(statements) != 1:
        raise UnsafeSQLError("Only a single SQL statement is allowed.")
    tree = statements[0]

    if not isinstance(tree, exp.Query):
        raise UnsafeSQLError("Only SELECT queries are allowed.")
    for node in tree.walk():
        if isinstance(node, WRITE_NODES):
            raise UnsafeSQLError(f"Statement type '{node.key.upper()}' is not allowed.")
        if isinstance(node, exp.Func):
            name = (node.name if isinstance(node, exp.Anonymous) else node.sql_name()).lower()
            if name in BLOCKED_FUNCTIONS:
                raise UnsafeSQLError(f"Function '{name}' is not allowed.")
        if isinstance(node, exp.Select) and node.args.get("locks"):
            raise UnsafeSQLError("Row locking clauses are not allowed.")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        db = (table.db or "").lower()
        if not name:
            continue
        if db and db != schema:
            raise UnsafeSQLError(f"Access to schema '{db}' is not allowed.")
        if not db and name in cte_names:
            continue
        if name not in allowed_tables:
            raise UnsafeSQLError(f"Unknown or disallowed table '{name}'.")
    return sql
