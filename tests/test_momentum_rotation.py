"""Tests for the momentum rotation (RRG-style) analyzer."""

import pandas as pd

from momentum_rotation import MomentumRotationAnalyzer


def test_classify_assigns_quadrants(comprehensive_dataset):
    analyzer = MomentumRotationAnalyzer(comprehensive_dataset)
    buckets = analyzer.classify()
    # AAA: RS 8.5 + Rising -> Leading
    assert any(h["symbol"] == "AAA.NS" for h in buckets["Leading"])
    # BBB: RS -12 + Falling -> Lagging
    assert any(h["symbol"] == "BBB.NS" for h in buckets["Lagging"])


def test_derives_quadrant_when_column_absent():
    df = pd.DataFrame([
        {"Symbol": "UP.NS", "RS": -5, "RS_Trend": "Rising", "RS_Prev": -8},
        {"Symbol": "DOWN.NS", "RS": 6, "RS_Trend": "Falling", "RS_Prev": 10},
    ])
    buckets = MomentumRotationAnalyzer(df).classify()
    assert any(h["symbol"] == "UP.NS" for h in buckets["Improving"])
    assert any(h["symbol"] == "DOWN.NS" for h in buckets["Weakening"])


def test_prefers_existing_quadrant_column():
    df = pd.DataFrame([
        {"Symbol": "X.NS", "RS": -5, "RS_Trend": "Falling", "RS_Quadrant": "Leading"},
    ])
    buckets = MomentumRotationAnalyzer(df).classify()
    assert any(h["symbol"] == "X.NS" for h in buckets["Leading"])


def test_rs_change_computed(comprehensive_dataset):
    analyzer = MomentumRotationAnalyzer(comprehensive_dataset)
    buckets = analyzer.classify()
    leading = [h for h in buckets["Leading"] if h["symbol"] == "AAA.NS"][0]
    assert "rs_change" in leading


def test_summary_counts_and_alloc(comprehensive_dataset):
    analyzer = MomentumRotationAnalyzer(comprehensive_dataset)
    buckets = analyzer.classify()
    summ = analyzer.summary(buckets)
    total = sum(s["count"] for s in summ.values())
    assert total == len(comprehensive_dataset)


def test_empty_dataset():
    analyzer = MomentumRotationAnalyzer(pd.DataFrame())
    buckets = analyzer.classify()
    assert all(v == [] for v in buckets.values())


def test_generate_report_writes_file(comprehensive_dataset, tmp_path, monkeypatch):
    analyzer = MomentumRotationAnalyzer(comprehensive_dataset)
    monkeypatch.setattr(analyzer, "reports_dir", str(tmp_path))
    path = analyzer.generate_report()
    assert path.endswith(".html")
    with open(path, encoding="utf-8") as f:
        assert "Momentum Rotation" in f.read()
