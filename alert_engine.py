#!/usr/bin/env python3
"""
Alert Engine Module
Scans the comprehensive dataset for critical threshold breaches and generates
an HTML alert report organized by severity (Critical / Warning / Info).

In addition to snapshot (single-day) threshold alerts, the engine can detect
*crossover* events (price reclaiming the 200-day MA, RSI rolling over from
overbought, Golden/Death cross) and *benchmark-relative* underperformance when
historical price series and benchmark data are supplied. These event-based
alerts are far less noisy than static thresholds because they fire on the
transition, not the state.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, date
from typing import Dict, List, Optional
from config_manager import get_config
from data_utils import clean_close_nan
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works, render_table


class AlertEngine:
    """Detect actionable alert conditions across the portfolio."""

    SEVERITY_CRITICAL = "Critical"
    SEVERITY_WARNING = "Warning"
    SEVERITY_INFO = "Info"

    def __init__(self, comprehensive_dataset: pd.DataFrame,
                 historical_data: Optional[pd.DataFrame] = None,
                 benchmark_data: Optional[pd.DataFrame] = None):
        self.dataset = comprehensive_dataset.copy()
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")
        alert_cfg = self.config.get_setting("alert_settings", {})
        # Configurable thresholds with sensible defaults
        self.rsi_severe_ob = alert_cfg.get("rsi_severe_overbought", 80)
        self.rsi_severe_os = alert_cfg.get("rsi_severe_oversold", 25)
        self.rsi_overbought = alert_cfg.get("rsi_overbought", 70)
        self.rsi_oversold = alert_cfg.get("rsi_oversold", 30)
        self.drawdown_threshold = alert_cfg.get("drawdown_threshold", -30)
        self.volume_spike = alert_cfg.get("volume_spike_threshold", 3.0)
        self.ma_proximity_pct = alert_cfg.get("ma_proximity_pct", 2.0)
        self.profit_protect_pct = alert_cfg.get("profit_protect_pct", 20)
        # Stock must underperform the benchmark drawdown by at least this many
        # percentage points (over the trailing window) to flag underperformance.
        self.rel_underperf_pct = alert_cfg.get("relative_underperformance_pct", 10)

        # Optional time-series inputs for event-based (crossover) alerts
        self.history = self._index_history(historical_data)
        self.benchmark = self._prepare_series(benchmark_data)

    # ------------------------------------------------------------------
    # Time-series preparation
    # ------------------------------------------------------------------
    def _prepare_series(self, df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
        """Return a cleaned, date-sorted copy of a single price series."""
        if df is None or df.empty or 'close' not in df.columns:
            return None
        out = df.copy()
        if 'Date' in out.columns and 'date' not in out.columns:
            out = out.rename(columns={'Date': 'date'})
        if 'date' in out.columns:
            out['date'] = pd.to_datetime(out['date'])
            out = out.set_index('date')
        if not isinstance(out.index, pd.DatetimeIndex):
            try:
                out.index = pd.to_datetime(out.index)
            except Exception:
                return None
        out = clean_close_nan(out).sort_index()
        return out if not out.empty else None

    def _index_history(self, historical_data: Optional[pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Split combined historical data into per-symbol cleaned series."""
        if historical_data is None or historical_data.empty or 'Symbol' not in historical_data.columns:
            return {}
        result: Dict[str, pd.DataFrame] = {}
        for sym, grp in historical_data.groupby('Symbol'):
            series = self._prepare_series(grp)
            if series is not None and len(series) >= 2:
                result[sym] = series
        return result

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
            sym = row.get('Symbol', '?')
            if sym in self.history:
                alerts.extend(self._check_crossovers(sym, self.history[sym]))
                alerts.extend(self._check_relative_drawdown(sym, self.history[sym]))

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
        rs_trend = row.get('RS_Trend', '')
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

        # RS deterioration (momentum leadership fading even while in uptrend)
        if rs_trend == 'Falling' and rs > 0 and stage in (2, 3):
            alerts.append(self._alert(sym, self.SEVERITY_INFO, "RS Momentum Fading",
                f"Relative strength is declining ({rs:.1f} now vs higher a month ago).",
                "RS_Trend = Falling while still outperforming — early leadership-rotation warning."))

        return alerts

    # ------------------------------------------------------------------
    # Event-based (crossover) detection using historical series
    # ------------------------------------------------------------------
    @staticmethod
    def _wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _check_crossovers(self, sym: str, series: pd.DataFrame) -> List[Dict]:
        """Detect transition events between yesterday and today."""
        alerts: List[Dict] = []
        close = series['close']
        if len(close) < 51:
            return alerts

        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        c_now, c_prev = close.iloc[-1], close.iloc[-2]

        # Price vs SMA200 reclaim / loss
        if len(close) >= 201 and not pd.isna(sma200.iloc[-2]):
            s_now, s_prev = sma200.iloc[-1], sma200.iloc[-2]
            if c_prev < s_prev and c_now >= s_now:
                alerts.append(self._alert(sym, self.SEVERITY_INFO, "Reclaimed SMA 200",
                    f"Price crossed back ABOVE the 200-day MA (₹{c_now:.0f} vs ₹{s_now:.0f}).",
                    "Yesterday's close was below SMA200, today's is above — bullish trend reclaim."))
            elif c_prev > s_prev and c_now <= s_now:
                alerts.append(self._alert(sym, self.SEVERITY_WARNING, "Lost SMA 200",
                    f"Price broke BELOW the 200-day MA (₹{c_now:.0f} vs ₹{s_now:.0f}).",
                    "Yesterday's close was above SMA200, today's is below — major trend breakdown."))

        # Price vs SMA50 crossover
        if not pd.isna(sma50.iloc[-2]):
            s_now, s_prev = sma50.iloc[-1], sma50.iloc[-2]
            if c_prev < s_prev and c_now >= s_now:
                alerts.append(self._alert(sym, self.SEVERITY_INFO, "Crossed Above SMA 50",
                    f"Price crossed ABOVE the 50-day MA (₹{c_now:.0f} vs ₹{s_now:.0f}).",
                    "Short-term momentum turned positive — price reclaimed SMA50."))
            elif c_prev > s_prev and c_now <= s_now:
                alerts.append(self._alert(sym, self.SEVERITY_INFO, "Crossed Below SMA 50",
                    f"Price crossed BELOW the 50-day MA (₹{c_now:.0f} vs ₹{s_now:.0f}).",
                    "Short-term momentum turned negative — price lost SMA50."))

        # Golden / Death cross (SMA50 vs SMA200)
        if len(close) >= 201 and not pd.isna(sma50.iloc[-2]) and not pd.isna(sma200.iloc[-2]):
            f_now, f_prev = sma50.iloc[-1], sma50.iloc[-2]
            sl_now, sl_prev = sma200.iloc[-1], sma200.iloc[-2]
            if f_prev <= sl_prev and f_now > sl_now:
                alerts.append(self._alert(sym, self.SEVERITY_INFO, "Golden Cross",
                    "SMA 50 crossed ABOVE SMA 200 — classic long-term bullish signal.",
                    "50-day MA rose above 200-day MA between the last two sessions."))
            elif f_prev >= sl_prev and f_now < sl_now:
                alerts.append(self._alert(sym, self.SEVERITY_WARNING, "Death Cross",
                    "SMA 50 crossed BELOW SMA 200 — classic long-term bearish signal.",
                    "50-day MA fell below 200-day MA between the last two sessions."))

        # RSI threshold crossings
        rsi = self._wilder_rsi(close)
        if len(rsi) >= 2 and not pd.isna(rsi.iloc[-2]):
            r_now, r_prev = rsi.iloc[-1], rsi.iloc[-2]
            if r_prev >= self.rsi_overbought and r_now < self.rsi_overbought:
                alerts.append(self._alert(sym, self.SEVERITY_WARNING, "RSI Rolled Over",
                    f"RSI dropped back below {self.rsi_overbought} (now {r_now:.0f}) — overbought unwinding.",
                    f"RSI crossed down through {self.rsi_overbought}, a momentum-exhaustion trigger."))
            elif r_prev <= self.rsi_oversold and r_now > self.rsi_oversold:
                alerts.append(self._alert(sym, self.SEVERITY_INFO, "RSI Bounce",
                    f"RSI rose back above {self.rsi_oversold} (now {r_now:.0f}) — oversold bounce.",
                    f"RSI crossed up through {self.rsi_oversold}, a potential reversal trigger."))

        return alerts

    def _check_relative_drawdown(self, sym: str, series: pd.DataFrame) -> List[Dict]:
        """Compare the stock's trailing drawdown to the benchmark's."""
        if self.benchmark is None:
            return []
        close = series['close']
        bench = self.benchmark['close']
        if len(close) < 30 or len(bench) < 30:
            return []

        window = 252
        stock_dd = (close.iloc[-1] / close.tail(window).max() - 1) * 100
        bench_dd = (bench.iloc[-1] / bench.tail(window).max() - 1) * 100
        gap = stock_dd - bench_dd  # negative means stock is deeper in drawdown
        if gap <= -self.rel_underperf_pct:
            return [self._alert(sym, self.SEVERITY_WARNING, "Relative Underperformance",
                f"Down {stock_dd:.0f}% from its high while benchmark is only {bench_dd:.0f}% — lagging by {abs(gap):.0f}pp.",
                f"Stock drawdown exceeds benchmark drawdown by more than {self.rel_underperf_pct} percentage points.")]
        return []

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

        sev_color = {'Critical': '#f44336', 'Warning': '#FF9800', 'Info': '#2196F3'}
        sev_icon = {'Critical': '🔴', 'Warning': '🟡', 'Info': '🔵'}

        table_rows = []
        for a in alerts:
            sc = sev_color[a['severity']]
            icon = sev_icon[a['severity']]
            table_rows.append([
                {'text': icon, 'align': 'center', 'html': True},
                {'text': f'<span style="color:{sc};font-weight:bold">{a["severity"]}</span>', 'html': True},
                {'text': f'<b>{a["symbol"]}</b>', 'html': True},
                a['type'],
                a['description'],
                {'text': a['methodology'], 'class': 'methodology-cell'},
            ])

        table_html = render_table(
            ['', 'Severity', 'Symbol', 'Type', 'Description', 'How Detected'],
            table_rows,
        )

        nav = get_nav_bar('Alert Conditions')
        how_it_works = get_how_it_works('How Alerts Are Generated', [
            ('Stage Alerts', 'Minervini Stage 4 = Critical, Stage 3 = Warning, Stage 2 (TT 7+) = Info'),
            ('MA Crossovers', f'Price within {self.ma_proximity_pct}% of Weekly EMA 21 or SMA 200 — potential trend change'),
            ('Crossover Events', 'Actual transitions between sessions: SMA50/200 reclaim or loss, Golden/Death cross, RSI through 70/30'),
            ('High Drawdown', f'52wHCh% < {self.drawdown_threshold}% — severe decline from 52-week high'),
            ('Relative Underperformance', f'Stock drawdown exceeds benchmark drawdown by > {self.rel_underperf_pct}pp'),
            ('Volume Spikes', f'Relative volume >= {self.volume_spike}x average — unusual activity detected'),
            ('RS Momentum Fading', 'RS_Trend = Falling while still outperforming — leadership rotation warning'),
            ('Profit Protection', f'>{self.profit_protect_pct}% profit with fading momentum — consider booking'),
        ])

        body_table = (
            "<div class='no-alerts'>✅ No alerts detected — portfolio looks healthy!</div>"
            if not alerts else table_html
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Alert Conditions Summary</title>
<style>{get_base_css()}
  .no-alerts {{ text-align:center; padding:40px; color:#3fb950; font-size:1.3em; }}
  .methodology-cell {{ color:#8b949e; font-size:0.85em; white-space:normal; }}
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
{body_table}
</div>

<div class="footer">
Alert Conditions Summary &bull; Generated by Portfolio Analysis System
</div>
</div>
</body></html>"""
        return html
