#!/usr/bin/env python3
"""
Signal Engine Module
Generates Buy/Sell/Hold signals with confidence levels and concise per-stock verdicts.
Uses a deterministic rule-based approach combining Composite Score, RS, trend, momentum, and risk.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from config_manager import get_config


def _safe(row, col, default=0.0):
    """Get a value from a row, returning default if missing or NaN."""
    val = row.get(col, default)
    if pd.isna(val):
        return default
    return float(val) if not isinstance(val, str) else val


class SignalEngine:
    """Generate actionable trading signals for every stock in the scored dataset."""

    SIGNAL_STRONG_BUY = "Strong Buy"
    SIGNAL_BUY = "Buy"
    SIGNAL_HOLD = "Hold"
    SIGNAL_SELL = "Sell"
    SIGNAL_STRONG_SELL = "Strong Sell"

    def __init__(self):
        self.config = get_config()
        sig_cfg = self.config.get_setting("signal_settings", {})
        # Thresholds (configurable)
        self.strong_buy_score = sig_cfg.get("strong_buy_score", 75)
        self.buy_score = sig_cfg.get("buy_score", 60)
        self.sell_score = sig_cfg.get("sell_score", 40)
        self.strong_sell_score = sig_cfg.get("strong_sell_score", 25)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Signal, Signal_Confidence, Signal_Reason, and Signal_Verdict columns."""
        if df.empty:
            return df

        result = df.copy()
        signals = result.apply(self._evaluate_stock, axis=1, result_type='expand')
        result['Signal'] = signals['signal']
        result['Signal_Confidence'] = signals['confidence']
        result['Signal_Reason'] = signals['reason']
        result['Signal_Verdict'] = signals['verdict']
        return result

    # ------------------------------------------------------------------
    # Per-stock evaluation
    # ------------------------------------------------------------------
    def _evaluate_stock(self, row) -> Dict:
        score = _safe(row, 'Composite_Score', 50)
        rs = _safe(row, 'RS', 0)
        rsi = _safe(row, 'RSI', 50)
        sharpe = _safe(row, 'Sharpe_Ratio', 0)
        sortino = _safe(row, 'Sortino_Ratio', 0)
        cmp = _safe(row, 'CMP', 0)
        wema21 = _safe(row, 'WEMA21', cmp)
        wema30 = _safe(row, 'WEMA30', cmp)
        dsma200 = _safe(row, 'DSMA200', cmp)
        h52_chg = _safe(row, '52wHCh%', 0)
        rel_vol = _safe(row, 'Relative_Volume', 0)
        symbol = row.get('Symbol', '?')
        vol = _safe(row, 'Standard_Deviation', 0)
        pl_pct = _safe(row, 'Profit_Loss_Pct', 0)
        stage = int(_safe(row, 'Stage', 1))
        tt_score = int(_safe(row, 'TT_Score', 0))

        above_wema21 = cmp > wema21 if wema21 > 0 else False
        above_wema30 = cmp > wema30 if wema30 > 0 else False
        above_dsma200 = cmp > dsma200 if dsma200 > 0 else False

        # ---- Determine signal ----
        bullish_factors = []
        bearish_factors = []

        if rs > 3.0:
            bullish_factors.append(f"RS {rs:.2f} (outperforming)")
        elif rs < -3.0:
            bearish_factors.append(f"RS {rs:.2f} (underperforming)")

        if above_wema21 and above_wema30:
            bullish_factors.append("Above WEMA21 & WEMA30")
        elif not above_wema21 and not above_wema30:
            bearish_factors.append("Below WEMA21 & WEMA30")

        if sharpe > 1:
            bullish_factors.append(f"Sharpe {sharpe:.1f}")
        elif sharpe < 0:
            bearish_factors.append(f"Sharpe {sharpe:.1f}")

        if sortino > 1:
            bullish_factors.append(f"Sortino {sortino:.1f}")
        elif sortino < 0:
            bearish_factors.append(f"Sortino {sortino:.1f}")

        if stage == 2 and tt_score >= 7:
            bullish_factors.append(f"Stage 2 TT {tt_score}/8 (prime uptrend)")
        elif stage == 2:
            bullish_factors.append(f"Stage 2 TT {tt_score}/8 (advancing)")
        elif stage == 3:
            bearish_factors.append(f"Stage 3 (topping/distribution)")
        elif stage == 4:
            bearish_factors.append(f"Stage 4 (declining)")

        if rel_vol >= 2.0:
            bullish_factors.append(f"RelVol {rel_vol:.1f}x")

        if above_dsma200:
            bullish_factors.append("Above DSMA200")
        else:
            bearish_factors.append("Below DSMA200")

        if h52_chg < -30:
            bearish_factors.append(f"52wH {h52_chg:.0f}%")

        # ---- Signal classification ----
        signal, confidence, reason = self._classify(
            score, bullish_factors, bearish_factors, rs, rsi, sharpe, sortino,
            above_wema21, above_wema30, above_dsma200, h52_chg,
            stage=stage, tt_score=tt_score
        )

        # ---- Verdict (2-3 sentences) ----
        verdict = self._build_verdict(
            symbol, signal, confidence, bullish_factors, bearish_factors,
            score, rs, rsi, sharpe, pl_pct, vol, rel_vol, stage
        )

        return {
            'signal': signal,
            'confidence': confidence,
            'reason': reason,
            'verdict': verdict,
        }

    def _classify(self, score, bull, bear, rs, rsi, sharpe, sortino,
                  above_w21, above_w30, above_d200, h52_chg,
                  stage=1, tt_score=0) -> tuple:
        """Return (signal_label, confidence_stars, primary_reason)."""

        # Strong Buy
        if score >= self.strong_buy_score and rs > 0 and above_w21 and sharpe > 0.5:
            conf = 5 if (score >= 85 and rs > 5.0 and sortino > 1) else 4
            reason = f"Score {score:.0f}, strong across RS/trend/risk"
            return self.SIGNAL_STRONG_BUY, conf, reason

        # Buy — require Stage 1/2 (not topping or declining)
        if score >= self.buy_score and stage <= 2 and (rs > 0 or tt_score >= 4):
            conf = 4 if (rs > 3.0 and sharpe > 0.5) else 3
            reason = f"Score {score:.0f}, Stage {stage} TT {tt_score}/8"
            return self.SIGNAL_BUY, conf, reason

        # Strong Sell
        if score < self.strong_sell_score and sharpe < 0 and not above_w21 and not above_w30:
            conf = 5 if (score < 15 and h52_chg < -30 and sortino < 0) else 4
            reason = f"Score {score:.0f}, weak across all categories"
            return self.SIGNAL_STRONG_SELL, conf, reason

        # Sell
        if score < self.sell_score and (sharpe < 0 or (not above_w21 and not above_w30)):
            conf = 4 if (rs < -3.0 and h52_chg < -20) else 3
            reason = f"Score {score:.0f}, declining trend & negative risk"
            return self.SIGNAL_SELL, conf, reason

        # Hold
        conf = 3 if abs(len(bull) - len(bear)) <= 1 else 2
        reason = f"Score {score:.0f}, mixed signals"
        return self.SIGNAL_HOLD, conf, reason

    def _build_verdict(self, symbol, signal, confidence, bull, bear,
                       score, rs, rsi, sharpe, pl_pct, vol, rel_vol, stage=1) -> str:
        """Build a concise 2-3 sentence verdict."""
        stars = "★" * confidence + "☆" * (5 - confidence)
        parts = [f"{symbol}: {signal} {stars}"]

        # First sentence — headline with key supporting factor
        if bull:
            parts.append(f"— {bull[0]}.")
        elif bear:
            parts.append(f"— {bear[0]}.")

        # Second sentence — risk/return context
        if sharpe > 1:
            parts.append(f"Excellent risk-adjusted returns (Sharpe {sharpe:.1f}).")
        elif sharpe > 0:
            parts.append(f"Positive risk-adjusted returns (Sharpe {sharpe:.1f}).")
        elif sharpe > -0.5:
            parts.append(f"Marginal risk-return profile (Sharpe {sharpe:.1f}).")
        else:
            parts.append(f"Poor risk-adjusted returns (Sharpe {sharpe:.1f}).")

        # Third sentence — notable conditions
        extras = []
        if rel_vol >= 2.0:
            extras.append(f"volume spike ({rel_vol:.1f}x)")
        if stage == 3:
            extras.append("Stage 3 — topping")
        elif stage == 4:
            extras.append("Stage 4 — declining")
        if pl_pct > 20:
            extras.append(f"profit {pl_pct:.0f}%")
        elif pl_pct < -20:
            extras.append(f"loss {pl_pct:.0f}%")

        if extras:
            parts.append("Note: " + ", ".join(extras) + ".")

        return " ".join(parts)


# ------------------------------------------------------------------
# Convenience
# ------------------------------------------------------------------
def generate_signals(scored_dataset: pd.DataFrame) -> pd.DataFrame:
    """Convenience function to generate signals for a scored dataset."""
    engine = SignalEngine()
    return engine.generate_signals(scored_dataset)
