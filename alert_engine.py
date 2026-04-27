#!/usr/bin/env python3
"""
Alert Engine Module
Scans the comprehensive dataset for critical threshold breaches and generates
an HTML alert report organized by severity (Critical / Warning / Info).
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, date
from typing import Dict, List
from config_manager import get_config
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works


class AlertEngine:
    """Detect actionable alert conditions across the portfolio."""

    SEVERITY_CRITICAL = "Critical"
    SEVERITY_WARNING = "Warning"
    SEVERITY_INFO = "Info"

    def __init__(self, comprehensive_dataset: pd.DataFrame):
        self.dataset = comprehensive_dataset.copy()
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")
        alert_cfg = self.config.get_setting("alert_settings", {})
        # Configurable thresholds with sensible defaults
        self.rsi_severe_ob = alert_cfg.get("rsi_severe_overbought", 80)
        self.rsi_severe_os = alert_cfg.get("rsi_severe_oversold", 25)
        self.drawdown_threshold = alert_cfg.get("drawdown_threshold", -30)
        self.volume_spike = alert_cfg.get("volume_spike_threshold", 3.0)
        self.ma_proximity_pct = alert_cfg.get("ma_proximity_pct", 2.0)
        self.profit_protect_pct = alert_cfg.get("profit_protect_pct", 20)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def scan_alerts(self) -> List[Dict]:
        """Return a list of alert dicts sorted by severity."""
        alerts: List[Dict] = []
        if self.dataset.empty:
            return alerts

        for _, row in self.dataset.iterrows():
            alerts.extend(self._check_stock(row))

        # Sort: Critical first, then Warning, then Info
        severity_order = {self.SEVERITY_CRITICAL: 0, self.SEVERITY_WARNING: 1, self.SEVERITY_INFO: 2}
        alerts.sort(key=lambda a: (severity_order.get(a['severity'], 3), a['symbol']))
        return alerts

    def generate_report(self) -> str:
        """Generate alert_conditions_YYYYMMDD.html and return its path."""
        alerts = self.scan_alerts()
        html = self._build_html(alerts)

        os.makedirs(self.reports_dir, exist_ok=True)
        ts = date.today().strftime('%Y%m%d')
        filepath = os.path.join(self.reports_dir, f"alert_conditions_{ts}.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        c_count = len([a for a in alerts if a['severity'] == self.SEVERITY_CRITICAL])
        w_count = len([a for a in alerts if a['severity'] == self.SEVERITY_WARNING])
        i_count = len([a for a in alerts if a['severity'] == self.SEVERITY_INFO])
        print(f"✅ Alert report saved: {filepath} ({c_count} critical, {w_count} warnings, {i_count} info)")
        return filepath

    def get_summary(self) -> Dict:
        """Return a brief summary for embedding in master report."""
        alerts = self.scan_alerts()
        return {
            'total': len(alerts),
            'critical': len([a for a in alerts if a['severity'] == self.SEVERITY_CRITICAL]),
            'warning': len([a for a in alerts if a['severity'] == self.SEVERITY_WARNING]),
            'info': len([a for a in alerts if a['severity'] == self.SEVERITY_INFO]),
            'top_alerts': alerts[:5],  # first 5 for quick display
        }

    # ------------------------------------------------------------------
    # Alert detection per stock
    # ------------------------------------------------------------------
    def _check_stock(self, row) -> List[Dict]:
        alerts = []
        sym = row.get('Symbol', '?')
        rsi = row.get('RSI', 50)
        rs = row.get('RS', 0)
        cmp = row.get('CMP', 0)
        wema21 = row.get('WEMA21', cmp)
        dsma200 = row.get('SMA200', cmp)  # Use current SMA200, not displaced
        h52_chg = row.get('52wHCh%', 0)
        l52_chg = row.get('52wLCh%', 0)
        rel_vol = row.get('Relative_Volume', 0)
        sharpe = row.get('Sharpe_Ratio', 0)
        sortino = row.get('Sortino_Ratio', 0)
        pl_pct = row.get('Profit_Loss_Pct', 0)
        score = row.get('Composite_Score', 50)
        stage = int(row.get('Stage', 1)) if not pd.isna(row.get('Stage', 1)) else 1
        tt_score = int(row.get('TT_Score', 0)) if not pd.isna(row.get('TT_Score', 0)) else 0

        # Stage-based alerts (Minervini)
        if stage == 4:
            alerts.append(self._alert(sym, self.SEVERITY_CRITICAL, "Stage 4 — Declining",
                f"Stock in Stage 4 (bearish MA stack, TT {tt_score}/8). Exit or avoid new positions.",
                f"Minervini Stage 4 detected — price below all key SMAs, downtrend confirmed."))
        elif stage == 3:
            alerts.append(self._alert(sym, self.SEVERITY_WARNING, "Stage 3 — Topping",
                f"Stock in Stage 3 (distribution, TT {tt_score}/8). Take profits or tighten stop-loss.",
                f"MAs converging, momentum fading — potential transition to Stage 4."))
        elif stage == 2 and tt_score >= 7:
            alerts.append(self._alert(sym, self.SEVERITY_INFO, "Stage 2 — Prime Uptrend",
                f"Full Trend Template ({tt_score}/8). Strong bullish setup for adding.",
                f"Minervini Trend Template nearly perfect — ideal for swing entries."))

        # MA crossover proximity
        if cmp > 0 and wema21 > 0:
            gap_pct = abs(cmp - wema21) / wema21 * 100
            if gap_pct <= self.ma_proximity_pct:
                direction = "crossing above" if cmp > wema21 else "crossing below"
                alerts.append(self._alert(sym, self.SEVERITY_INFO, "Weekly EMA 21 Crossover",
                    f"CMP ₹{cmp:.0f} is {direction} Weekly EMA 21 (₹{wema21:.0f}), gap {gap_pct:.1f}%.",
                    f"Price within {self.ma_proximity_pct}% of Weekly EMA 21, potential trend change."))

        if cmp > 0 and dsma200 > 0:
            gap_pct = abs(cmp - dsma200) / dsma200 * 100
            if gap_pct <= self.ma_proximity_pct:
                direction = "crossing above" if cmp > dsma200 else "crossing below"
                alerts.append(self._alert(sym, self.SEVERITY_WARNING, "SMA 200 Crossover",
                    f"CMP ₹{cmp:.0f} is {direction} SMA 200 (₹{dsma200:.0f}), gap {gap_pct:.1f}%.",
                    f"Price within {self.ma_proximity_pct}% of 200-day MA, significant trend signal."))

        # High drawdown
        if h52_chg < self.drawdown_threshold:
            alerts.append(self._alert(sym, self.SEVERITY_CRITICAL, "High Drawdown",
                f"Down {h52_chg:.0f}% from 52-week high. Review position for potential exit.",
                f"52wHCh% is {h52_chg:.0f}%, exceeding the {self.drawdown_threshold}% threshold."))

        # Volume spike
        if rel_vol >= self.volume_spike:
            alerts.append(self._alert(sym, self.SEVERITY_INFO, "Volume Spike",
                f"Relative volume {rel_vol:.1f}x — unusual activity detected.",
                f"Volume is {rel_vol:.1f}x the 20-day average, threshold is {self.volume_spike}x."))

        # Risk deterioration
        if sharpe < 0 and sortino < 0:
            alerts.append(self._alert(sym, self.SEVERITY_CRITICAL, "Risk Deterioration",
                f"Both Sharpe ({sharpe:.2f}) and Sortino ({sortino:.2f}) are negative. Poor risk-return.",
                "Negative risk-adjusted returns on both measures — review position urgency."))

        # Contrarian opportunity (near 52w low with positive RS)
        if l52_chg <= 5 and rs > 0:
            alerts.append(self._alert(sym, self.SEVERITY_INFO, "Contrarian Opportunity",
                f"Within {l52_chg:.0f}% of 52-week low but RS is positive ({rs:.2f}).",
                "Stock near 52-week low but outperforming benchmark — potential reversal."))

        # Profit protection
        if pl_pct > self.profit_protect_pct and rsi > 65 and cmp < wema21:
            alerts.append(self._alert(sym, self.SEVERITY_WARNING, "Profit Protection",
                f"Profit {pl_pct:.0f}% at risk — RSI {rsi:.0f} declining, below Weekly EMA 21.",
                f"Stock has >{self.profit_protect_pct}% profit but momentum is fading."))

        return alerts

    def _alert(self, symbol, severity, alert_type, description, methodology) -> Dict:
        return {
            'symbol': symbol,
            'severity': severity,
            'type': alert_type,
            'description': description,
            'methodology': methodology,
        }

    # ------------------------------------------------------------------
    # HTML builder
    # ------------------------------------------------------------------
    def _build_html(self, alerts: List[Dict]) -> str:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        c_count = len([a for a in alerts if a['severity'] == self.SEVERITY_CRITICAL])
        w_count = len([a for a in alerts if a['severity'] == self.SEVERITY_WARNING])
        i_count = len([a for a in alerts if a['severity'] == self.SEVERITY_INFO])

        rows_html = ""
        for a in alerts:
            sc = {'Critical': '#f44336', 'Warning': '#FF9800', 'Info': '#2196F3'}[a['severity']]
            icon = {'Critical': '🔴', 'Warning': '🟡', 'Info': '🔵'}[a['severity']]
            rows_html += f"""
            <tr>
                <td style="text-align:center">{icon}</td>
                <td><span style="color:{sc};font-weight:bold">{a['severity']}</span></td>
                <td><b>{a['symbol']}</b></td>
                <td>{a['type']}</td>
                <td>{a['description']}</td>
                <td style="color:#8b949e;font-size:0.85em">{a['methodology']}</td>
            </tr>"""

        nav = get_nav_bar('Alert Conditions')
        how_it_works = get_how_it_works('How Alerts Are Generated', [
            ('RSI Extremes', f'Overbought > {self.rsi_severe_ob}, Oversold < {self.rsi_severe_os} — momentum warning signals'),
            ('MA Crossovers', f'Price within {self.ma_proximity_pct}% of Weekly EMA 21 or SMA 200 — potential trend change'),
            ('High Drawdown', f'52wHCh% < {self.drawdown_threshold}% — severe decline from 52-week high'),
            ('Volume Spikes', f'Relative volume >= {self.volume_spike}x average — unusual activity detected'),
            ('Risk Deterioration', 'Both Sharpe & Sortino negative — poor risk-adjusted returns'),
            ('Contrarian Opportunity', 'Near 52-week low with positive RS — potential reversal candidate'),
            ('Profit Protection', f'>{self.profit_protect_pct}% profit with fading momentum — consider booking'),
        ])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Alert Conditions Summary</title>
<style>{get_base_css()}
  .no-alerts {{ text-align:center; padding:40px; color:#3fb950; font-size:1.3em; }}
</style>
<script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
<h1>🚨 Alert Conditions Summary</h1>
<p class="subtitle">Generated {ts} | {len(alerts)} alerts across {self.dataset.shape[0]} stocks</p>

<div class="cards">
  <div class="card" style="border-color:#f44336"><div class="label">Critical</div><div class="value" style="color:#f44336">{c_count}</div></div>
  <div class="card" style="border-color:#FF9800"><div class="label">Warning</div><div class="value" style="color:#FF9800">{w_count}</div></div>
  <div class="card" style="border-color:#2196F3"><div class="label">Info</div><div class="value" style="color:#2196F3">{i_count}</div></div>
  <div class="card"><div class="label">Total Alerts</div><div class="value">{len(alerts)}</div></div>
</div>

{how_it_works}

<div class="section">
<h2>📋 All Alerts</h2>
{"<div class='no-alerts'>✅ No alerts detected — portfolio looks healthy!</div>" if not alerts else f'''
<p class="sort-hint">Click any column header to sort</p>
<div class="table-wrapper">
<table>
<thead><tr><th></th><th onclick="sortTable(this)">Severity</th><th onclick="sortTable(this)">Symbol</th><th onclick="sortTable(this)">Type</th><th>Description</th><th>How Detected</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
</div>'''}
</div>

<div class="footer">
Alert Conditions Summary &bull; Generated by Portfolio Analysis System
</div>
</div>
</body></html>"""
        return html
