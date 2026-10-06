from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd
from langchain_core.embeddings import Embeddings
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.vectorstores import InMemoryVectorStore

from sql_assistant.config import Settings
from sql_assistant.db import Database
from sql_assistant.examples import FEW_SHOT_EXAMPLES
from sql_assistant.sql_guard import extract_sql, validate_sql

CANNOT_ANSWER = "CANNOT_ANSWER"

SQL_SYSTEM_PROMPT = """You are an expert PostgreSQL analyst for the Indiana University Bookstore (a demo database with synthetic data).
Write ONE PostgreSQL query that answers the user's question.

Rules:
- Use only the tables and columns in the schema below. Do not schema-qualify table names.
- Only SELECT (optionally with WITH). Never modify data.
- Sales/revenue means SUM(order_items.line_total) over orders with status = 'Completed', unless the user asks otherwise.
- Never aggregate stock (product_variants.stock_quantity) and sales (order_items) in the same joined query; the join repeats each stock row once per sale. Compute them in separate CTEs or subqueries and combine the results.
- For categorical columns use the exact values listed in the column comments. Use ILIKE '%...%' to match product names, titles or people.
- Orders run from {first_date} to {last_date}. Treat {last_date} as "today" for relative dates like "this year" or "last month".
- Round money to 2 decimals and give every computed column a readable alias.
- For lists, add LIMIT 50 unless the user asks for a specific number or for everything.
- If the question cannot be answered from this database, reply with exactly: {cannot_answer}: <short reason>
- Reply with only the SQL inside a ```sql code block, no explanation.

Schema:
{schema}"""

ANSWER_SYSTEM_PROMPT = """You are a friendly analyst for the Indiana University Bookstore.
Answer the user's question in 1-3 sentences using ONLY the query result provided.
Format money like $1,234.56 and large counts with thousands separators.
If the result is empty or every value is null, nothing matched the question's filters: say which filters matched
nothing (using the query provided), suggest the value may not exist in the store, and point the user to the
"What's in the data" sidebar to see valid brands, product types, sizes and colors.
The result is complete unless it is explicitly marked as truncated; only then mention that just the first rows are shown.
Do not mention SQL, tables or columns."""


@dataclass
class AssistantResponse:
    question: str
    answer: str
    sql: str | None = None
    dataframe: pd.DataFrame | None = None
    truncated: bool = False
    attempts: int = 0
    error: str | None = None
    examples_used: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.error is None and self.dataframe is not None


@dataclass
class Turn:
    question: str
    sql: str


