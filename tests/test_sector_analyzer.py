"""Tests for the sector rotation analyzer."""

import pandas as pd

from sector_analyzer import SectorAnalyzer


def test_aggregate_uses_default_sector_when_unmapped(comprehensive_dataset):
    analyzer = SectorAnalyzer(comprehensive_dataset)
    analyzer.sector_map = {}  # force empty map
    agg = analyzer.aggregate()
    assert list(agg.keys()) == [analyzer.default_sector]
    bucket = agg[analyzer.default_sector]
    assert bucket["count"] == 3


def test_aggregate_groups_by_mapped_sector(comprehensive_dataset):
    analyzer = SectorAnalyzer(comprehensive_dataset)
    analyzer.sector_map = {"AAA": "Tech", "BBB": "Banks", "CCC": "Tech"}
    agg = analyzer.aggregate()
    assert agg["Tech"]["count"] == 2
    assert agg["Banks"]["count"] == 1
    # Tech has higher avg RS than Banks, so it should rank first
    assert list(agg.keys())[0] == "Tech"


def test_aggregate_stage_distribution(comprehensive_dataset):
    analyzer = SectorAnalyzer(comprehensive_dataset)
    analyzer.sector_map = {}
    agg = analyzer.aggregate()
    bucket = agg[analyzer.default_sector]
    # AAA Stage 2 (bullish), BBB Stage 4 + CCC Stage 3 (bearish)
    assert bucket["bullish"] == 1
    assert bucket["bearish"] == 2


def test_aggregate_empty_dataset():
    analyzer = SectorAnalyzer(pd.DataFrame())
    assert analyzer.aggregate() == {}


def test_generate_report_writes_file(comprehensive_dataset, tmp_path, monkeypatch):
    analyzer = SectorAnalyzer(comprehensive_dataset)
    monkeypatch.setattr(analyzer, "reports_dir", str(tmp_path))
    path = analyzer.generate_report()
    assert path.endswith(".html")
    with open(path, encoding="utf-8") as f:
        assert "Sector Rotation" in f.read()
