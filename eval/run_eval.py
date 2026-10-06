"""Execution-accuracy benchmark for the SQL assistant.

A prediction counts as correct when its result has the same number of rows as the
gold query and every gold column matches some predicted column (same values,
ignoring order, aliases and extra columns).

Usage:
    python -m eval.run_eval                 # with few-shot examples
    python -m eval.run_eval --few-shot-k 0  # zero-shot baseline
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from sql_assistant.config import Settings
from sql_assistant.pipeline import SQLAssistant

EVAL_DIR = Path(__file__).resolve().parent


def _norm(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return round(float(value), 1)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.date().isoformat() if isinstance(value, (datetime, pd.Timestamp)) else value.isoformat()
    return str(value).strip().lower()


def _column_signature(series: pd.Series) -> Counter:
    return Counter(_norm(v) for v in series.tolist())


def results_match(gold: pd.DataFrame, pred: pd.DataFrame) -> bool:
    if len(gold) != len(pred):
        return False
    remaining = [_column_signature(pred[c]) for c in pred.columns]
    for col in gold.columns:
        sig = _column_signature(gold[col])
        if sig in remaining:
            remaining.remove(sig)
        else:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--few-shot-k", type=int, default=None, help="Number of few-shot examples (0 = zero-shot).")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between questions (free-tier rate limits).")
    parser.add_argument("--ids", type=int, nargs="*", help="Only run these question ids.")
    parser.add_argument("--repeats", type=int, default=1, help="Run the suite several times; LLM output varies between runs.")
    args = parser.parse_args()

    settings = Settings.from_env()
    assistant = SQLAssistant.from_settings(settings, few_shot_k=args.few_shot_k)
    k = settings.few_shot_k if args.few_shot_k is None else args.few_shot_k
    questions = json.loads((EVAL_DIR / "questions.json").read_text(encoding="utf-8"))
    if args.ids:
        questions = [q for q in questions if q["id"] in args.ids]

    gold = {q["id"]: assistant.db.run_query(q["gold_sql"]).dataframe for q in questions}
    records = []
    for run in range(1, args.repeats + 1):
        for q in questions:
            start = time.perf_counter()
            resp = assistant.generate_and_run(q["question"])
            elapsed = time.perf_counter() - start
            correct = resp.ok and results_match(gold[q["id"]], resp.dataframe)
            records.append({
                "run": run, "id": q["id"], "difficulty": q["difficulty"], "question": q["question"], "correct": correct,
                "attempts": resp.attempts, "seconds": round(elapsed, 2), "error": resp.error, "sql": resp.sql,
            })
            print(f"[{'PASS' if correct else 'FAIL'}] run {run} #{q['id']:>2} ({resp.attempts} attempt) {q['question']}")
            time.sleep(args.delay)

    df = pd.DataFrame(records)
    per_run = df.groupby("run")["correct"].mean().mul(100)
    by_difficulty = df.groupby("difficulty")["correct"].mean().mul(100).round(1).to_dict()
    repaired = int(((df["attempts"] > 1) & df["correct"]).sum())
    print(f"\nModel: {settings.chat_model} | few-shot k={k} | {args.repeats} run(s) x {len(questions)} questions")
    print(f"Execution accuracy: {per_run.mean():.1f}% (per run: {', '.join(f'{v:.1f}%' for v in per_run)})")
    print(f"By difficulty: {by_difficulty}")
    print(f"Questions fixed by the self-correction retry: {repaired}")

    out_dir = EVAL_DIR / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"eval_k{k}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    df.to_csv(out_file, index=False)
    print(f"Details saved to {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
