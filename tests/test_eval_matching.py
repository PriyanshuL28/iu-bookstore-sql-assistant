import pandas as pd

from eval.run_eval import results_match


def test_ignores_aliases_column_order_and_extra_columns():
    gold = pd.DataFrame({"sum": [123.456]})
    pred = pd.DataFrame({"category": ["Clothing"], "revenue": [123.46]})
    assert results_match(gold, pred)


def test_ignores_row_order():
    gold = pd.DataFrame({"a": ["x", "y"], "b": [1, 2]})
    pred = pd.DataFrame({"b": [2, 1], "a": ["y", "x"]})
    assert results_match(gold, pred)


def test_rejects_wrong_values_or_row_counts():
    gold = pd.DataFrame({"n": [10]})
    assert not results_match(gold, pd.DataFrame({"n": [11]}))
    assert not results_match(gold, pd.DataFrame({"n": [10, 10]}))
