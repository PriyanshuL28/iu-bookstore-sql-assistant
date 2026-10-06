from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
import psycopg
from psycopg import sql as pgsql

SCHEMA_QUERY = """
SELECT c.table_name,
       obj_description(format('%%I.%%I', c.table_schema, c.table_name)::regclass, 'pg_class') AS table_comment,
       c.column_name,
       c.data_type,
       col_description(format('%%I.%%I', c.table_schema, c.table_name)::regclass, c.ordinal_position) AS column_comment
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name AND t.table_type = 'BASE TABLE'
WHERE c.table_schema = %s
ORDER BY c.table_name, c.ordinal_position
"""

FOREIGN_KEY_QUERY = """
SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table, ccu.column_name AS ref_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s
ORDER BY tc.table_name, kcu.column_name
"""


@dataclass
class QueryResult:
    dataframe: pd.DataFrame
    truncated: bool


def normalize_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")


class Database:
    def __init__(self, url: str, schema: str = "bookstore", statement_timeout_ms: int = 10_000):
        self.url = normalize_url(url)
        self.schema = schema
        self.statement_timeout_ms = statement_timeout_ms

    def connect(self) -> psycopg.Connection:
        # prepare_threshold=None keeps this compatible with Supabase's transaction pooler.
        return psycopg.connect(self.url, prepare_threshold=None, connect_timeout=10)

    def _execute_readonly(self, conn: psycopg.Connection, query: str, params=None):
        cur = conn.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute(pgsql.SQL("SET LOCAL statement_timeout = {}").format(pgsql.Literal(self.statement_timeout_ms)))
        cur.execute(pgsql.SQL("SET LOCAL search_path = {}").format(pgsql.Identifier(self.schema)))
        cur.execute(query, params)
        return cur

    def table_names(self) -> set[str]:
        with self.connect() as conn:
            cur = self._execute_readonly(
                conn,
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (self.schema,),
            )
            return {row[0] for row in cur.fetchall()}

    def column_docs(self) -> pd.DataFrame:
        """One row per column with its type and documentation comment."""
        with self.connect() as conn:
            rows = self._execute_readonly(conn, SCHEMA_QUERY, (self.schema,)).fetchall()
        return pd.DataFrame(rows, columns=["table", "table_comment", "column", "type", "description"])

    def preview_table(self, table: str, limit: int = 5) -> pd.DataFrame:
        if table not in self.table_names():
            raise ValueError(f"Unknown table '{table}'.")
        return self.run_query(f'SELECT * FROM "{table}" LIMIT {int(limit)}', max_rows=limit).dataframe

    def schema_description(self) -> str:
        """Compact, comment-annotated description of every table, for the LLM prompt."""
        with self.connect() as conn:
            columns = self._execute_readonly(conn, SCHEMA_QUERY, (self.schema,)).fetchall()
            fks = conn.execute(FOREIGN_KEY_QUERY, (self.schema,)).fetchall()

        refs = {(t, c): f"{rt}.{rc}" for t, c, rt, rc in fks}
        lines: list[str] = []
        current = None
        for table, table_comment, column, data_type, column_comment in columns:
            if table != current:
                if current is not None:
                    lines.append("")
                header = f"TABLE {table}"
                if table_comment:
                    header += f"  -- {table_comment}"
                lines.append(header)
                current = table
            line = f"  {column} {data_type}"
            if (table, column) in refs:
                line += f" REFERENCES {refs[(table, column)]}"
            if column_comment:
                line += f"  -- {column_comment}"
            lines.append(line)
        return "\n".join(lines)

    def run_query(self, query: str, max_rows: int = 500) -> QueryResult:
        with self.connect() as conn:
            cur = self._execute_readonly(conn, query)
            columns = [d.name for d in cur.description]
            rows = cur.fetchmany(max_rows + 1)
            conn.rollback()
        truncated = len(rows) > max_rows
        df = pd.DataFrame(rows[:max_rows], columns=columns)
        for col in df.columns:
            if df[col].map(lambda v: isinstance(v, Decimal)).any():
                df[col] = df[col].map(lambda v: float(v) if isinstance(v, Decimal) else v)
        return QueryResult(dataframe=df, truncated=truncated)
