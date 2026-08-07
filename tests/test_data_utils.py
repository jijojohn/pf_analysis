"""Tests for centralized data utilities."""

import numpy as np
import pandas as pd

from data_utils import clean_close_nan, safe_float


def test_clean_close_nan_drops_nan_rows():
    df = pd.DataFrame({"close": [1.0, np.nan, 3.0], "x": [1, 2, 3]})
    out = clean_close_nan(df)
    assert len(out) == 2
    assert not out["close"].isna().any()


def test_clean_close_nan_handles_missing_column():
    df = pd.DataFrame({"x": [1, 2, 3]})
    out = clean_close_nan(df)
    assert len(out) == 3  # unchanged


def test_clean_close_nan_handles_none_and_empty():
    assert clean_close_nan(None) is None
    empty = pd.DataFrame()
    assert clean_close_nan(empty).empty


def test_safe_float_valid():
    assert safe_float("3.5") == 3.5
    assert safe_float(7) == 7.0


def test_safe_float_invalid_returns_default():
    assert safe_float(None) == 0.0
    assert safe_float(np.nan) == 0.0
    assert safe_float("abc", default=-1.0) == -1.0
    assert safe_float(np.inf) == 0.0
