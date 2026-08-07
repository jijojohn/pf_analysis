#!/usr/bin/env python3
"""
Rebalance Advisor
=================
Turns the system's diagnostics into concrete, transparent rebalancing actions.
The drag analyzer identifies laggards; this module goes one step further and
proposes specific trim / add / exit deltas with a projected target allocation.

Rules (all thresholds configurable via config.json → rebalance_settings):
  • EXIT  — Stage 4, a Sell/Strong Sell signal, or composite score below exit_score.
  • TRIM  — Stage 3, or an overweight position whose score is below trim_score.
  • ADD   — Stage 1/2 with a Buy/Strong Buy signal, underweight, score >= add_score.
  • HOLD  — everything else.

Capital freed by exits/trims is redistributed to ADD candidates in proportion to
their composite score, capped at max_position_pct per name. Suggestions are
advisory only — they ignore taxes, lot sizes and liquidity.

Output: rebalance_suggestions_YYYYMMDD.html
"""

import os
from datetime import date, datetime
from typing import Dict, List

import pandas as pd

from config_manager import get_config
from data_utils import safe_float
from report_style import (
    get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works, render_table,
)


class RebalanceAdvisor:
    """Generate trim/add/exit suggestions from the comprehensive dataset."""

    SELL_SIGNALS = {"Sell", "Strong Sell"}
    BUY_SIGNALS = {"Buy", "Strong Buy"}

    def __init__(self, comprehensive_dataset: pd.DataFrame):
        self.dataset = comprehensive_dataset  # read-only reference
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")
        cfg = self.config.get_setting("rebalance_settings", {})
        self.exit_score = cfg.get("exit_score", 35)
        self.trim_score = cfg.get("trim_score", 50)
        self.add_score = cfg.get("add_score", 65)
        self.overweight_pct = cfg.get("overweight_pct", 10.0)
        self.underweight_pct = cfg.get("underweight_pct", 4.0)
        self.trim_fraction = cfg.get("trim_fraction", 0.30)
        self.max_position_pct = cfg.get("max_position_pct", 12.0)

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def _classify(self, row) -> Dict:
        sym = str(row.get('Symbol', '?'))
        alloc = safe_float(row.get('Percentage_Allocation'))
        score = safe_float(row.get('Composite_Score'), 50.0)
        signal = str(row.get('Signal', '') or '')
        try:
            stage = int(row.get('Stage')) if not pd.isna(row.get('Stage')) else 0
        except (TypeError, ValueError):
            stage = 0

        action, reason, target = 'HOLD', 'Within target — no action needed.', alloc

        if stage == 4 or signal in self.SELL_SIGNALS or score < self.exit_score:
            action = 'EXIT'
            target = 0.0
            if stage == 4:
                reason = f'Stage 4 (declining). Score {score:.0f}, signal "{signal or "n/a"}". Exit position.'
            elif signal in self.SELL_SIGNALS:
                reason = f'{signal} signal with score {score:.0f}. Close the position.'
            else:
                reason = f'Composite score {score:.0f} < {self.exit_score}. Weakest tier — exit.'
        elif stage == 3 or (alloc > self.overweight_pct and score < self.trim_score):
            action = 'TRIM'
            target = round(alloc * (1 - self.trim_fraction), 2)
            if stage == 3:
                reason = f'Stage 3 (topping). Book partial profit / reduce by {int(self.trim_fraction*100)}%.'
            else:
                reason = f'Overweight ({alloc:.1f}% > {self.overweight_pct:.0f}%) with mediocre score {score:.0f}. Trim.'
        elif (stage in (1, 2) and signal in self.BUY_SIGNALS
              and alloc < self.underweight_pct and score >= self.add_score):
            action = 'ADD'
            reason = f'Stage {stage} + {signal}, underweight ({alloc:.1f}%) with strong score {score:.0f}. Accumulate.'
            target = alloc  # filled in during redistribution
        else:
            reason = f'Stage {stage}, score {score:.0f}, signal "{signal or "n/a"}". Hold.'

        return {
            'symbol': sym, 'alloc': alloc, 'score': score, 'signal': signal,
            'stage': stage, 'action': action, 'reason': reason, 'target': target,
        }

    def build_suggestions(self) -> List[Dict]:
        if self.dataset.empty or 'Symbol' not in self.dataset.columns:
            return []
        items = [self._classify(row) for _, row in self.dataset.iterrows()]

        # Freed capital from exits and trims
        freed = 0.0
        for it in items:
            if it['action'] == 'EXIT':
                freed += it['alloc']
            elif it['action'] == 'TRIM':
                freed += it['alloc'] - it['target']

        # Redistribute to ADD candidates, weighted by score, capped per name
        adders = [it for it in items if it['action'] == 'ADD']
        if adders and freed > 0:
            total_score = sum(it['score'] for it in adders) or 1.0
            for it in adders:
                share = freed * (it['score'] / total_score)
                proposed = min(it['alloc'] + share, self.max_position_pct)
                it['target'] = round(proposed, 2)

        for it in items:
            it['delta'] = round(it['target'] - it['alloc'], 2)
        # Order: EXIT, TRIM, ADD, HOLD then by allocation desc
        order = {'EXIT': 0, 'TRIM': 1, 'ADD': 2, 'HOLD': 3}
        items.sort(key=lambda it: (order.get(it['action'], 4), -it['alloc']))
        return items

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def generate_report(self) -> str:
        items = self.build_suggestions()
        os.makedirs(self.reports_dir, exist_ok=True)
        ts = date.today().strftime('%Y%m%d')
        filepath = os.path.join(self.reports_dir, f"rebalance_suggestions_{ts}.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self._build_html(items))
        counts = {a: len([i for i in items if i['action'] == a]) for a in ('EXIT', 'TRIM', 'ADD', 'HOLD')}
        print(f"✅ Rebalance suggestions saved: {filepath} "
              f"({counts['EXIT']} exit, {counts['TRIM']} trim, {counts['ADD']} add, {counts['HOLD']} hold)")
        return filepath

    def _build_html(self, items: List[Dict]) -> str:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        nav = get_nav_bar('Rebalance Suggestions')
        how = get_how_it_works('How These Suggestions Are Built', [
            ('EXIT', f'Stage 4, a Sell/Strong Sell signal, or composite score < {self.exit_score}.'),
            ('TRIM', f'Stage 3, or overweight (> {self.overweight_pct:.0f}%) with score < {self.trim_score}. Reduces by {int(self.trim_fraction*100)}%.'),
            ('ADD', f'Stage 1/2 + Buy/Strong Buy, underweight (< {self.underweight_pct:.0f}%), score >= {self.add_score}.'),
            ('Redistribution', f'Capital freed by exits/trims flows to ADD names by score, capped at {self.max_position_pct:.0f}% per position.'),
            ('Advisory only', 'Ignores taxes, brokerage, lot sizes and liquidity — sanity-check before acting.'),
        ])

        action_color = {'EXIT': '#f85149', 'TRIM': '#d29922', 'ADD': '#3fb950', 'HOLD': '#8b949e'}
        counts = {a: len([i for i in items if i['action'] == a]) for a in ('EXIT', 'TRIM', 'ADD', 'HOLD')}
        freed = sum(i['alloc'] - i['target'] for i in items if i['action'] in ('EXIT', 'TRIM'))

        rows = []
        for it in items:
            ac = action_color[it['action']]
            delta_class = 'positive' if it['delta'] > 0 else 'negative' if it['delta'] < 0 else 'neutral'
            rows.append([
                {'text': f"<b>{it['symbol']}</b>", 'html': True},
                {'text': f"<span style='color:{ac};font-weight:bold'>{it['action']}</span>", 'html': True},
                {'text': f"{it['alloc']:.2f}%"},
                {'text': f"{it['target']:.2f}%"},
                {'text': f"{it['delta']:+.2f}%", 'class': delta_class},
                {'text': f"{it['score']:.0f}"},
                {'text': it['reason'], 'class': 'reason-cell'},
            ])
        table = render_table(
            ['Symbol', 'Action', 'Current %', 'Target %', 'Delta', 'Score', 'Rationale'],
            rows,
        ) if rows else "<p style='color:#8b949e'>No holdings to analyze.</p>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rebalance Suggestions</title>
<style>{get_base_css()}
  .reason-cell {{ color:#8b949e; font-size:0.85em; white-space:normal; }}
</style>
<script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
<h1>⚖️ Rebalance Suggestions</h1>
<p class="subtitle">Generated {ts} | {len(items)} holdings analyzed</p>
{how}
<div class="cards">
  <div class="card" style="border-color:#f85149"><div class="label">Exit</div><div class="value" style="color:#f85149">{counts['EXIT']}</div></div>
  <div class="card" style="border-color:#d29922"><div class="label">Trim</div><div class="value" style="color:#d29922">{counts['TRIM']}</div></div>
  <div class="card" style="border-color:#3fb950"><div class="label">Add</div><div class="value" style="color:#3fb950">{counts['ADD']}</div></div>
  <div class="card"><div class="label">Hold</div><div class="value">{counts['HOLD']}</div></div>
  <div class="card"><div class="label">Capital Freed</div><div class="value">{freed:.1f}%</div></div>
</div>
<div class="section">
<h2>📋 Suggested Actions</h2>
{table}
</div>
<div class="footer">Rebalance Suggestions &bull; Generated by Portfolio Analysis System</div>
</div>
</body></html>"""
