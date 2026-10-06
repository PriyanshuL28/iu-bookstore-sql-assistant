from datetime import date

import pandas as pd
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import FakeListChatModel
from streamlit.testing.v1 import AppTest

from sql_assistant import data_guide, pipeline
from sql_assistant.db import QueryResult


class ChannelDatabase:
    schema = "bookstore"

    def table_names(self):
        return {"orders", "order_items"}

    def schema_description(self):
        return "TABLE orders\n  channel text"

    def column_docs(self):
        return pd.DataFrame(
            [["orders", "One row per checkout.", "channel", "text", "In-Store, Online or Game Day Kiosk"]],
            columns=["table", "table_comment", "column", "type", "description"],
        )

    def preview_table(self, table, limit=5):
        return pd.DataFrame({"channel": ["Online"]})

    def run_query(self, query, max_rows=500):
        if "MIN(order_date)" in query:
            return QueryResult(pd.DataFrame([["2024-07-01", "2026-09-30"]]), False)
        return QueryResult(pd.DataFrame({"channel": ["In-Store", "Online", "Game Day Kiosk"], "revenue": [300.0, 200.0, 40.0]}), False)


FAKE_GUIDE = data_guide.DataGuide(
    first_order=date(2024, 7, 1),
    last_order=date(2026, 9, 30),
    product_types=pd.DataFrame({"category": ["Clothing"], "product_types": ["Hoodie, T-Shirt"]}),
    brands=["Nike"],
    sizes=["S", "M"],
    colors=["Crimson"],
    schools=pd.DataFrame({"school": ["Kelley School of Business"], "courses": ["BUS-K 201"]}),
    customer_types=pd.DataFrame({"customer_type": ["Student"], "customers": [10]}),
    channels=["Online"],
    payment_methods=["CrimsonCard"],
    promotions=pd.DataFrame({"name": ["Black Friday"], "discount": ["25%"]}),
    tables=pd.DataFrame({"table": ["orders"], "description": ["One row per checkout."], "columns": [["channel"]]}),
)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")
    monkeypatch.setenv("MISTRAL_API_KEY", "fake")
    fake = pipeline.SQLAssistant(
        db=ChannelDatabase(),
        llm=FakeListChatModel(responses=["SELECT channel, SUM(line_total) AS revenue FROM orders GROUP BY 1"]),
        answer_llm=FakeListChatModel(responses=["In-Store leads with $300.00."]),
        embeddings=DeterministicFakeEmbedding(size=8),
    )
    monkeypatch.setattr(pipeline.SQLAssistant, "from_settings", classmethod(lambda cls, settings, few_shot_k=None: fake))
    monkeypatch.setattr(data_guide, "load_data_guide", lambda db: FAKE_GUIDE)
    at = AppTest.from_file("../main.py", default_timeout=30)
    at.run()
    assert not at.exception
    return at


def test_welcome_screen_and_data_guide(app):
    assert any("You don't need to know SQL" in m.value for m in app.markdown)
    assert any("Kelley School of Business" in m.value for m in app.sidebar.markdown)
    assert len(app.chat_message) == 0


def test_clicking_example_question_asks_it(app):
    button = next(b for b in app.button if b.label == "Which sales channel brings in the most revenue?")
    button.click().run()
    assert not app.exception
    assert app.chat_message[0].markdown[0].value == "Which sales channel brings in the most revenue?"
    assert not any("You don't need to know SQL" in m.value for m in app.markdown)


def test_chat_flow_renders_answer_table_chart_and_sql(app):
    app.chat_input[0].set_value("Revenue by channel?").run()
    assert not app.exception
    assert any("In-Store leads" in m.value for m in app.markdown)
    assert app.main.dataframe[0].value.shape == (3, 2)
    assert "SELECT channel" in app.code[0].value
    assert [t.label for t in app.tabs] == ["Chart", "Data", "SQL"]

    app.chat_input[0].set_value("And for 2024?").run()
    assert not app.exception
    assert len(app.chat_message) == 4
