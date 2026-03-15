"""
Mark Minervini Stage Analysis Module
=====================================
Implements the 4-stage stock cycle framework and 8-point Trend Template
from Mark Minervini's methodology (Trade Like a Stock Market Wizard).

Stages:
  Stage 1 (Basing/Accumulation): Price consolidating, MAs flattening
  Stage 2 (Advancing): Bullish MA stack, trending up — BUY ZONE
  Stage 3 (Topping/Distribution): MAs converging, price losing momentum
  Stage 4 (Declining): Bearish MA stack, price below all MAs — AVOID

Trend Template (8 criteria for Stage 2 qualification):
  1. Price > SMA150 and Price > SMA200
  2. SMA150 > SMA200
  3. SMA200 trending up for ≥1 month (22 trading days)
  4. SMA50 > SMA150 and SMA50 > SMA200
  5. Price > SMA50
  6. Price ≥25% above 52-week low
  7. Price within 25% of 52-week high
  8. RS > 0 (outperforming benchmark)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works


class MinerviniAnalyzer:
    """Classifies stocks into Minervini's 4 stages and evaluates Trend Template criteria."""

    def __init__(self, config: dict = None):
        """Initialize with optional config overrides."""
        self.config = config or {}
        # Configurable thresholds
        self.min_above_52w_low = self.config.get('min_above_52w_low', 25)   # Criterion 6: ≥25% above 52w low
        self.max_below_52w_high = self.config.get('max_below_52w_high', 25)  # Criterion 7: within 25% of 52w high
        self.sma200_trend_days = self.config.get('sma200_trend_days', 22)    # Criterion 3: ~1 month

    def evaluate_trend_template(self, row: pd.Series) -> Dict:
        """
        Evaluate the 8-point Trend Template for a single stock.
        
        Returns dict with:
          - criteria: list of 8 dicts (name, passed, value, threshold)
          - tt_score: count of passed criteria (0-8)
          - passed: True if tt_score >= 6
        """
        cmp = _safe(row, 'CMP', 0)
        sma50 = _safe(row, 'SMA50', 0)
        sma150 = _safe(row, 'SMA150', 0)
        sma200 = _safe(row, 'SMA200', 0)
        sma200_slope = _safe(row, 'SMA200_Slope', 0)
        high_52w_chg = _safe(row, '52wHCh%', -100)
        low_52w_chg = _safe(row, '52wLCh%', 0)
        rs = _safe(row, 'RS', 0)

        criteria = [
            {
                'name': 'Price > SMA150 & SMA200',
                'passed': cmp > sma150 and cmp > sma200,
                'value': f'CMP={cmp:.1f}, SMA150={sma150:.1f}, SMA200={sma200:.1f}',
                'description': 'Stock trading above both long-term moving averages'
            },
            {
                'name': 'SMA150 > SMA200',
                'passed': sma150 > sma200,
                'value': f'SMA150={sma150:.1f}, SMA200={sma200:.1f}',
                'description': 'Medium-term trend stronger than long-term'
            },
            {
                'name': 'SMA200 trending up ≥1 month',
                'passed': sma200_slope > 0,
                'value': f'Slope={sma200_slope:.2f}%',
                'description': f'SMA200 rising over last {self.sma200_trend_days} trading days'
            },
            {
                'name': 'SMA50 > SMA150 & SMA200',
                'passed': sma50 > sma150 and sma50 > sma200,
                'value': f'SMA50={sma50:.1f}, SMA150={sma150:.1f}, SMA200={sma200:.1f}',
                'description': 'Short-term trend leading — bullish MA stack'
            },
            {
                'name': 'Price > SMA50',
                'passed': cmp > sma50,
                'value': f'CMP={cmp:.1f}, SMA50={sma50:.1f}',
                'description': 'Stock above short-term moving average'
            },
            {
                'name': f'Price ≥{self.min_above_52w_low}% above 52w Low',
                'passed': low_52w_chg >= self.min_above_52w_low,
                'value': f'{low_52w_chg:.1f}%',
                'description': 'Sufficient distance from 52-week low shows strength'
            },
            {
                'name': f'Price within {self.max_below_52w_high}% of 52w High',
                'passed': abs(high_52w_chg) <= self.max_below_52w_high,
                'value': f'{high_52w_chg:.1f}%',
                'description': 'Near highs — not in deep correction'
            },
            {
                'name': 'RS > 0 (outperforming benchmark)',
                'passed': rs > 0,
                'value': f'RS={rs:.2f}',
                'description': 'Relative strength positive vs NIFTY 50'
            }
        ]

        tt_score = sum(1 for c in criteria if c['passed'])

        return {
            'criteria': criteria,
            'tt_score': tt_score,
            'passed': tt_score >= 6
        }

    def classify_stage(self, row: pd.Series) -> Dict:
        """
        Classify a stock into one of 4 Minervini stages.
        
        Returns dict with:
          - stage: int (1-4)
          - stage_name: str
          - description: str
          - action: str (recommended action)
          - tt_result: trend template evaluation dict
        """
        tt = self.evaluate_trend_template(row)
        tt_score = tt['tt_score']

        cmp = _safe(row, 'CMP', 0)
        sma50 = _safe(row, 'SMA50', 0)
        sma150 = _safe(row, 'SMA150', 0)
        sma200 = _safe(row, 'SMA200', 0)
        sma200_slope = _safe(row, 'SMA200_Slope', 0)

        # --- Stage 2 (Advancing) ---
        # Bullish MA stack + passes most Trend Template criteria
        ma_stack_bullish = sma50 > sma150 > sma200
        if tt_score >= 6 and ma_stack_bullish:
            return {
                'stage': 2,
                'stage_name': 'Stage 2 — Advancing',
                'description': 'Uptrend confirmed. Bullish MA stack with strong trend template.',
                'action': 'Buy / Add on pullbacks to SMA50',
                'tt_result': tt
            }

        # --- Stage 4 (Declining) ---
        # Bearish MA stack OR price below all MAs with declining SMA200
        ma_stack_bearish = sma50 < sma150 < sma200
        price_below_all = cmp < sma50 and cmp < sma150 and cmp < sma200
        if (ma_stack_bearish and price_below_all) or (price_below_all and sma200_slope < 0):
            return {
                'stage': 4,
                'stage_name': 'Stage 4 — Declining',
                'description': 'Downtrend confirmed. Bearish MA stack, avoid new positions.',
                'action': 'Sell / Exit — do not hold',
                'tt_result': tt
            }

        # --- Stage 3 (Topping/Distribution) ---
        # Price dropped below SMA50, MAs starting to converge
        price_below_sma50 = cmp < sma50
        mas_converging = abs(sma50 - sma150) / sma150 < 0.03 if sma150 > 0 else False
        was_advancing = sma150 > sma200  # Still has remnant bullish structure
        if price_below_sma50 and (mas_converging or was_advancing) and not ma_stack_bearish:
            return {
                'stage': 3,
                'stage_name': 'Stage 3 — Topping',
                'description': 'Distribution phase. MAs converging, momentum fading.',
                'action': 'Take profits / Tighten stop-loss',
                'tt_result': tt
            }

        # --- Stage 1 (Basing/Accumulation) ---
        # Default: price near SMA200, MAs flattening, doesn't qualify for 2/3/4
        return {
            'stage': 1,
            'stage_name': 'Stage 1 — Basing',
            'description': 'Consolidation phase. Price near SMA200, MAs flattening.',
            'action': 'Watch — wait for Stage 2 breakout',
            'tt_result': tt
        }

    def analyze_dataset(self, dataset: pd.DataFrame) -> pd.DataFrame:
        """
        Add Minervini stage columns to the comprehensive dataset.
        
        Adds columns: Stage, Stage_Name, TT_Score, Stage_Action
        """
        if dataset.empty:
            dataset['Stage'] = []
            dataset['Stage_Name'] = []
            dataset['TT_Score'] = []
            dataset['Stage_Action'] = []
            return dataset

        stages = []
        stage_names = []
        tt_scores = []
        actions = []

        for _, row in dataset.iterrows():
            result = self.classify_stage(row)
            stages.append(result['stage'])
            stage_names.append(result['stage_name'])
            tt_scores.append(result['tt_result']['tt_score'])
            actions.append(result['action'])

        dataset['Stage'] = stages
        dataset['Stage_Name'] = stage_names
        dataset['TT_Score'] = tt_scores
        dataset['Stage_Action'] = actions

        # Print summary
        stage_counts = dataset['Stage'].value_counts().sort_index()
        print(f"\n📊 Minervini Stage Distribution:")
        stage_labels = {1: 'Basing', 2: 'Advancing', 3: 'Topping', 4: 'Declining'}
        for s in [1, 2, 3, 4]:
            count = stage_counts.get(s, 0)
            pct = (count / len(dataset)) * 100 if len(dataset) > 0 else 0
            print(f"   Stage {s} ({stage_labels[s]}): {count} stocks ({pct:.1f}%)")
        
        tt_pass = (dataset['TT_Score'] >= 7).sum()
        print(f"   📋 Full Trend Template (7+/8): {tt_pass} stocks")

        return dataset

    def generate_report(self, dataset: pd.DataFrame, timestamp: str = None) -> str:
        """
        Generate the Minervini Stage Analysis HTML report.
        
        Returns the output file path.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d')

        output_path = f'reports/minervini_stage_analysis_{timestamp}.html'

        # Ensure stage columns exist
        if 'Stage' not in dataset.columns:
            dataset = self.analyze_dataset(dataset)

        total = len(dataset)
        stage_counts = {s: (dataset['Stage'] == s).sum() for s in [1, 2, 3, 4]}
        stage_pcts = {s: (c / total * 100) if total > 0 else 0 for s, c in stage_counts.items()}

        # Stage 2 stocks sorted by TT_Score
        stage2_df = dataset[dataset['Stage'] == 2].sort_values('TT_Score', ascending=False)
        # Full TT pass (7+/8)
        full_tt_df = dataset[dataset['TT_Score'] >= 7].sort_values('TT_Score', ascending=False)
        # Exit candidates (Stage 3 & 4)
        exit_df = dataset[dataset['Stage'].isin([3, 4])].sort_values('Stage')
        # Basing (potential breakouts)
        basing_df = dataset[dataset['Stage'] == 1].sort_values('TT_Score', ascending=False)

        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minervini Stage Analysis - {timestamp}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
{get_base_css()}

.stage-cards {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 24px 0;
}}
.stage-card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}}
.stage-card.s1 {{ border-top: 3px solid #8b949e; }}
.stage-card.s2 {{ border-top: 3px solid #3fb950; }}
.stage-card.s3 {{ border-top: 3px solid #d29922; }}
.stage-card.s4 {{ border-top: 3px solid #f85149; }}
.stage-card .count {{
    font-size: 2.5em;
    font-weight: bold;
    color: #e6edf3;
    margin: 8px 0;
}}
.stage-card .label {{
    font-size: 0.9em;
    color: #8b949e;
}}
.stage-card .pct {{
    font-size: 1.1em;
    color: #58a6ff;
}}
.stage-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.85em;
    font-weight: 600;
}}
.stage-badge.s1 {{ background: #21262d; color: #8b949e; }}
.stage-badge.s2 {{ background: #0d2818; color: #3fb950; }}
.stage-badge.s3 {{ background: #2d2000; color: #d29922; }}
.stage-badge.s4 {{ background: #2d0000; color: #f85149; }}
.tt-pass {{ color: #3fb950; font-weight: bold; }}
.tt-fail {{ color: #f85149; }}
.tt-score {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
}}
.tt-score.high {{ background: #0d2818; color: #3fb950; }}
.tt-score.mid {{ background: #2d2000; color: #d29922; }}
.tt-score.low {{ background: #2d0000; color: #f85149; }}
.section-header {{
    border-bottom: 2px solid #58a6ff;
    padding-bottom: 8px;
    margin: 32px 0 16px 0;
    color: #e6edf3;
}}
.key-takeaway {{
    background: #161b22;
    border-left: 4px solid #58a6ff;
    padding: 16px 20px;
    margin: 16px 0;
    border-radius: 0 8px 8px 0;
}}
.key-takeaway h4 {{ margin: 0 0 8px 0; color: #58a6ff; }}
.methodology {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
    font-size: 0.9em;
}}
@media (max-width: 768px) {{
    .stage-cards {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media (max-width: 480px) {{
    .stage-cards {{ grid-template-columns: 1fr; }}
}}
    </style>
</head>
<body>
{get_nav_bar('Minervini Stage Analysis')}

<div class="container">
{get_how_it_works('Minervini Stage Analysis', [
    ('4-Stage Classification', 'Each stock is classified as Basing (1), Advancing (2), Topping (3), or Declining (4)'),
    ('8-Point Trend Template', 'Evaluates SMA 50/150/200, 52-week range, and RS to score trend strength (0-8)'),
    ('Buy Zone', 'Stage 2 (Advancing) with bullish MA stack and strong trend — ideal for entries'),
    ('Exit Candidates', 'Stage 3/4 — take profits or cut losses before further decline'),
    ('TT Score', 'Count of 8 criteria passed. 7+/8 = strongest setups, drives Momentum score'),
    ('Stage Signals', 'Buy signals require Stage 1/2. Stage 3/4 generate bearish factors in Signal Engine')
])}

    <h2>📊 Stage Distribution</h2>
    <div class="stage-cards">
        <div class="stage-card s1">
            <div class="label">Stage 1 — Basing</div>
            <div class="count">{stage_counts[1]}</div>
            <div class="pct">{stage_pcts[1]:.1f}%</div>
            <div class="label">Watch for breakout</div>
        </div>
        <div class="stage-card s2">
            <div class="label">Stage 2 — Advancing</div>
            <div class="count">{stage_counts[2]}</div>
            <div class="pct">{stage_pcts[2]:.1f}%</div>
            <div class="label">✅ Buy Zone</div>
        </div>
        <div class="stage-card s3">
            <div class="label">Stage 3 — Topping</div>
            <div class="count">{stage_counts[3]}</div>
            <div class="pct">{stage_pcts[3]:.1f}%</div>
            <div class="label">⚠️ Take Profits</div>
        </div>
        <div class="stage-card s4">
            <div class="label">Stage 4 — Declining</div>
            <div class="count">{stage_counts[4]}</div>
            <div class="pct">{stage_pcts[4]:.1f}%</div>
            <div class="label">🚫 Exit / Avoid</div>
        </div>
    </div>

    <div id="stageChart" style="min-height:350px;"></div>

    <div class="key-takeaway">
        <h4>🔑 Key Takeaways</h4>
        <ul>
            <li><strong>{stage_counts[2]}</strong> stocks ({stage_pcts[2]:.0f}%) in Stage 2 — actively advancing, suitable for buying or adding</li>
            <li><strong>{(dataset['TT_Score'] >= 7).sum()}</strong> stocks pass the full Trend Template (7+/8 criteria) — the strongest setups</li>
            <li><strong>{stage_counts[3] + stage_counts[4]}</strong> stocks ({stage_pcts[3] + stage_pcts[4]:.0f}%) in Stage 3/4 — consider exiting or tightening stops</li>
            <li><strong>{stage_counts[1]}</strong> stocks ({stage_pcts[1]:.0f}%) in Stage 1 — basing, watch for potential breakout into Stage 2</li>
        </ul>
    </div>
"""

        # Stage 2 table (Buy Zone)
        html += self._generate_stage_table(
            stage2_df, 'Stage 2 — Advancing (Buy Zone)',
            '🟢 These stocks have a bullish MA stack (SMA50 > SMA150 > SMA200) and pass ≥6/8 Trend Template criteria. Ideal for swing trades and position building.',
            's2'
        )

        # Full Trend Template table
        html += self._generate_stage_table(
            full_tt_df, 'Full Trend Template (7+/8 Criteria)',
            '⭐ The strongest setups — stocks passing 7 or more of 8 Trend Template criteria. These represent the highest conviction opportunities.',
            's2'
        )

        # Stage 3/4 Exit candidates
        html += self._generate_stage_table(
            exit_df, 'Stage 3/4 — Exit Candidates',
            '🔴 These stocks are in distribution (Stage 3) or declining (Stage 4). Consider taking profits, tightening stop-losses, or exiting positions.',
            's4'
        )

        # Stage 1 Basing (watchlist)
        html += self._generate_stage_table(
            basing_df, 'Stage 1 — Basing (Watchlist)',
            '⚪ Consolidating stocks. Watch for breakout above SMA50 with increasing volume — could transition to Stage 2.',
            's1'
        )

        # Trend Template methodology
        html += """
    <h2 class="section-header">📋 Trend Template — 8-Point Checklist</h2>
    <div class="methodology">
        <p>Mark Minervini's Trend Template identifies stocks in a confirmed Stage 2 uptrend. All 8 criteria should ideally pass, but stocks with 6+/8 are considered strong setups.</p>
        <table>
            <thead>
                <tr>
                    <th onclick="sortTable(this)">#</th>
                    <th onclick="sortTable(this)">Criterion</th>
                    <th onclick="sortTable(this)">What It Checks</th>
                    <th onclick="sortTable(this)">Why It Matters</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>1</td><td>Price > SMA150 & SMA200</td><td>Stock above both long-term averages</td><td>Confirms long-term uptrend</td></tr>
                <tr><td>2</td><td>SMA150 > SMA200</td><td>Medium-term MA above long-term</td><td>Trend acceleration</td></tr>
                <tr><td>3</td><td>SMA200 trending up ≥1 month</td><td>SMA200 slope positive</td><td>Sustained institutional support</td></tr>
                <tr><td>4</td><td>SMA50 > SMA150 & SMA200</td><td>Short-term leading</td><td>Bullish MA stack confirmed</td></tr>
                <tr><td>5</td><td>Price > SMA50</td><td>Above short-term trend</td><td>Immediate momentum positive</td></tr>
                <tr><td>6</td><td>Price ≥25% above 52w Low</td><td>Distance from bottom</td><td>Not languishing near lows</td></tr>
                <tr><td>7</td><td>Price within 25% of 52w High</td><td>Near highs territory</td><td>Strength, not deep correction</td></tr>
                <tr><td>8</td><td>RS > 0</td><td>Outperforming NIFTY 50</td><td>Relative strength vs market</td></tr>
            </tbody>
        </table>
    </div>
"""

        # Plotly chart
        html += f"""
    <script>
{get_sortable_table_js()}

// Stage distribution pie chart
var stageData = [{{
    values: [{stage_counts[1]}, {stage_counts[2]}, {stage_counts[3]}, {stage_counts[4]}],
    labels: ['Stage 1 — Basing', 'Stage 2 — Advancing', 'Stage 3 — Topping', 'Stage 4 — Declining'],
    type: 'pie',
    marker: {{
        colors: ['#8b949e', '#3fb950', '#d29922', '#f85149']
    }},
    textinfo: 'label+value+percent',
    textfont: {{ color: '#e6edf3', size: 13 }},
    hole: 0.4
}}];

Plotly.newPlot('stageChart', stageData, {{
    title: {{ text: 'Portfolio Stage Distribution', font: {{ color: '#e6edf3', size: 16 }} }},
    paper_bgcolor: '#161b22',
    plot_bgcolor: '#0d1117',
    font: {{ color: '#c9d1d9' }},
    showlegend: true,
    legend: {{ font: {{ color: '#c9d1d9' }} }},
    margin: {{ t: 50, b: 30, l: 30, r: 30 }}
}}, {{responsive: true}});
    </script>

    <div style="text-align:center; padding:20px; color:#8b949e; font-size:0.85em;">
        Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Mark Minervini Stage Analysis
    </div>
</div>
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"   📊 Minervini Stage Analysis report: {output_path}")
        return output_path

    def _generate_stage_table(self, df: pd.DataFrame, title: str, description: str, style_class: str) -> str:
        """Generate an HTML table section for a subset of stocks."""
        html = f'\n    <h2 class="section-header">{title}</h2>\n'
        html += f'    <p>{description}</p>\n'

        if df.empty:
            html += '    <p style="color:#8b949e; font-style:italic;">No stocks in this category.</p>\n'
            return html

        # Select display columns
        cols = ['Symbol', 'CMP', 'Stage', 'TT_Score', 'SMA50', 'SMA150', 'SMA200',
                '52wHCh%', '52wLCh%', 'RS', '1W%', '1M%', 'Composite_Score', 'Signal', 'Swing_Trend', 'Stage_Action']
        available = [c for c in cols if c in df.columns]
        display = df[available].copy()

        html += '    <div class="table-wrapper">\n    <table>\n        <thead><tr>\n'
        for col in available:
            html += f'            <th onclick="sortTable(this)">{col}</th>\n'
        html += '        </tr></thead>\n        <tbody>\n'

        for _, row in display.iterrows():
            html += '        <tr>\n'
            for col in available:
                val = row[col]
                cell_style = ''
                cell_content = val

                if col == 'Stage':
                    badge_class = f's{int(val)}'
                    stage_labels = {1: 'S1-Base', 2: 'S2-Advance', 3: 'S3-Top', 4: 'S4-Decline'}
                    cell_content = f'<span class="stage-badge {badge_class}">{stage_labels.get(int(val), val)}</span>'
                elif col == 'TT_Score':
                    score = int(val) if not pd.isna(val) else 0
                    cls = 'high' if score >= 7 else 'mid' if score >= 5 else 'low'
                    cell_content = f'<span class="tt-score {cls}">{score}/8</span>'
                elif col in ('52wHCh%', 'RS', 'Composite_Score', '1W%', '1M%'):
                    try:
                        v = float(val)
                        cell_style = f' style="color: {"#3fb950" if v >= 0 else "#f85149"}"'
                        cell_content = f'{v:.2f}'
                    except (ValueError, TypeError):
                        cell_content = val
                elif col == '52wLCh%':
                    try:
                        v = float(val)
                        cell_style = f' style="color: {"#3fb950" if v >= 25 else "#d29922" if v >= 10 else "#f85149"}"'
                        cell_content = f'{v:.2f}'
                    except (ValueError, TypeError):
                        cell_content = val
                elif col in ('CMP', 'SMA50', 'SMA150', 'SMA200'):
                    try:
                        cell_content = f'{float(val):,.2f}'
                    except (ValueError, TypeError):
                        cell_content = val

                html += f'            <td{cell_style}>{cell_content}</td>\n'
            html += '        </tr>\n'

        html += '        </tbody>\n    </table>\n    </div>\n'
        return html


def _safe(row, col, default=0):
    """Safely get a numeric value from a row."""
    try:
        val = row.get(col, default)
        if pd.isna(val):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default
