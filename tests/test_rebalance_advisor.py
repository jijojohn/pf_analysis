"""Tests for the rebalance advisor."""

import pandas as pd

from rebalance_advisor import RebalanceAdvisor


def test_classify_exit_for_stage4(comprehensive_dataset):
    advisor = RebalanceAdvisor(comprehensive_dataset)
    items = {it["symbol"]: it for it in advisor.build_suggestions()}
    # BBB is Stage 4, Strong Sell, low score -> EXIT with target 0
    assert items["BBB.NS"]["action"] == "EXIT"
    assert items["BBB.NS"]["target"] == 0.0


def test_classify_trim_for_stage3(comprehensive_dataset):
    advisor = RebalanceAdvisor(comprehensive_dataset)
    items = {it["symbol"]: it for it in advisor.build_suggestions()}
    # CCC is Stage 3 -> TRIM, target reduced from current allocation
    assert items["CCC.NS"]["action"] == "TRIM"
    assert items["CCC.NS"]["target"] < items["CCC.NS"]["alloc"]


def test_add_candidate_receives_freed_capital():
    # One strong underweight ADD candidate + one EXIT freeing capital
    df = pd.DataFrame([
        {"Symbol": "GOOD.NS", "Percentage_Allocation": 2.0, "Composite_Score": 80,
         "Signal": "Strong Buy", "Stage": 2},
        {"Symbol": "BAD.NS", "Percentage_Allocation": 8.0, "Composite_Score": 20,
         "Signal": "Strong Sell", "Stage": 4},
    ])
    advisor = RebalanceAdvisor(df)
    items = {it["symbol"]: it for it in advisor.build_suggestions()}
    assert items["GOOD.NS"]["action"] == "ADD"
    # Freed 8% should push GOOD's target above its current 2%
    assert items["GOOD.NS"]["target"] > 2.0
    assert items["GOOD.NS"]["target"] <= advisor.max_position_pct


def test_delta_is_target_minus_alloc(comprehensive_dataset):
    advisor = RebalanceAdvisor(comprehensive_dataset)
    for it in advisor.build_suggestions():
        assert it["delta"] == round(it["target"] - it["alloc"], 2)


def test_empty_dataset():
    advisor = RebalanceAdvisor(pd.DataFrame())
    assert advisor.build_suggestions() == []


def test_generate_report_writes_file(comprehensive_dataset, tmp_path, monkeypatch):
    advisor = RebalanceAdvisor(comprehensive_dataset)
    monkeypatch.setattr(advisor, "reports_dir", str(tmp_path))
    path = advisor.generate_report()
    assert path.endswith(".html")
    with open(path, encoding="utf-8") as f:
        assert "Rebalance" in f.read()
