"""Tests for the enhanced alert engine (backward compat + crossover events)."""

import numpy as np
import pandas as pd

from alert_engine import AlertEngine


def test_backward_compatible_without_history(comprehensive_dataset):
    """AlertEngine must still work with only the dataset (legacy call)."""
    engine = AlertEngine(comprehensive_dataset)
    alerts = engine.scan_alerts()
    assert isinstance(alerts, list)
    summary = engine.get_summary()
    assert summary["total"] == len(alerts)
    assert set(summary) >= {"total", "critical", "warning", "info", "top_alerts"}


def test_stage4_generates_critical(comprehensive_dataset):
    engine = AlertEngine(comprehensive_dataset)
    alerts = engine.scan_alerts()
    bbb = [a for a in alerts if a["symbol"] == "BBB.NS"]
    assert any(a["severity"] == "Critical" for a in bbb)


def _series(closes):
    dates = pd.bdate_range("2022-01-03", periods=len(closes))
    return pd.DataFrame({"close": np.asarray(closes, dtype=float)}, index=dates)


def test_crossover_above_sma50():
    # 58 flat bars then a dip below and a jump above -> Crossed Above SMA 50
    closes = [100.0] * 58 + [95.0, 110.0]
    engine = AlertEngine(pd.DataFrame())
    alerts = engine._check_crossovers("AAA.NS", _series(closes))
    types = {a["type"] for a in alerts}
    assert "Crossed Above SMA 50" in types


def test_crossover_below_sma50():
    closes = [100.0] * 58 + [105.0, 90.0]
    engine = AlertEngine(pd.DataFrame())
    alerts = engine._check_crossovers("AAA.NS", _series(closes))
    types = {a["type"] for a in alerts}
    assert "Crossed Below SMA 50" in types


def test_crossovers_need_min_history():
    engine = AlertEngine(pd.DataFrame())
    assert engine._check_crossovers("AAA.NS", _series([100.0] * 10)) == []


def test_relative_drawdown_flags_laggard():
    # Stock down 40% from high; benchmark flat -> underperformance warning
    stock = _series(list(np.linspace(100, 160, 200)) + list(np.linspace(160, 96, 60)))
    bench = _series(list(np.linspace(1000, 1100, 260)))
    engine = AlertEngine(pd.DataFrame(), benchmark_data=bench.reset_index().rename(columns={"index": "date"}))
    alerts = engine._check_relative_drawdown("AAA.NS", stock)
    assert any(a["type"] == "Relative Underperformance" for a in alerts)
