#!/usr/bin/env python3
"""
Signal Backtest Engine
======================
Validates the *approach* behind the system's signals by replaying transparent,
reconstructable entry setups across each stock's price history and measuring
forward returns. Instead of asking "is this stock a Buy today?", it answers
"historically, when this setup fired, how often did it work and by how much?".

Setups are event-based (they fire on a transition, e.g. price reclaiming the
200-day MA), so they map directly to the crossover alerts in alert_engine.py.

Output: signal_backtest_YYYYMMDD.html — win rate, average/median forward return
and expectancy per setup and per holding horizon.
"""

import os
from datetime import date, datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config_manager import get_config
from data_utils import clean_close_nan
from report_style import (
    get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works, render_table,
)


class SignalBacktester:
    """Replay entry setups historically and measure forward returns."""

    def __init__(self, historical_data: pd.DataFrame):
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")
        bt_cfg = self.config.get_setting("backtest_settings", {})
        self.horizons: List[int] = bt_cfg.get("horizons", [5, 21, 63])
        self.rsi_period: int = bt_cfg.get("rsi_period", 14)
        self.rsi_oversold: int = bt_cfg.get("rsi_oversold", 30)
        self.history = self._index_history(historical_data)

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------
    def _index_history(self, historical_data: Optional[pd.DataFrame]) -> Dict[str, pd.Series]:
        """Return {symbol: close-series} indexed by date, cleaned & sorted."""
        result: Dict[str, pd.Series] = {}
        if historical_data is None or historical_data.empty or 'Symbol' not in historical_data.columns:
            return result
        for sym, grp in historical_data.groupby('Symbol'):
            df = grp.copy()
            if 'Date' in df.columns and 'date' not in df.columns:
                df = df.rename(columns={'Date': 'date'})
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception:
                    continue
            df = clean_close_nan(df).sort_index()
            if 'close' in df.columns and len(df) >= 60:
                result[sym] = df['close']
        return result

    @staticmethod
    def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # ------------------------------------------------------------------
    # Event detection
    # ------------------------------------------------------------------
    def _detect_events(self, close: pd.Series) -> Dict[str, List[int]]:
        """Return {setup_name: [positional indices where setup fired]}."""
        events: Dict[str, List[int]] = {
            "SMA50 Reclaim": [],
            "SMA200 Reclaim": [],
            "Golden Cross": [],
            "RSI Oversold Bounce": [],
        }
        n = len(close)
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        rsi = self._wilder_rsi(close, self.rsi_period)
        c = close.values
        s50 = sma50.values
        s200 = sma200.values
        r = rsi.values

        for i in range(1, n):
            # SMA50 reclaim
            if not np.isnan(s50[i - 1]) and c[i - 1] < s50[i - 1] and c[i] >= s50[i]:
                events["SMA50 Reclaim"].append(i)
            # SMA200 reclaim
            if not np.isnan(s200[i - 1]) and c[i - 1] < s200[i - 1] and c[i] >= s200[i]:
                events["SMA200 Reclaim"].append(i)
            # Golden cross
            if (not np.isnan(s50[i - 1]) and not np.isnan(s200[i - 1])
                    and s50[i - 1] <= s200[i - 1] and s50[i] > s200[i]):
                events["Golden Cross"].append(i)
            # RSI oversold bounce
            if not np.isnan(r[i - 1]) and r[i - 1] <= self.rsi_oversold and r[i] > self.rsi_oversold:
                events["RSI Oversold Bounce"].append(i)
        return events

    # ------------------------------------------------------------------
    # Backtest
    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Dict[int, Dict]]:
        """Return {setup: {horizon: {count, win_rate, avg, median, expectancy}}}."""
        # Collect forward returns: fwd[setup][horizon] = list of pct returns
        fwd: Dict[str, Dict[int, List[float]]] = {}
        for close in self.history.values():
            c = close.values
            n = len(c)
            events = self._detect_events(close)
            for setup, idxs in events.items():
                fwd.setdefault(setup, {h: [] for h in self.horizons})
                for i in idxs:
                    for h in self.horizons:
                        j = i + h
                        if j < n and c[i] > 0:
                            fwd[setup][h].append((c[j] / c[i] - 1) * 100)

        # Aggregate
        results: Dict[str, Dict[int, Dict]] = {}
        for setup, by_h in fwd.items():
            results[setup] = {}
            for h, rets in by_h.items():
                results[setup][h] = self._summarize(rets)
        return results

    @staticmethod
    def _summarize(rets: List[float]) -> Dict:
        if not rets:
            return {"count": 0, "win_rate": 0.0, "avg": 0.0, "median": 0.0, "expectancy": 0.0}
        arr = np.array(rets, dtype=float)
        wins = arr[arr > 0]
        losses = arr[arr <= 0]
        win_rate = len(wins) / len(arr) * 100
        avg_win = wins.mean() if len(wins) else 0.0
        avg_loss = losses.mean() if len(losses) else 0.0
        # Expectancy per trade = P(win)*avgWin + P(loss)*avgLoss
        p_win = len(wins) / len(arr)
        expectancy = p_win * avg_win + (1 - p_win) * avg_loss
        return {
            "count": int(len(arr)),
            "win_rate": round(win_rate, 1),
            "avg": round(float(arr.mean()), 2),
            "median": round(float(np.median(arr)), 2),
            "expectancy": round(float(expectancy), 2),
        }

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def generate_report(self) -> str:
        results = self.run()
        os.makedirs(self.reports_dir, exist_ok=True)
        ts = date.today().strftime('%Y%m%d')
        filepath = os.path.join(self.reports_dir, f"signal_backtest_{ts}.html")
        html = self._build_html(results)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        total_events = sum(r[self.horizons[0]]["count"] for r in results.values()) if results else 0
        print(f"✅ Signal backtest report saved: {filepath} ({total_events} events across {len(self.history)} stocks)")
        return filepath

    def _build_html(self, results: Dict[str, Dict[int, Dict]]) -> str:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        nav = get_nav_bar('Signal Backtest')
        how = get_how_it_works('How This Backtest Works', [
            ('Purpose', 'Measures how the system\'s entry setups performed historically — validating the approach, not predicting the future.'),
            ('Setups', 'Event-based triggers: SMA50/SMA200 reclaim, Golden Cross, RSI oversold bounce (same logic as crossover alerts).'),
            ('Forward Return', f'For each trigger we measure the % price change after {", ".join(str(h) for h in self.horizons)} trading days.'),
            ('Win Rate', 'Percentage of triggers that produced a positive forward return at that horizon.'),
            ('Expectancy', 'Average return per trade = P(win)×avgWin + P(loss)×avgLoss. Positive = edge.'),
            ('Caveat', 'Backtests ignore slippage, costs and survivorship; treat as directional evidence, not a guarantee.'),
        ])

        # Build one table per setup (horizons as rows)
        sections = []
        if not results or all(
            all(results[s][h]["count"] == 0 for h in self.horizons) for s in results
        ):
            sections.append("<div class='section'><p style='color:#8b949e'>Not enough historical data to backtest setups.</p></div>")
        else:
            for setup, by_h in results.items():
                rows = []
                for h in self.horizons:
                    m = by_h[h]
                    if m["count"] == 0:
                        continue
                    wr_class = 'positive' if m["win_rate"] >= 55 else 'negative' if m["win_rate"] < 45 else 'neutral'
                    exp_class = 'positive' if m["expectancy"] > 0 else 'negative'
                    avg_class = 'positive' if m["avg"] > 0 else 'negative'
                    rows.append([
                        {'text': f'{h} days', 'html': False},
                        {'text': m["count"], 'html': False},
                        {'text': f'{m["win_rate"]:.1f}%', 'class': wr_class},
                        {'text': f'{m["avg"]:+.2f}%', 'class': avg_class},
                        {'text': f'{m["median"]:+.2f}%'},
                        {'text': f'{m["expectancy"]:+.2f}%', 'class': exp_class},
                    ])
                if not rows:
                    continue
                table = render_table(
                    ['Horizon', 'Triggers', 'Win Rate', 'Avg Return', 'Median', 'Expectancy'],
                    rows, sort_hint=False,
                )
                sections.append(f"<div class='section'><h2>📐 {setup}</h2>{table}</div>")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Signal Backtest</title>
<style>{get_base_css()}</style>
<script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
<h1>🧪 Signal Backtest &amp; Hit-Rate</h1>
<p class="subtitle">Generated {ts} | {len(self.history)} stocks | horizons {", ".join(str(h) for h in self.horizons)} days</p>
{how}
{''.join(sections)}
<div class="footer">Signal Backtest &bull; Generated by Portfolio Analysis System</div>
</div>
</body></html>"""
