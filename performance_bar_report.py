#!/usr/bin/env python3
"""
Performance Bar Chart Report
=============================
Generates a horizontal bar chart report showing period returns (1W%, 1M%, 3M%, 6M%, 1Y%)
for every stock in the portfolio, sorted by 1-week return by default.

The visual style mimics mutual-fund comparison screens: green bars for positive returns,
red bars for negative, grouped by time period per stock.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works


class PerformanceBarReport:
    """Generate an HTML report with horizontal performance bars for each stock."""

    PERIOD_COLS = ['1W%', '1M%', '3M%', '6M%', '1Y%']
    PERIOD_LABELS = {'1W%': '1 Week', '1M%': '1 Month', '3M%': '3 Month', '6M%': '6 Month', '1Y%': '1 Year'}

    def __init__(self, dataset: pd.DataFrame):
        self.dataset = dataset.copy()

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def generate_report(self, timestamp: str = None) -> str:
        """Build and save the performance bar chart HTML report.

        Returns:
            Path to the generated HTML file.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d')

        output_path = f'reports/performance_bar_chart_{timestamp}.html'

        df = self.dataset.copy()

        # Ensure period columns exist
        for col in self.PERIOD_COLS:
            if col not in df.columns:
                df[col] = 0.0

        # Sort by 1-week return descending (best performers first)
        df = df.sort_values('1W%', ascending=False).reset_index(drop=True)

        # Compute max absolute return for bar scaling
        max_abs = 0.01  # avoid division by zero
        for col in self.PERIOD_COLS:
            col_max = df[col].abs().max()
            if col_max > max_abs:
                max_abs = col_max

        html = self._build_html(df, timestamp, max_abs)

        import os
        os.makedirs('reports', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"   📊 Performance bar chart report: {output_path}")
        return output_path

    # ------------------------------------------------------------------ #
    #  Private helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _bar_html(value: float, max_abs: float, width_pct: int = 100) -> str:
        """Return an inline horizontal bar + value label."""
        bar_len = abs(value) / max_abs * width_pct if max_abs else 0
        bar_len = min(bar_len, width_pct)
        color = '#3fb950' if value >= 0 else '#f85149'
        sign = '+' if value > 0 else ''
        return (
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'<div style="width:{bar_len:.1f}%;min-width:2px;height:16px;background:{color};border-radius:3px;"></div>'
            f'<span style="color:{color};font-size:0.85em;white-space:nowrap;">{sign}{value:.2f}%</span>'
            f'</div>'
        )

    def _build_html(self, df: pd.DataFrame, timestamp: str, max_abs: float) -> str:
        """Assemble full HTML document."""

        # Summary cards
        gainers_1w = (df['1W%'] > 0).sum()
        losers_1w = (df['1W%'] < 0).sum()
        best_1w = df.iloc[0] if len(df) else None
        worst_1w = df.iloc[-1] if len(df) else None
        avg_returns = {col: df[col].mean() for col in self.PERIOD_COLS}

        # --- begin HTML ---
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Bar Chart - {timestamp}</title>
    <style>
{get_base_css()}

