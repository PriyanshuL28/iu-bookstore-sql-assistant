import pandas as pd
import streamlit as st

from sql_assistant.config import Settings
from sql_assistant.data_guide import DataGuide, load_data_guide
from sql_assistant.pipeline import AssistantResponse, SQLAssistant, Turn

st.set_page_config(page_title="Ask the IU Bookstore", page_icon="📚", layout="wide")

QUESTION_TOPICS = {
    "💰 Sales & revenue": [
        "What was total revenue in each month of 2025?",
        "Which sales channel brings in the most revenue?",
        "How did Game Day Kiosk sales compare between the 2024 and 2025 football seasons?",
    ],
    "📦 Inventory": [
        "Which products need to be restocked?",
        "How many Crimson hoodies in size M are left in stock?",
        "What is our current inventory worth at list price, by category?",
    ],
    "📖 Textbooks & courses": [
        "Which Luddy courses have the most expensive required textbooks?",
        "Which textbook sold the most copies in January 2026?",
        "How many textbooks did Kelley students buy?",
    ],
    "🎓 Customers": [
        "Who are our top 10 customers by total spending?",
        "What share of in-store student orders were paid with CrimsonCard?",
        "Which states do most of our alumni customers live in?",
    ],
    "🏷️ Promotions": [
        "Which promotion generated the most revenue?",
        "How much did customers save during Black Friday 2025?",
        "How did clothing sales during Homecoming Week 2025 compare to the week before?",
    ],
    "👕 Products": [
        "What are the top 5 best-selling t-shirts?",
        "Which clothing brand made the most gross profit?",
        "Which jerseys sold best during basketball season?",
    ],
}


@st.cache_resource(show_spinner="Connecting to the database and loading examples...")
def load_assistant() -> SQLAssistant:
    return SQLAssistant.from_settings(Settings.from_env())


@st.cache_data(ttl=3600, show_spinner=False)
def get_data_guide() -> DataGuide:
    return load_data_guide(load_assistant().db)


@st.cache_data(ttl=3600, show_spinner=False)
def get_table_preview(table: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    db = load_assistant().db
    docs = db.column_docs()
    columns = docs.loc[docs["table"] == table, ["column", "type", "description"]].fillna("")
    return columns, db.preview_table(table)


def ask(question: str) -> None:
    st.session_state.pending_question = question


def pick_chart(df: pd.DataFrame):
    """Return (kind, x, y) for a simple chart when the result shape suits one."""
    if df is None or len(df) < 2 or len(df) > 60 or df.shape[1] < 2:
        return None
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not c.endswith("_id")]
    if not numeric:
        return None
    first = df.columns[0]
    if first in numeric:
        return None
    y = numeric[-1]
    sample = df[first].dropna().iloc[0]
    if hasattr(sample, "year") or pd.api.types.is_datetime64_any_dtype(df[first]):
        return "line", first, y
    return "bar", first, y


def render_result(resp: AssistantResponse) -> None:
    st.markdown(resp.answer)
    if resp.sql is None:
        return
    df = resp.dataframe
    chart = pick_chart(df) if resp.ok else None
    tabs = st.tabs(["Chart", "Data", "SQL"] if chart else ["Data", "SQL"])
    if chart:
        kind, x, y = chart
        with tabs[0]:
            plot_df = df[[x, y]].set_index(x)
            if kind == "line":
                st.line_chart(plot_df, color="#990000")
            else:
                st.bar_chart(plot_df, color="#990000", horizontal=len(df) > 8)
        tabs = tabs[1:]
    with tabs[0]:
        if df is not None:
            st.dataframe(df, width="stretch", hide_index=True)
            if resp.truncated:
                st.caption(f"Showing the first {len(df)} rows.")
        else:
            st.caption("No data.")
    with tabs[1]:
        st.code(resp.sql, language="sql")
        details = f"{resp.attempts} attempt(s) · {resp.elapsed_s:.1f}s"
        if resp.examples_used:
            details += " · similar examples: " + "; ".join(resp.examples_used)
        st.caption(details)


