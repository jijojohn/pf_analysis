#!/usr/bin/env python3
"""
Performance Tracker Module
Persists key portfolio metrics across runs and generates trend reports.
Storage: performance_history.json (append-only, one entry per run date).
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional
from config_manager import get_config
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works


HISTORY_FILE = "performance_history.json"


class PerformanceTracker:
    """Track portfolio metrics across runs and generate trend analysis."""

    def __init__(self, comprehensive_dataset: pd.DataFrame):
        self.dataset = comprehensive_dataset.copy()
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")
        self.history = self._load_history()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def save_run_metrics(self) -> Dict:
        """Compute and persist metrics for the current run. Returns the metrics dict."""
        metrics = self._compute_current_metrics()
        # Deduplicate: if entry for today exists, replace it
        self.history = [e for e in self.history if e.get('date') != metrics['date']]
        self.history.append(metrics)
        # Keep last 365 entries max
        self.history = self.history[-365:]
        self._save_history()
        print(f"✅ Performance metrics saved for {metrics['date']}")
        return metrics

    def generate_report(self) -> str:
        """Generate performance_trend_YYYYMMDD.html and return its path."""
        if len(self.history) < 1:
            print("⚠️  No performance history available for trend report")
            return ""

        html = self._build_html()
        os.makedirs(self.reports_dir, exist_ok=True)
        ts = date.today().strftime('%Y%m%d')
        filepath = os.path.join(self.reports_dir, f"performance_trend_{ts}.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ Performance trend report saved: {filepath}")
        return filepath

    def get_trend_summary(self) -> Dict:
        """Get a brief comparison: current vs last run vs 5-run average."""
        if not self.history:
            return {}
        current = self.history[-1]
        previous = self.history[-2] if len(self.history) >= 2 else current
        last5 = self.history[-5:] if len(self.history) >= 5 else self.history

        def delta(key):
            c = current.get(key, 0)
            p = previous.get(key, 0)
            return round(c - p, 2)

        def avg5(key):
            vals = [e.get(key, 0) for e in last5]
            return round(sum(vals) / max(len(vals), 1), 2)

        return {
            'current_date': current.get('date', ''),
            'previous_date': previous.get('date', ''),
            'total_runs': len(self.history),
            'pnl_current': current.get('total_pnl', 0),
            'pnl_delta': delta('total_pnl'),
            'return_current': current.get('portfolio_return_pct', 0),
            'return_delta': delta('portfolio_return_pct'),
            'health_current': current.get('avg_composite_score', 0),
            'health_delta': delta('avg_composite_score'),
            'avg_rsi_current': current.get('avg_rsi', 0),
            'avg_sharpe_current': current.get('avg_sharpe', 0),
            'buy_count': current.get('buy_count', 0),
            'sell_count': current.get('sell_count', 0),
            'hold_count': current.get('hold_count', 0),
            'avg5_return': avg5('portfolio_return_pct'),
            'avg5_health': avg5('avg_composite_score'),
        }

    # ------------------------------------------------------------------
    # Metrics computation
    # ------------------------------------------------------------------
    def _compute_current_metrics(self) -> Dict:
        df = self.dataset
        today_str = date.today().strftime('%Y-%m-%d')

        # Basic portfolio metrics
        total_investment = (df['DP_Bal'] * df['Hold_Price']).sum() if 'DP_Bal' in df.columns else 0
        current_value = (df['DP_Bal'] * df['CMP']).sum() if 'DP_Bal' in df.columns else 0
        total_pnl = df['Profit/Loss'].sum() if 'Profit/Loss' in df.columns else 0
        ret_pct = ((current_value - total_investment) / total_investment * 100) if total_investment > 0 else 0

        # Averages
        avg_rsi = df['RSI'].mean() if 'RSI' in df.columns else 50
        avg_sharpe = df['Sharpe_Ratio'].mean() if 'Sharpe_Ratio' in df.columns else 0
        avg_score = df['Composite_Score'].mean() if 'Composite_Score' in df.columns else 50

        # Signal distribution
        sig_dist = {}
        if 'Signal' in df.columns:
            sig_dist = df['Signal'].value_counts().to_dict()

        return {
            'date': today_str,
            'stock_count': len(df),
            'total_pnl': round(total_pnl, 2),
            'portfolio_return_pct': round(ret_pct, 2),
            'avg_composite_score': round(avg_score, 1),
            'avg_rsi': round(avg_rsi, 1),
            'avg_sharpe': round(avg_sharpe, 2),
            'buy_count': sig_dist.get('Strong Buy', 0) + sig_dist.get('Buy', 0),
            'sell_count': sig_dist.get('Strong Sell', 0) + sig_dist.get('Sell', 0),
            'hold_count': sig_dist.get('Hold', 0),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load_history(self) -> List[Dict]:
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_history(self):
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)

    # ------------------------------------------------------------------
    # HTML builder
    # ------------------------------------------------------------------
    def _build_html(self) -> str:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        hist = self.history

        # Prepare data for charts
        dates = [e['date'] for e in hist]
        pnl_vals = [e.get('total_pnl', 0) for e in hist]
        ret_vals = [e.get('portfolio_return_pct', 0) for e in hist]
        score_vals = [e.get('avg_composite_score', 50) for e in hist]
        rsi_vals = [e.get('avg_rsi', 50) for e in hist]
        sharpe_vals = [e.get('avg_sharpe', 0) for e in hist]

        # Trend summary
        summary = self.get_trend_summary()

        def arrow(val):
            if val > 0:
                return f'<span style="color:#4CAF50">▲ +{val}</span>'
            elif val < 0:
                return f'<span style="color:#f44336">▼ {val}</span>'
            return f'<span style="color:#8b949e">— {val}</span>'

        # History table
        table_rows = ""
        for e in reversed(hist[-30:]):  # show last 30 entries
            table_rows += f"""
            <tr>
                <td>{e['date']}</td>
                <td>{e.get('stock_count', 0)}</td>
                <td style="color:{'#4CAF50' if e.get('total_pnl', 0) >= 0 else '#f44336'}">₹{e.get('total_pnl', 0):,.0f}</td>
                <td style="color:{'#4CAF50' if e.get('portfolio_return_pct', 0) >= 0 else '#f44336'}">{e.get('portfolio_return_pct', 0):.2f}%</td>
                <td>{e.get('avg_composite_score', 0):.1f}</td>
                <td>{e.get('avg_rsi', 0):.0f}</td>
                <td>{e.get('avg_sharpe', 0):.2f}</td>
                <td style="color:#4CAF50">{e.get('buy_count', 0)}</td>
                <td style="color:#f44336">{e.get('sell_count', 0)}</td>
                <td style="color:#FF9800">{e.get('hold_count', 0)}</td>
            </tr>"""

        nav = get_nav_bar('Performance Trend')
        how_it_works = get_how_it_works('How This Report Works', [
            ('Tracking', 'After each analysis run, key portfolio metrics are saved to performance_history.json'),
            ('Trend Charts', 'P&L trajectory, composite score evolution, RSI & Sharpe trends visualised over time via Plotly'),
            ('Delta Indicators', '▲/▼ compare current run to previous run; 5-run average smooths short-term noise'),
            ('Run History', 'Last 30 entries with full metrics — click column headers to sort'),
        ])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Performance Trend Report</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>{get_base_css()}</style>
<script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
<h1>📈 Performance Trend Report</h1>
<p class="subtitle">Generated {ts} | {len(hist)} data points tracked</p>

<div class="cards">
  <div class="card">
    <div class="label">Portfolio Return</div>
    <div class="value" style="color:{'#4CAF50' if summary.get('return_current',0)>=0 else '#f44336'}">{summary.get('return_current',0):.2f}%</div>
    <div class="delta">vs last: {arrow(summary.get('return_delta',0))}</div>
  </div>
  <div class="card">
    <div class="label">Total P&L</div>
    <div class="value" style="color:{'#4CAF50' if summary.get('pnl_current',0)>=0 else '#f44336'}">₹{summary.get('pnl_current',0):,.0f}</div>
    <div class="delta">vs last: {arrow(summary.get('pnl_delta',0))}</div>
  </div>
  <div class="card">
    <div class="label">Health Score</div>
    <div class="value">{summary.get('health_current',0):.1f}</div>
    <div class="delta">vs last: {arrow(summary.get('health_delta',0))}</div>
  </div>
  <div class="card">
    <div class="label">5-Run Avg Return</div>
    <div class="value">{summary.get('avg5_return',0):.2f}%</div>
  </div>
  <div class="card">
    <div class="label">Signals</div>
    <div class="value" style="font-size:1em">
      <span style="color:#4CAF50">Buy {summary.get('buy_count',0)}</span> |
      <span style="color:#FF9800">Hold {summary.get('hold_count',0)}</span> |
      <span style="color:#f44336">Sell {summary.get('sell_count',0)}</span>
    </div>
  </div>
</div>

{how_it_works}

<!-- Charts -->
<div class="section">
<h2>📊 Trend Charts</h2>
<div id="pnlChart" class="chart-container"></div>
<div id="scoreChart" class="chart-container"></div>
<div id="rsiSharpeChart" class="chart-container"></div>
</div>

<!-- History Table -->
<div class="section">
<h2>📋 Run History (Last 30)</h2>
<p class="sort-hint">Click any column header to sort</p>
<div class="table-wrapper">
<table>
<thead><tr>
  <th onclick="sortTable(this)">Date</th><th onclick="sortTable(this)">Stocks</th><th onclick="sortTable(this)">P&L</th><th onclick="sortTable(this)">Return%</th><th onclick="sortTable(this)">Comp.Score</th>
  <th onclick="sortTable(this)">RSI</th><th onclick="sortTable(this)">Sharpe</th><th onclick="sortTable(this)">Buy</th><th onclick="sortTable(this)">Sell</th><th onclick="sortTable(this)">Hold</th>
</tr></thead>
<tbody>{table_rows}</tbody>
</table>
</div>
</div>

<div class="footer">
Performance Trend Report &bull; Generated by Portfolio Analysis System
</div>
</div>

<script>
var dates = {json.dumps(dates)};
var pnl = {json.dumps(pnl_vals)};
var ret = {json.dumps(ret_vals)};
var scores = {json.dumps(score_vals)};
var rsi = {json.dumps(rsi_vals)};
var sharpe = {json.dumps(sharpe_vals)};

var layout = {{
  paper_bgcolor:'#161b22', plot_bgcolor:'#0d1117',
  font:{{color:'#c9d1d9'}}, margin:{{t:40,b:40,l:60,r:30}},
  xaxis:{{gridcolor:'#21262d'}}, yaxis:{{gridcolor:'#21262d'}},
  height: 300
}};

Plotly.newPlot('pnlChart',[
  {{x:dates, y:pnl, type:'scatter', mode:'lines+markers', name:'P&L (₹)', line:{{color:'#4CAF50',width:2}}}},
  {{x:dates, y:ret, type:'scatter', mode:'lines+markers', name:'Return %', yaxis:'y2', line:{{color:'#2196F3',width:2}}}}
], Object.assign({{}}, layout, {{
  title:'P&L and Return % Over Time',
  yaxis:{{title:'P&L (₹)',gridcolor:'#21262d'}},
  yaxis2:{{title:'Return %',overlaying:'y',side:'right',gridcolor:'#21262d'}}
}}));

Plotly.newPlot('scoreChart',[
  {{x:dates, y:scores, type:'scatter', mode:'lines+markers', name:'Composite Score', fill:'tozeroy',
    line:{{color:'#FF9800',width:2}}, fillcolor:'rgba(255,152,0,0.1)'}}
], Object.assign({{}}, layout, {{title:'Avg Composite Score Trend', yaxis:{{title:'Score',range:[0,100],gridcolor:'#21262d'}}}}));

Plotly.newPlot('rsiSharpeChart',[
  {{x:dates, y:rsi, type:'scatter', mode:'lines+markers', name:'Avg RSI', line:{{color:'#9C27B0',width:2}}}},
  {{x:dates, y:sharpe, type:'scatter', mode:'lines+markers', name:'Avg Sharpe', yaxis:'y2', line:{{color:'#00BCD4',width:2}}}}
], Object.assign({{}}, layout, {{
  title:'RSI and Sharpe Ratio Trends',
  yaxis:{{title:'RSI',gridcolor:'#21262d'}},
  yaxis2:{{title:'Sharpe',overlaying:'y',side:'right',gridcolor:'#21262d'}}
}}));
</script>
</body></html>"""
        return html
