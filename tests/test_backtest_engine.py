"""Tests for the signal backtest engine."""

import numpy as np
import pandas as pd

from backtest_engine import SignalBacktester


def test_summarize_known_values():
    bt = SignalBacktester(pd.DataFrame())
    res = bt._summarize([10.0, -5.0, 20.0, -2.0])
    assert res["count"] == 4
    assert res["win_rate"] == 50.0
    assert res["avg"] == 5.75
    # expectancy = 0.5*15 + 0.5*(-3.5) = 5.75
    assert res["expectancy"] == 5.75


def test_summarize_empty():
    bt = SignalBacktester(pd.DataFrame())
    res = bt._summarize([])
    assert res == {"count": 0, "win_rate": 0.0, "avg": 0.0, "median": 0.0, "expectancy": 0.0}


def test_run_returns_expected_setups(uptrend_history):
    bt = SignalBacktester(uptrend_history)
    results = bt.run()
    assert set(results.keys()) == {
        "SMA50 Reclaim", "SMA200 Reclaim", "Golden Cross", "RSI Oversold Bounce",
    }
    # Each setup has a result for every configured horizon
    for setup, by_h in results.items():
        for h in bt.horizons:
            assert "win_rate" in by_h[h]
            assert by_h[h]["count"] >= 0


def test_dip_series_produces_oversold_bounce(uptrend_history):
    bt = SignalBacktester(uptrend_history)
    results = bt.run()
    # The engineered dip-and-recover series should yield at least one bounce event
    total_bounces = results["RSI Oversold Bounce"][bt.horizons[0]]["count"]
    assert total_bounces >= 1


def test_generate_report_writes_file(uptrend_history, tmp_path, monkeypatch):
    bt = SignalBacktester(uptrend_history)
    monkeypatch.setattr(bt, "reports_dir", str(tmp_path))
    path = bt.generate_report()
    assert path.endswith(".html")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Signal Backtest" in content