def render_welcome(guide: DataGuide) -> None:
    st.markdown(
        f"Ask anything about the bookstore's **products, inventory, textbooks, customers, promotions and sales** "
        f"from **{guide.first_order:%B %Y}** to **{guide.last_order:%B %Y}**. You don't need to know SQL or the "
        "table names — just ask the way you'd ask a coworker. Not sure where to start? Pick a question below, or "
        "open **What's in the data** in the sidebar to see the categories, brands, courses and promotions you can "
        "ask about."
    )
    topics = list(QUESTION_TOPICS.items())
    for row in range(0, len(topics), 3):
        for col, (topic, questions) in zip(st.columns(3), topics[row : row + 3]):
            with col.container(border=True):
                st.markdown(f"**{topic}**")
                for q in questions:
                    st.button(q, key=f"topic-{q}", on_click=ask, args=(q,), width="stretch", type="tertiary")


def render_data_guide(guide: DataGuide) -> None:
    st.subheader("What's in the data")
    st.caption(f"Orders from {guide.first_order:%b %d, %Y} to {guide.last_order:%b %d, %Y}.")
    with st.expander("🛍️ Products"):
        for _, row in guide.product_types.iterrows():
            st.markdown(f"**{row['category']}:** {row['product_types']}")
        st.markdown(f"**Sizes:** {', '.join(guide.sizes)}")
        st.markdown(f"**Colors:** {', '.join(guide.colors)}")
        st.markdown(f"**Brands:** {', '.join(guide.brands)}")
    with st.expander("📖 Textbooks & courses"):
        for _, row in guide.schools.iterrows():
            st.markdown(f"**{row['school']}:** {row['courses']}")
    with st.expander("🎓 Customers"):
        st.markdown(", ".join(f"**{r.customer_type}** ({r.customers:,})" for r in guide.customer_types.itertuples()))
    with st.expander("🧾 Orders"):
        st.markdown(f"**Channels:** {', '.join(guide.channels)}")
        st.markdown(f"**Payment methods:** {', '.join(guide.payment_methods)}")
        st.markdown("**Status:** Completed or Refunded (refunds are excluded from revenue)")
    with st.expander("🏷️ Promotions"):
        st.dataframe(guide.promotions, hide_index=True, width="stretch")
    with st.expander("🗂️ Browse tables"):
        table = st.selectbox("Table", guide.tables["table"].tolist(), label_visibility="collapsed")
        description = guide.tables.loc[guide.tables["table"] == table, "description"].iloc[0]
        if description:
            st.caption(description)
        columns, preview = get_table_preview(table)
        st.dataframe(columns, hide_index=True, width="stretch")
        st.markdown("**Sample rows**")
        st.dataframe(preview, hide_index=True, width="stretch")


st.header("Ask the IU Bookstore database 🏀")

try:
    assistant = load_assistant()
    guide = get_data_guide()
except Exception as e:
    st.error(f"Could not start the assistant: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("📚 Ask the IU Bookstore")
    st.write("A plain-English assistant for a synthetic Indiana University Bookstore database.")
    if st.session_state.messages:
        with st.popover("💡 Example questions", width="stretch"):
            for topic, questions in QUESTION_TOPICS.items():
                st.markdown(f"**{topic}**")
                for q in questions:
                    st.button(q, key=f"pop-{q}", on_click=ask, args=(q,), width="stretch", type="tertiary")
        if st.button("Clear conversation", width="stretch"):
            st.session_state.messages = []
            st.rerun()
    render_data_guide(guide)
    st.divider()
    st.caption("Mistral AI · LangChain · PostgreSQL (Supabase) · Streamlit. All data is fictional.")

question = st.chat_input("Ask a question, e.g. Which jerseys sold best during basketball season?")
question = question or st.session_state.pop("pending_question", None)

if not st.session_state.messages and not question:
    render_welcome(guide)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_result(msg["response"])

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    history = [
        Turn(m["response"].question, m["response"].sql)
        for m in st.session_state.messages
        if m["role"] == "assistant" and m["response"].ok
    ]
    with st.chat_message("assistant"):
        with st.spinner("Writing and running SQL..."):
            try:
                response = assistant.ask(question, history=history)
            except Exception as e:
                response = AssistantResponse(question=question, answer=f"Something went wrong: {e}", error=str(e))
        render_result(response)
    st.session_state.messages.append({"role": "assistant", "response": response})