def _word_count_tokenizer():
    """Offline stand-in for Mistral's tokenizer, which the embeddings client only uses to size batches.

    Without it, the client downloads a tokenizer from Hugging Face on every startup.
    """
    from tokenizers import Tokenizer, models, pre_tokenizers

    tokenizer = Tokenizer(models.WordLevel({"[UNK]": 0}, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    return tokenizer


class SQLAssistant:
    def __init__(
        self,
        db: Database,
        llm: Runnable[list[BaseMessage], BaseMessage],
        embeddings: Embeddings | None,
        few_shot_k: int = 3,
        max_attempts: int = 3,
        max_rows: int = 500,
        answer_llm: Runnable[list[BaseMessage], BaseMessage] | None = None,
    ):
        self.db = db
        self.llm = llm
        self.answer_llm = answer_llm or llm
        self.max_attempts = max_attempts
        self.max_rows = max_rows
        self.allowed_tables = db.table_names()
        self.schema_text = db.schema_description()
        first, last = db.run_query("SELECT MIN(order_date)::date, MAX(order_date)::date FROM orders").dataframe.iloc[0]
        self.first_date, self.last_date = first, last
        self.example_selector = None
        if embeddings is not None and few_shot_k > 0:
            self.example_selector = SemanticSimilarityExampleSelector.from_examples(
                FEW_SHOT_EXAMPLES, embeddings, InMemoryVectorStore, k=few_shot_k, input_keys=["question"]
            )

    @classmethod
    def from_settings(cls, settings: Settings, few_shot_k: int | None = None) -> "SQLAssistant":
        import httpx
        from langchain_core.rate_limiters import InMemoryRateLimiter
        from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings

        # Mistral's free tier allows roughly one request per second.
        limiter = InMemoryRateLimiter(requests_per_second=settings.requests_per_second, check_every_n_seconds=0.1, max_bucket_size=1)
        def chat_model(model: str):
            return ChatMistralAI(
                model=model, api_key=settings.mistral_api_key, temperature=0, rate_limiter=limiter
            ).with_retry(retry_if_exception_type=(httpx.HTTPStatusError,), wait_exponential_jitter=True, stop_after_attempt=5)

        embeddings = MistralAIEmbeddings(
            model=settings.embedding_model, api_key=settings.mistral_api_key, tokenizer=_word_count_tokenizer()
        )
        return cls(
            db=Database(settings.database_url, schema=settings.db_schema),
            llm=chat_model(settings.chat_model),
            answer_llm=chat_model(settings.answer_model),
            embeddings=embeddings,
            few_shot_k=settings.few_shot_k if few_shot_k is None else few_shot_k,
            max_attempts=settings.max_attempts,
            max_rows=settings.max_rows,
        )

    def _sql_messages(self, question: str, history: list[Turn]) -> tuple[list[BaseMessage], list[str]]:
        system = SQL_SYSTEM_PROMPT.format(
            first_date=self.first_date,
            last_date=self.last_date,
            cannot_answer=CANNOT_ANSWER,
            schema=self.schema_text,
        )
        messages: list[BaseMessage] = [SystemMessage(system)]
        examples = self.example_selector.select_examples({"question": question}) if self.example_selector else []
        for ex in examples:
            messages += [HumanMessage(ex["question"]), AIMessage(f"```sql\n{ex['sql']}\n```")]
        for turn in history[-3:]:
            messages += [HumanMessage(turn.question), AIMessage(f"```sql\n{turn.sql}\n```")]
        messages.append(HumanMessage(question))
        return messages, [ex["question"] for ex in examples]

    def generate_and_run(self, question: str, history: list[Turn] | None = None) -> AssistantResponse:
        """Generate SQL, validate and execute it, feeding errors back to the LLM for repair."""
        messages, examples_used = self._sql_messages(question, history or [])
        response = AssistantResponse(question=question, answer="", examples_used=examples_used)
        for attempt in range(1, self.max_attempts + 1):
            response.attempts = attempt
            reply = self.llm.invoke(messages).content
            if CANNOT_ANSWER in reply:
                reason = reply.split(CANNOT_ANSWER, 1)[1].replace("`", "").lstrip(": ").strip()
                reason = reason or "It is outside what this database contains."
                response.answer = f"I can't answer that from the bookstore database. {reason}"
                response.error = CANNOT_ANSWER
                return response
            sql = extract_sql(reply)
            response.sql = sql
            try:
                validate_sql(sql, self.allowed_tables, schema=self.db.schema)
                result = self.db.run_query(sql, max_rows=self.max_rows)
            except Exception as e:
                error = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
                response.error = error
                messages += [
                    AIMessage(f"```sql\n{sql}\n```"),
                    HumanMessage(f"That query failed with this error:\n{error}\nReturn a corrected query."),
                ]
                continue
            response.error = None
            response.dataframe = result.dataframe
            response.truncated = result.truncated
            return response
        response.answer = f"Sorry, I couldn't build a working query for that question. Last error: {response.error}"
        return response

    def summarize(self, response: AssistantResponse, history: list[Turn] | None = None) -> str:
        df = response.dataframe
        preview = df.head(30).to_csv(index=False) if df is not None and not df.empty else "(no rows)"
        note = f"\n(Result truncated: showing the first {len(df)} rows.)" if response.truncated else ""
        if df is None or df.empty or df.isna().all().all():
            note += f"\n\nNo data matched. The query was:\n{response.sql}"
        context = ""
        if history:
            earlier = "\n".join(f"- {turn.question}" for turn in history[-3:])
            context = f"Earlier questions in this conversation (the latest question may be a follow-up):\n{earlier}\n\n"
        messages = [
            SystemMessage(ANSWER_SYSTEM_PROMPT),
            HumanMessage(f"{context}Question: {response.question}\n\nQuery result ({len(df)} rows):\n{preview}{note}"),
        ]
        return self.answer_llm.invoke(messages).content.strip()

    def ask(self, question: str, history: list[Turn] | None = None) -> AssistantResponse:
        start = time.perf_counter()
        response = self.generate_and_run(question, history)
        if response.ok:
            response.answer = self.summarize(response, history)
        response.elapsed_s = time.perf_counter() - start
        return response
