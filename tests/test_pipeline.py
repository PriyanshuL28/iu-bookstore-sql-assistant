import pandas as pd
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import FakeListChatModel

from sql_assistant.db import QueryResult
from sql_assistant.pipeline import SQLAssistant, Turn


class FakeDatabase:
    schema = "bookstore"

    def __init__(self, fail_first: bool = False):
        self.fail_first = fail_first
        self.queries: list[str] = []

    def table_names(self):
        return {"orders", "order_items"}

    def schema_description(self):
        return "TABLE orders\n  order_id integer"

    def run_query(self, query, max_rows=500):
        self.queries.append(query)
        if "MIN(order_date)" in query:
            return QueryResult(pd.DataFrame([["2024-07-01", "2026-09-30"]]), False)
        if self.fail_first and len(self.queries) == 2:
            raise RuntimeError('column "totl" does not exist')
        return QueryResult(pd.DataFrame({"orders": [42]}), False)


def make_assistant(responses, db=None):
    return SQLAssistant(
        db=db or FakeDatabase(),
        llm=FakeListChatModel(responses=responses),
        embeddings=DeterministicFakeEmbedding(size=16),
        few_shot_k=2,
    )


def test_happy_path_returns_data_and_answer():
    assistant = make_assistant(["```sql\nSELECT COUNT(*) AS orders FROM orders\n```", "There are 42 orders."])
    resp = assistant.ask("How many orders are there?")
    assert resp.ok
    assert resp.attempts == 1
    assert resp.dataframe.iloc[0, 0] == 42
    assert resp.answer == "There are 42 orders."
    assert len(resp.examples_used) == 2


def test_database_error_is_fed_back_and_repaired():
    db = FakeDatabase(fail_first=True)
    assistant = make_assistant(["SELECT totl FROM orders", "SELECT COUNT(*) FROM orders", "42 orders."], db=db)
    resp = assistant.ask("How many orders?")
    assert resp.ok
    assert resp.attempts == 2
    assert resp.sql == "SELECT COUNT(*) FROM orders"


def test_unsafe_sql_is_never_executed():
    db = FakeDatabase()
    assistant = make_assistant(["DELETE FROM orders"] * 3, db=db)
    resp = assistant.ask("Delete everything")
    assert not resp.ok
    assert resp.attempts == 3
    assert all("DELETE" not in q for q in db.queries)


def test_out_of_scope_question():
    assistant = make_assistant(["CANNOT_ANSWER: The database has no weather data."])
    resp = assistant.ask("What's the weather in Bloomington?")
    assert not resp.ok
    assert "weather" in resp.answer


def test_conversation_history_is_included_in_prompt():
    assistant = make_assistant(["SELECT 1"])
    messages, _ = assistant._sql_messages("What about 2024?", [Turn("Revenue in 2025?", "SELECT 2025")])
    assert any("SELECT 2025" in m.content for m in messages)
    assert messages[-1].content == "What about 2024?"
