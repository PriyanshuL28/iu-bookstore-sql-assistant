from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment, falling back to Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


@dataclass(frozen=True)
class Settings:
    database_url: str
    mistral_api_key: str
    chat_model: str = "codestral-latest"
    answer_model: str = "ministral-14b-latest"
    embedding_model: str = "mistral-embed"
    db_schema: str = "bookstore"
    max_rows: int = 500
    max_attempts: int = 3
    few_shot_k: int = 3
    requests_per_second: float = 0.8

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [n for n in ("DATABASE_URL", "MISTRAL_API_KEY") if not get_setting(n)]
        if missing:
            raise RuntimeError(f"Missing required setting(s): {', '.join(missing)}. Add them to .env or Streamlit secrets.")
        return cls(
            database_url=get_setting("DATABASE_URL"),
            mistral_api_key=get_setting("MISTRAL_API_KEY"),
            chat_model=get_setting("MISTRAL_CHAT_MODEL", cls.chat_model),
            answer_model=get_setting("MISTRAL_ANSWER_MODEL", cls.answer_model),
            embedding_model=get_setting("MISTRAL_EMBEDDING_MODEL", cls.embedding_model),
        )
