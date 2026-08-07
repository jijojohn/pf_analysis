#!/usr/bin/env python3
"""
Momentum Rotation Analyzer (Relative Rotation Graph style)
=========================================================
Turns the existing RS (Relative Strength) and RS_Trend columns into a single,
actionable rotation map. Every holding falls into one of four quadrants based on
*where* its relative strength is (leading vs lagging the benchmark) and *which
way it is moving* (improving vs deteriorating):

    LEADING    (RS > 0, rising/flat)  → strongest names; hold / add on dips.
    WEAKENING  (RS > 0, falling)      → leaders losing steam; tighten stops / trim.
    IMPROVING  (RS < 0, rising)       → early turnarounds; build a watchlist.
    LAGGING    (RS < 0, falling)      → weakest names; avoid / exit.

The classic rotation flow is LEADING → WEAKENING → LAGGING → IMPROVING → LEADING,
so this view tells you which holdings are rotating *into* and *out of* leadership
before the change shows up in price alone.

Output: momentum_rotation_YYYYMMDD.html
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


# Display metadata per quadrant: (icon, color, headline action)
QUADRANTS = {
    'Leading':   ('🟢', '#3fb950', 'Leaders — hold winners, add on pullbacks.'),
    'Weakening': ('🟡', '#d29922', 'Leaders losing momentum — tighten stops / book partial profit.'),
    'Improving': ('🔵', '#58a6ff', 'Early turnarounds — watchlist for fresh entries.'),
    'Lagging':   ('🔴', '#f85149', 'Laggards — avoid fresh buys, exit broken trends.'),
}
QUADRANT_ORDER = ['Leading', 'Weakening', 'Improving', 'Lagging']


class MomentumRotationAnalyzer:
    """Classify holdings into RRG-style rotation quadrants from existing RS data."""

    def __init__(self, comprehensive_dataset: pd.DataFrame):
        self.dataset = comprehensive_dataset  # read-only reference
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def _quadrant_for(self, row) -> str:
        # Prefer the precomputed column; fall back to deriving it from RS/RS_Trend.
        q = str(row.get('RS_Quadrant', '') or '')
        if q in QUADRANTS:
            return q
        rs = safe_float(row.get('RS'))
        trend = str(row.get('RS_Trend', '') or '')
        if rs > 0:
            return 'Weakening' if trend == 'Falling' else 'Leading'
        return 'Improving' if trend == 'Rising' else 'Lagging'

    def classify(self) -> Dict[str, List[Dict]]:
        """Return {quadrant: [holding dicts]} preserving the canonical order."""
        buckets: Dict[str, List[Dict]] = {q: [] for q in QUADRANT_ORDER}
        if self.dataset.empty or 'Symbol' not in self.dataset.columns:
            return buckets
        for _, row in self.dataset.iterrows():
            quadrant = self._quadrant_for(row)
            rs = safe_float(row.get('RS'))
            rs_prev = safe_float(row.get('RS_Prev'), rs)
            buckets[quadrant].append({
                'symbol': str(row.get('Symbol', '?')),
                'rs': rs,
                'rs_change': round(rs - rs_prev, 2),
                'trend': str(row.get('RS_Trend', '') or '—'),
                'stage': row.get('Stage'),
                'signal': str(row.get('Signal', '') or '—'),
                'score': safe_float(row.get('Composite_Score'), 50.0),
                'alloc': safe_float(row.get('Percentage_Allocation')),
            })
        # Within a quadrant, rank by RS strength descending
        for q in buckets:
            buckets[q].sort(key=lambda h: h['rs'], reverse=True)
        return buckets

    def summary(self, buckets: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """Per-quadrant count + total allocation."""
        out = {}
        for q in QUADRANT_ORDER:
            holds = buckets.get(q, [])
            out[q] = {
                'count': len(holds),
                'alloc': round(sum(h['alloc'] for h in holds), 2),
            }
        return out

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def generate_report(self) -> str:
        buckets = self.classify()
        os.makedirs(self.reports_dir, exist_ok=True)
        ts = date.today().strftime('%Y%m%d')
        filepath = os.path.join(self.reports_dir, f"momentum_rotation_{ts}.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self._build_html(buckets))
        counts = {q: len(v) for q, v in buckets.items()}
        print(f"✅ Momentum rotation report saved: {filepath} "
              f"({counts['Leading']} leading, {counts['Weakening']} weakening, "
              f"{counts['Improving']} improving, {counts['Lagging']} lagging)")
        return filepath

    def _stage_label(self, stage) -> str:
        try:
            s = int(stage) if not pd.isna(stage) else 0
        except (TypeError, ValueError):
            s = 0
        return str(s) if s else '—'

    def _build_html(self, buckets: Dict[str, List[Dict]]) -> str:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        nav = get_nav_bar('Momentum Rotation')
        summ = self.summary(buckets)
        how = get_how_it_works('How This Rotation Map Works', [
            ('Quadrant', 'Combines relative strength (RS sign — leading vs lagging the benchmark) with its 1-month trend (improving vs deteriorating).'),
            ('Leading', 'RS > 0 and not falling — strongest names. Hold winners, add on pullbacks.'),
            ('Weakening', 'RS > 0 but falling — leaders losing momentum. Tighten stops, consider trimming.'),
            ('Improving', 'RS < 0 but rising — early turnarounds worth watching for entries.'),
            ('Lagging', 'RS < 0 and falling — weakest names. Avoid fresh buys, exit broken trends.'),
            ('Rotation flow', 'Money typically rotates Leading → Weakening → Lagging → Improving → Leading. Watch names drifting between quadrants.'),
        ])

        # Summary cards
        cards = []
        for q in QUADRANT_ORDER:
            icon, color, action = QUADRANTS[q]
            s = summ[q]
            cards.append(
                f"<div class='qcard' style='border-left:4px solid {color}'>"
                f"<div class='qtitle' style='color:{color}'>{icon} {q}</div>"
                f"<div class='qstat'>{s['count']} holdings &bull; {s['alloc']:.1f}% allocation</div>"
                f"<div class='qaction'>{action}</div></div>"
            )
        cards_html = f"<div class='qgrid'>{''.join(cards)}</div>"

        # One table per non-empty quadrant
        sections = []
        for q in QUADRANT_ORDER:
            holds = buckets.get(q, [])
            if not holds:
                continue
            icon, color, action = QUADRANTS[q]
            rows = []
            for h in holds:
                rs_class = 'positive' if h['rs'] > 0 else 'negative'
                chg_class = 'positive' if h['rs_change'] > 0 else 'negative' if h['rs_change'] < 0 else 'neutral'
                rows.append([
                    {'text': f"<b>{h['symbol']}</b>", 'html': True},
                    {'text': f"{h['rs']:+.2f}", 'class': rs_class},
                    {'text': f"{h['rs_change']:+.2f}", 'class': chg_class},
                    {'text': h['trend']},
                    {'text': self._stage_label(h['stage'])},
                    {'text': h['signal']},
                    {'text': f"{h['score']:.0f}"},
                    {'text': f"{h['alloc']:.1f}%"},
                ])
            table = render_table(
                ['Symbol', 'RS', 'RS Δ (1M)', 'Trend', 'Stage', 'Signal', 'Score', 'Allocation'],
                rows, sort_hint=(q == QUADRANT_ORDER[0]),
            )
            sections.append(
                f"<div class='section'><h2 style='color:{color}'>{icon} {q} "
                f"<span style='font-size:0.6em;color:#8b949e'>— {action}</span></h2>{table}</div>"
            )

        if not any(buckets.values()):
            sections.append("<div class='section'><p style='color:#8b949e'>No holdings to classify.</p></div>")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Momentum Rotation</title>
<style>{get_base_css()}
  .qgrid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; margin:18px 0; }}
  .qcard {{ background:#161b22; padding:14px 16px; border-radius:8px; }}
  .qtitle {{ font-weight:bold; font-size:1.1em; margin-bottom:4px; }}
  .qstat {{ color:#c9d1d9; font-size:0.9em; margin-bottom:6px; }}
  .qaction {{ color:#8b949e; font-size:0.85em; }}
</style>
<script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
<h1>🧭 Momentum Rotation Map</h1>
<p class="subtitle">Generated {ts} | Relative Rotation Graph (RRG) style</p>
{how}
{cards_html}
{''.join(sections)}
<div class="footer">Momentum Rotation &bull; Generated by Portfolio Analysis System</div>
</div>
</body></html>"""
