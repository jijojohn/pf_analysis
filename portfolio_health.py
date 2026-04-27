#!/usr/bin/env python3
"""
Portfolio Health Dashboard Module
Generates a single-page health overview HTML report with traffic-light indicators,
overall health score, concentration risk, and momentum health metrics.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, date
from typing import Dict, List, Optional
from config_manager import get_config
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works


class PortfolioHealthDashboard:
    """Generate a portfolio health dashboard report."""

    def __init__(self, comprehensive_dataset: pd.DataFrame):
        self.dataset = comprehensive_dataset.copy()
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_report(self) -> str:
        """Generate portfolio_health_YYYYMMDD.html and return its path."""
        if self.dataset.empty:
            print("⚠️  No data for health dashboard")
            return ""

        metrics = self._compute_health_metrics()
        html = self._build_html(metrics)

        os.makedirs(self.reports_dir, exist_ok=True)
        ts = date.today().strftime('%Y%m%d')
        filepath = os.path.join(self.reports_dir, f"portfolio_health_{ts}.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Portfolio health dashboard saved: {filepath}")
        return filepath

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def _compute_health_metrics(self) -> Dict:
        df = self.dataset
        metrics: Dict = {}

        # Overall health score (allocation-weighted composite score)
        if 'Composite_Score' in df.columns and 'Percentage_Allocation' in df.columns:
            weights = df['Percentage_Allocation'].fillna(0)
            total_w = weights.sum()
            if total_w > 0:
                metrics['health_score'] = round((df['Composite_Score'] * weights).sum() / total_w, 1)
            else:
                metrics['health_score'] = round(df['Composite_Score'].mean(), 1)
        else:
            metrics['health_score'] = 50.0

        # Signal distribution
        if 'Signal' in df.columns:
            dist = df['Signal'].value_counts().to_dict()
        else:
            dist = {}
        metrics['signal_dist'] = dist

        # Traffic light per stock
        traffic = []
        for _, row in df.iterrows():
            sc = row.get('Composite_Score', 50)
            if sc >= 65:
                light = 'green'
            elif sc >= 40:
                light = 'yellow'
            else:
                light = 'red'
            traffic.append({
                'symbol': row.get('Symbol', '?'),
                'score': sc,
                'signal': row.get('Signal', 'Hold'),
                'light': light,
                'rs': row.get('RS', 0),
                'rsi': row.get('RSI', 50),
                'sharpe': row.get('Sharpe_Ratio', 0),
                'pl_pct': row.get('Profit_Loss_Pct', 0),
                'verdict': row.get('Signal_Verdict', ''),
            })
        metrics['traffic'] = sorted(traffic, key=lambda x: x['score'], reverse=True)

        # Concentration risk — Herfindahl index
        allocs = df['Percentage_Allocation'].fillna(0) / 100  # as fractions
        hhi = (allocs ** 2).sum()
        metrics['hhi'] = round(hhi * 10000)  # basis points
        top3_alloc = allocs.nlargest(3).sum() * 100
        metrics['top3_alloc'] = round(top3_alloc, 1)
        max_alloc = allocs.max() * 100
        metrics['max_alloc'] = round(max_alloc, 1)

        concentration_risk = 'Low'
        if max_alloc > 20 or top3_alloc > 50:
            concentration_risk = 'High'
        elif max_alloc > 15 or top3_alloc > 40:
            concentration_risk = 'Medium'
        metrics['concentration_risk'] = concentration_risk

        # Momentum health
        metrics['pct_above_wema21'] = round(len(df[df['CMP'] > df['WEMA21']]) / max(len(df), 1) * 100, 1)
        metrics['pct_above_sma200'] = round(len(df[df['CMP'] > df['SMA200']]) / max(len(df), 1) * 100, 1)
        metrics['pct_positive_rs'] = round(len(df[df['RS'] > 0]) / max(len(df), 1) * 100, 1)

        # Risk alerts
        metrics['neg_sharpe_count'] = int(len(df[df['Sharpe_Ratio'] < 0]))
        metrics['high_drawdown_count'] = int(len(df[df['52wHCh%'] < -30]))
        metrics['avg_sortino'] = round(df['Sortino_Ratio'].mean(), 2) if 'Sortino_Ratio' in df.columns else 0

        # Counts
        metrics['total_stocks'] = len(df)
        metrics['green_count'] = len([t for t in traffic if t['light'] == 'green'])
        metrics['yellow_count'] = len([t for t in traffic if t['light'] == 'yellow'])
        metrics['red_count'] = len([t for t in traffic if t['light'] == 'red'])

        return metrics

    # ------------------------------------------------------------------
    # HTML builder
    # ------------------------------------------------------------------
    def _build_html(self, m: Dict) -> str:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        hs = m['health_score']
        hs_color = '#4CAF50' if hs >= 65 else '#FF9800' if hs >= 40 else '#f44336'

        # Signal distribution bar
        sig_dist = m.get('signal_dist', {})
        total_sig = max(sum(sig_dist.values()), 1)

        # Build traffic light rows
        traffic_rows = ""
        for t in m['traffic']:
            lc = {'green': '#4CAF50', 'yellow': '#FF9800', 'red': '#f44336'}[t['light']]
            sig_badge_color = self._signal_color(t['signal'])
            traffic_rows += f"""
            <tr>
                <td style="text-align:center"><span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:{lc}"></span></td>
                <td><b>{t['symbol']}</b></td>
                <td style="text-align:center">{t['score']:.0f}</td>
                <td><span style="padding:2px 8px;border-radius:4px;background:{sig_badge_color};color:#fff;font-size:0.85em">{t['signal']}</span></td>
                <td style="text-align:center">{t['rs']:.2f}</td>
                <td style="text-align:center">{t['rsi']:.0f}</td>
                <td style="text-align:center">{t['sharpe']:.2f}</td>
                <td style="text-align:center;color:{'#4CAF50' if t['pl_pct'] >= 0 else '#f44336'}">{t['pl_pct']:.1f}%</td>
                <td style="font-size:0.82em">{t['verdict'][:120]}{'...' if len(t['verdict'])>120 else ''}</td>
            </tr>"""

        nav = get_nav_bar('Health Dashboard')
        how_it_works = get_how_it_works('How This Dashboard Works', [
            ('Health Score', 'Allocation-weighted average of all stock Composite Scores (0-100)'),
            ('Traffic Lights', '🟢 Score >= 65 (healthy) | 🟡 40-64 (caution) | 🔴 < 40 (needs attention)'),
            ('Composite Score', 'Equally-weighted across Relative Strength, Trend, Momentum, Risk & Value/Volume'),
            ('Concentration Risk', 'Herfindahl index — High if any stock > 20% or top-3 > 50% allocation'),
            ('Momentum Health', 'Percentage of stocks above key moving averages and with positive Relative Strength'),
        ])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Health Dashboard</title>
<style>{get_base_css()}
  .health-gauge {{ font-size:3em; font-weight:bold; color:{hs_color}; }}
</style>
<script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
<h1>🏥 Portfolio Health Dashboard</h1>
<p class="subtitle">Generated {ts} | {m['total_stocks']} stocks analyzed</p>

<!-- Health Score -->
<div class="cards">
  <div class="card" style="border-color:{hs_color}">
    <div class="label">Overall Health Score</div>
    <div class="health-gauge">{hs:.0f}</div>
    <div class="sub">Allocation-weighted composite score (0-100)</div>
  </div>
  <div class="card">
    <div class="label">🟢 Green</div>
    <div class="value" style="color:#4CAF50">{m['green_count']}</div>
    <div class="sub">Score ≥ 65</div>
  </div>
  <div class="card">
    <div class="label">🟡 Yellow</div>
    <div class="value" style="color:#FF9800">{m['yellow_count']}</div>
    <div class="sub">Score 40-64</div>
  </div>
  <div class="card">
    <div class="label">🔴 Red</div>
    <div class="value" style="color:#f44336">{m['red_count']}</div>
    <div class="sub">Score &lt; 40</div>
  </div>
  <div class="card">
    <div class="label">Concentration Risk</div>
    <div class="value" style="color:{'#f44336' if m['concentration_risk']=='High' else '#FF9800' if m['concentration_risk']=='Medium' else '#4CAF50'}">{m['concentration_risk']}</div>
    <div class="sub">Top-3: {m['top3_alloc']:.1f}% | Max: {m['max_alloc']:.1f}%</div>
  </div>
</div>

<!-- Signal Distribution -->
<div class="section">
<h2>📊 Signal Distribution</h2>
<div style="display:flex; gap:15px; flex-wrap:wrap; margin-bottom:10px;">
  {''.join(f'<div><span style="color:{self._signal_color(k)}">{k}</span>: <b>{v}</b> ({v/total_sig*100:.0f}%)</div>' for k,v in sig_dist.items())}
</div>
<div style="height:22px;background:#21262d;border-radius:4px;overflow:hidden;display:flex">
  {''.join(f'<div class="bar" style="width:{v/total_sig*100:.1f}%;background:{self._signal_color(k)}"></div>' for k,v in sig_dist.items())}
</div>
</div>

<!-- Momentum Health -->
<div class="section">
<h2>📈 Momentum Health</h2>
<div class="cards" style="justify-content:flex-start">
  <div class="card"><div class="label">Above Weekly EMA 21</div><div class="value">{m['pct_above_wema21']:.0f}%</div></div>
  <div class="card"><div class="label">Above SMA 200</div><div class="value">{m['pct_above_sma200']:.0f}%</div></div>
  <div class="card"><div class="label">Positive RS</div><div class="value">{m['pct_positive_rs']:.0f}%</div></div>
  <div class="card"><div class="label">Neg. Sharpe</div><div class="value" style="color:#f44336">{m['neg_sharpe_count']}</div></div>
  <div class="card"><div class="label">High Drawdown</div><div class="value" style="color:#f44336">{m['high_drawdown_count']}</div><div class="sub">52wH &lt; -30%</div></div>
  <div class="card"><div class="label">Avg Sortino</div><div class="value">{m['avg_sortino']:.2f}</div></div>
</div>
</div>

{how_it_works}

<!-- Stock Table -->
<div class="section">
<h2>🚦 Stock-by-Stock Health</h2>
<p class="sort-hint">Click any column header to sort</p>
<div class="table-wrapper">
<table>
<thead><tr>
  <th>Light</th><th onclick="sortTable(this)">Symbol</th><th onclick="sortTable(this)">Score</th>
  <th onclick="sortTable(this)">Signal</th><th onclick="sortTable(this)">RS</th><th onclick="sortTable(this)">RSI</th>
  <th onclick="sortTable(this)">Sharpe</th><th onclick="sortTable(this)">P&L%</th><th>Verdict</th>
</tr></thead>
<tbody>
{traffic_rows}
</tbody>
</table>
</div>
</div>

<div class="footer">
Portfolio Health Dashboard &bull; Generated by Portfolio Analysis System
</div>
</div>
</body></html>"""
        return html

    @staticmethod
    def _signal_color(signal: str) -> str:
        colors = {
            'Strong Buy': '#00c853', 'Buy': '#4CAF50',
            'Hold': '#FF9800',
            'Sell': '#f44336', 'Strong Sell': '#b71c1c',
        }
        return colors.get(signal, '#8b949e')