.perf-table {{ width:100%; border-collapse:separate; border-spacing:0; font-size:0.85em; }}
.perf-table thead th {{ background:#21262d; color:#58a6ff; padding:10px 8px; text-align:left;
    position:sticky; top:0; z-index:10; cursor:pointer; white-space:nowrap;
    border-bottom:2px solid #30363d; user-select:none; }}
.perf-table thead th:first-child {{ position:sticky; left:0; z-index:15; }}
.perf-table tbody td {{ padding:8px; border-bottom:1px solid #21262d; }}
.perf-table tbody td:first-child {{ position:sticky; left:0; z-index:5;
    background:#161b22; font-weight:600; border-right:1px solid #30363d; white-space:nowrap; }}
.perf-table tbody tr:hover {{ background:#1c2128; }}
.perf-table tbody tr:hover td:first-child {{ background:#1c2128; }}
.bar-cell {{ min-width: 140px; }}
.period-header {{ text-align:center; }}
.sort-controls {{ display:flex; gap:8px; flex-wrap:wrap; margin:12px 0; }}
.sort-btn {{ background:#21262d; color:#58a6ff; padding:6px 14px; border-radius:16px;
    border:1px solid #30363d; cursor:pointer; font-size:0.85em; transition:all 0.2s; }}
.sort-btn:hover, .sort-btn.active {{ background:#30363d; border-color:#58a6ff; }}
    </style>
</head>
<body>
{get_nav_bar('Performance Bar Chart')}

<div class="container">
{get_how_it_works('Performance Bar Chart Report', [
    ('Period Returns', '1-week, 1-month, 3-month, 6-month, and 1-year percentage returns based on closing prices'),
    ('Green / Red Bars', 'Positive returns are green, negative returns are red. Bar length is proportional to the return magnitude'),
    ('Sort by Period', 'Click any column header or use the quick-sort buttons to rank stocks by a specific period'),
    ('Swing Trading', 'Use 1W% and 1M% to spot momentum shifts. Stocks flipping from red to green may signal entry points'),
    ('Long-Term View', '6M% and 1Y% reveal sustained trends versus short-term noise'),
    ('Action', 'Compare period returns across the portfolio to identify leaders (add) and laggards (trim/exit)')
])}

    <h2>📊 Portfolio Period Returns</h2>
    <div class="cards">
        <div class="card">
            <div class="label">Total Stocks</div>
            <div class="value">{len(df)}</div>
        </div>
        <div class="card">
            <div class="label">1W Gainers</div>
            <div class="value positive">{gainers_1w}</div>
        </div>
        <div class="card">
            <div class="label">1W Losers</div>
            <div class="value negative">{losers_1w}</div>
        </div>"""

        if best_1w is not None:
            html += f"""
        <div class="card">
            <div class="label">Best 1W</div>
            <div class="value positive">{best_1w['Symbol']}</div>
            <div class="sub">+{best_1w['1W%']:.2f}%</div>
        </div>"""
        if worst_1w is not None:
            html += f"""
        <div class="card">
            <div class="label">Worst 1W</div>
            <div class="value negative">{worst_1w['Symbol']}</div>
            <div class="sub">{worst_1w['1W%']:.2f}%</div>
        </div>"""

        html += """
    </div>

    <h3>📈 Average Returns by Period</h3>
    <div class="cards">"""
        for col in self.PERIOD_COLS:
            val = avg_returns[col]
            cls = 'positive' if val >= 0 else 'negative'
            sign = '+' if val > 0 else ''
            html += f"""
        <div class="card">
            <div class="label">{self.PERIOD_LABELS[col]}</div>
            <div class="value {cls}">{sign}{val:.2f}%</div>
        </div>"""

        html += """
    </div>

    <div class="sort-controls">
        <span style="color:#8b949e;line-height:30px;">Quick sort:</span>"""
        for idx, col in enumerate(self.PERIOD_COLS):
            html += f' <button class="sort-btn" onclick="sortByCol({idx + 2})">{self.PERIOD_LABELS[col]}</button>'
        html += """
    </div>

    <div class="table-wrapper">
    <table class="perf-table" id="perfTable">
        <thead><tr>
            <th onclick="sortTable(this)">Symbol</th>
            <th onclick="sortTable(this)">CMP</th>"""
        for col in self.PERIOD_COLS:
            html += f'\n            <th class="period-header bar-cell" onclick="sortTable(this)">{self.PERIOD_LABELS[col]}</th>'
        html += """
            <th onclick="sortTable(this)">Stage</th>
            <th onclick="sortTable(this)">Signal</th>
            <th onclick="sortTable(this)">Swing</th>
        </tr></thead>
        <tbody>"""

        for _, row in df.iterrows():
            symbol = row.get('Symbol', '')
            cmp = row.get('CMP', 0)
            stage = int(row.get('Stage', 0)) if pd.notna(row.get('Stage')) else 0
            signal = row.get('Signal', '')
            swing = row.get('Swing_Trend', '')

            html += f'\n        <tr>\n            <td>{symbol}</td>\n            <td>₹{cmp:,.2f}</td>'
            for col in self.PERIOD_COLS:
                val = float(row.get(col, 0))
                html += f'\n            <td class="bar-cell">{self._bar_html(val, max_abs, 80)}</td>'

            # Stage badge
            stage_colors = {1: '#8b949e', 2: '#3fb950', 3: '#d29922', 4: '#f85149'}
            stage_labels = {1: 'S1', 2: 'S2', 3: 'S3', 4: 'S4'}
            sc = stage_colors.get(stage, '#8b949e')
            sl = stage_labels.get(stage, f'S{stage}')
            html += f'\n            <td><span style="color:{sc};font-weight:600;">{sl}</span></td>'

            # Signal
            sig_color = '#3fb950' if 'Buy' in str(signal) else '#f85149' if 'Sell' in str(signal) else '#d29922'
            html += f'\n            <td style="color:{sig_color};">{signal}</td>'

            # Swing trend
            sw_color = '#3fb950' if swing == 'Bullish' else '#f85149' if swing == 'Bearish' else '#d29922'
            html += f'\n            <td style="color:{sw_color};">{swing}</td>'

            html += '\n        </tr>'

        html += f"""
        </tbody>
    </table>
    </div>

    <script>
{get_sortable_table_js()}
function sortByCol(colIdx) {{
    const table = document.getElementById('perfTable');
    const th = table.querySelectorAll('thead th')[colIdx];
    if (th) sortTable(th);
}}
    </script>

    <div style="text-align:center; padding:20px; color:#8b949e; font-size:0.85em;">
        Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Performance Bar Chart Report
    </div>
</div>
</body>
</html>"""

        return html
