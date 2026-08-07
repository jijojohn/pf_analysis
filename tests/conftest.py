"""Shared pytest fixtures for the Stock Analysis System test suite.

These build small, deterministic synthetic datasets so the analysis modules can
be tested without any network access or cached data.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

# Ensure the project root is importable when pytest is invoked from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_price_series(symbol, closes, start="2023-01-02"):
    """Build an OHLCV DataFrame for one symbol from a list of close prices."""
    dates = pd.bdate_range(start=start, periods=len(closes))
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame({
        "date": dates,
        "open": closes,
        "high": closes * 1.01,
        "low": closes * 0.99,
        "close": closes,
        "volume": np.full(len(closes), 100000),
        "Symbol": symbol,
    })


@pytest.fixture
def uptrend_history():
    """Combined historical data: one steady uptrend, one with a dip-and-recover."""
    n = 260
    up = 100 + np.linspace(0, 60, n) + np.sin(np.linspace(0, 12, n)) * 2
    dip = np.concatenate([
        np.linspace(100, 130, 200),       # rise
        np.linspace(130, 95, 30),          # sharp drop (oversold)
        np.linspace(95, 120, 30),          # recovery (bounce + reclaim)
    ])
    a = _make_price_series("AAA.NS", up)
    b = _make_price_series("BBB.NS", dip)
    return pd.concat([a, b], ignore_index=True)


@pytest.fixture
def benchmark_history():
    """A benchmark series that is only mildly down from its high."""
    n = 260
    closes = 1000 + np.linspace(0, 50, n)
    closes[-10:] = closes[-10:] * 0.99  # tiny pullback
    df = _make_price_series("^NSEI", closes)
    return df


@pytest.fixture
def comprehensive_dataset():
    """A small comprehensive dataset spanning bullish and bearish profiles."""
    return pd.DataFrame([
        {
            "Symbol": "AAA.NS", "CMP": 150, "RS": 8.5, "RS_Trend": "Rising", "RSI": 62,
            "WEMA21": 145, "SMA50": 140, "SMA150": 130, "SMA200": 120,
            "52wHCh%": -3, "52wLCh%": 40, "Relative_Volume": 1.2,
            "Sharpe_Ratio": 1.5, "Sortino_Ratio": 2.0, "Profit_Loss_Pct": 25,
            "Percentage_Allocation": 3.0, "Composite_Score": 82, "Stage": 2,
            "TT_Score": 8, "Signal": "Strong Buy",
        },
        {
            "Symbol": "BBB.NS", "CMP": 80, "RS": -12, "RS_Trend": "Falling", "RSI": 35,
            "WEMA21": 95, "SMA50": 100, "SMA150": 110, "SMA200": 120,
            "52wHCh%": -45, "52wLCh%": 4, "Relative_Volume": 3.5,
            "Sharpe_Ratio": -0.5, "Sortino_Ratio": -0.8, "Profit_Loss_Pct": -30,
            "Percentage_Allocation": 14.0, "Composite_Score": 28, "Stage": 4,
            "TT_Score": 1, "Signal": "Strong Sell",
        },
        {
            "Symbol": "CCC.NS", "CMP": 200, "RS": 2.0, "RS_Trend": "Flat", "RSI": 55,
            "WEMA21": 198, "SMA50": 195, "SMA150": 190, "SMA200": 185,
            "52wHCh%": -8, "52wLCh%": 25, "Relative_Volume": 1.0,
            "Sharpe_Ratio": 0.8, "Sortino_Ratio": 1.1, "Profit_Loss_Pct": 5,
            "Percentage_Allocation": 11.0, "Composite_Score": 45, "Stage": 3,
            "TT_Score": 4, "Signal": "Hold",
        },
    ])
