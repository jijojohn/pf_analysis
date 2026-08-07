"""Smoke test: every module in the pipeline must import cleanly."""

import importlib

import pytest

MODULES = [
    "data_utils",
    "report_style",
    "config_manager",
    "data_fetcher",
    "technical_indicators",
    "alert_engine",
    "backtest_engine",
    "sector_analyzer",
    "rebalance_advisor",
    "momentum_rotation",
    "master_report_generator",
    "stock_scorer",
    "signal_engine",
    "minervini_analyzer",
    "interactive_filter",
    "portfolio_health",
    "pf_optimizer",
    "pf_drag_analyzer",
    "performance_tracker",
    "performance_bar_report",
    "html_report_generator",
    "report_documentation",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    importlib.import_module(module_name)
