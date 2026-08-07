#!/usr/bin/env python3
"""
Sector Rotation Analyzer
========================
Groups portfolio holdings by sector and surfaces macro themes that per-stock
reports hide — e.g. "all IT names are in Stage 2 while banks are in Stage 4".

Sectors come from a user-maintained map in config.json
(``sector_settings.sector_map``: { "RELIANCE": "Energy", ... }). Symbols not in
the map fall back to ``sector_settings.default_sector`` ("Unclassified"), so the
report degrades gracefully when the map is empty.

Output: sector_rotation_YYYYMMDD.html — sector leaderboard (by avg RS / composite
score) and a stage-distribution breakdown per sector.
"""

import os
from collections import defaultdict
from datetime import date, datetime
from typing import Dict

import numpy as np
import pandas as pd

from config_manager import get_config
from data_utils import safe_float
from report_style import (
    get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works, render_table,
)


def _base_symbol(symbol: str) -> str:
    for suffix in ('.NS', '.BO'):
        if symbol.endswith(suffix):
            return symbol[:-len(suffix)]
    return symbol


class SectorAnalyzer:
    """Aggregate portfolio metrics by sector and rank sector strength."""

    def __init__(self, comprehensive_dataset: pd.DataFrame):
        self.dataset = comprehensive_dataset  # read-only reference
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")
        sec_cfg = self.config.get_setting("sector_settings", {})
        self.sector_map: Dict[str, str] = sec_cfg.get("sector_map", {}) or {}
        self.default_sector: str = sec_cfg.get("default_sector", "Unclassified")

    def _sector_for(self, symbol: str) -> str:
        if symbol in self.sector_map:
            return self.sector_map[symbol]
        base = _base_symbol(symbol)
        if base in self.sector_map:
            return self.sector_map[base]
        return self.default_sector

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    def aggregate(self) -> Dict[str, Dict]:
        """Return {sector: {metrics...}} sorted by avg RS descending."""
        buckets: Dict[str, list] = defaultdict(list)
        if self.dataset.empty or 'Symbol' not in self.dataset.columns:
            return {}
        for _, row in self.dataset.iterrows():
            sector = self._sector_for(str(row.get('Symbol', '')))
            buckets[sector].append(row)

        agg: Dict[str, Dict] = {}
        for sector, rows in buckets.items():
            n = len(rows)
            rs_vals = [safe_float(r.get('RS')) for r in rows]
            comp_vals = [safe_float(r.get('Composite_Score'), 50.0) for r in rows]
            pl_vals = [safe_float(r.get('Profit_Loss_Pct', r.get('Profit/Loss'))) for r in rows]
            alloc_vals = [safe_float(r.get('Percentage_Allocation')) for r in rows]
            stage_counts = defaultdict(int)
            for r in rows:
                stage = r.get('Stage')
                try:
                    stage = int(stage) if not pd.isna(stage) else 0
                except (TypeError, ValueError):
                    stage = 0
                stage_counts[stage] += 1
            bullish = stage_counts.get(1, 0) + stage_counts.get(2, 0)
            bearish = stage_counts.get(3, 0) + stage_counts.get(4, 0)
            agg[sector] = {
                'count': n,
                'avg_rs': round(float(np.mean(rs_vals)), 2) if rs_vals else 0.0,
                'avg_score': round(float(np.mean(comp_vals)), 1) if comp_vals else 0.0,
                'avg_pl': round(float(np.mean(pl_vals)), 2) if pl_vals else 0.0,
                'allocation': round(float(np.sum(alloc_vals)), 2),
                'stage_counts': dict(stage_counts),
                'bullish': bullish,
                'bearish': bearish,
                'symbols': [str(r.get('Symbol', '')) for r in rows],
            }

        # Sort by avg RS desc
        return dict(sorted(agg.items(), key=lambda kv: kv[1]['avg_rs'], reverse=True))

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def generate_report(self) -> str:
        agg = self.aggregate()
        os.makedirs(self.reports_dir, exist_ok=True)
        ts = date.today().strftime('%Y%m%d')
        filepath = os.path.join(self.reports_dir, f"sector_rotation_{ts}.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self._build_html(agg))
        mapped = sum(1 for s in self.dataset.get('Symbol', []) if self._sector_for(str(s)) != self.default_sector)
        print(f"✅ Sector rotation report saved: {filepath} ({len(agg)} sectors, {mapped} mapped symbols)")
        return filepath

    def _build_html(self, agg: Dict[str, Dict]) -> str:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        nav = get_nav_bar('Sector Rotation')
        how = get_how_it_works('How This Report Works', [
            ('Sector Map', 'Sectors come from config.json → sector_settings.sector_map. Unmapped symbols are grouped as "Unclassified".'),
            ('Avg RS', 'Average Relative Strength of holdings in the sector — positive means the sector outperforms the benchmark.'),
            ('Stage Mix', 'Minervini stage distribution: bullish (Stage 1/2) vs bearish (Stage 3/4) reveals rotation.'),
            ('Leaderboard', 'Sectors are ranked by average RS — the top rows are where leadership currently sits.'),
            ('Action', 'Favour adding in top-ranked bullish sectors; trim exposure in bottom-ranked bearish sectors.'),
        ])

        leaders_rows = []
        for sector, m in agg.items():
            rs_class = 'positive' if m['avg_rs'] > 0 else 'negative'
            pl_class = 'positive' if m['avg_pl'] > 0 else 'negative'
            tilt = 'Bullish' if m['bullish'] > m['bearish'] else 'Bearish' if m['bearish'] > m['bullish'] else 'Mixed'
            tilt_class = 'positive' if tilt == 'Bullish' else 'negative' if tilt == 'Bearish' else 'neutral'
            leaders_rows.append([
                {'text': sector, 'html': False},
                {'text': m['count']},
                {'text': f"{m['avg_rs']:+.2f}", 'class': rs_class},
                {'text': f"{m['avg_score']:.1f}"},
                {'text': f"{m['avg_pl']:+.2f}%", 'class': pl_class},
                {'text': f"{m['allocation']:.1f}%"},
                {'text': f"{m['bullish']} / {m['bearish']}"},
                {'text': tilt, 'class': tilt_class},
            ])

        leaderboard = render_table(
            ['Sector', 'Holdings', 'Avg RS', 'Avg Score', 'Avg P/L', 'Allocation', 'Bull/Bear', 'Tilt'],
            leaders_rows,
        ) if leaders_rows else "<p style='color:#8b949e'>No holdings to analyze.</p>"

        # Stage distribution detail
        stage_rows = []
        for sector, m in agg.items():
            sc = m['stage_counts']
            stage_rows.append([
                {'text': sector, 'html': False},
                {'text': sc.get(1, 0)},
                {'text': sc.get(2, 0)},
                {'text': sc.get(3, 0)},
                {'text': sc.get(4, 0)},
                {'text': ', '.join(m['symbols'][:8]) + ('…' if len(m['symbols']) > 8 else ''), 'class': 'methodology-cell'},
            ])
        stage_table = render_table(
            ['Sector', 'Stage 1', 'Stage 2', 'Stage 3', 'Stage 4', 'Symbols'],
            stage_rows, sort_hint=False,
        ) if stage_rows else ""

        unmapped_note = ""
        if not self.sector_map:
            unmapped_note = (
                "<div class='methodology'>💡 No sector map configured yet. Add a "
                "<code>sector_settings.sector_map</code> object to <code>config.json</code> "
                "(e.g. <code>{\"RELIANCE\": \"Energy\"}</code>) to unlock full rotation insights.</div>"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sector Rotation</title>
<style>{get_base_css()}
  .methodology-cell {{ color:#8b949e; font-size:0.85em; white-space:normal; }}
  code {{ background:#161b22; padding:1px 5px; border-radius:4px; color:#79c0ff; }}
</style>
<script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
<h1>🔄 Sector Rotation Analysis</h1>
<p class="subtitle">Generated {ts} | {len(agg)} sectors</p>
{how}
{unmapped_note}
<div class="section">
<h2>🏆 Sector Leaderboard (by Avg RS)</h2>
{leaderboard}
</div>
<div class="section">
<h2>📊 Stage Distribution by Sector</h2>
{stage_table}
</div>
<div class="footer">Sector Rotation &bull; Generated by Portfolio Analysis System</div>
</div>
</body></html>"""
