#!/usr/bin/env python3
"""
Stock Scoring & Ranking Module
Produces a composite score (0-100) per stock combining RS, Trend, Momentum, Risk, and Value/Volume.
Scores are config-driven with adjustable category weights.
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
    return float(val)


class StockScorer:
    """Compute composite scores for every stock in the comprehensive dataset."""

    def __init__(self, config_overrides: Optional[Dict] = None):
        self.config = get_config()
        # Default weights (each 0-20 points)
        defaults = {
            "rs_weight": 20,
            "trend_weight": 20,
            "momentum_weight": 20,
            "risk_weight": 20,
            "value_volume_weight": 20,
        }
        scoring_cfg = self.config.get_setting("scoring_settings", {})
        if isinstance(scoring_cfg, dict):
            defaults.update(scoring_cfg)
        if config_overrides:
            defaults.update(config_overrides)
        self.weights = defaults

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def score_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add scoring columns to the comprehensive dataset and return it.
        
        New columns added:
            RS_Score, Trend_Score, Momentum_Score, Risk_Score, Value_Volume_Score,
            Composite_Score, Score_Rank
        """
        if df.empty:
            return df

        result = df.copy()
        result['RS_Score'] = result.apply(self._rs_score, axis=1).fillna(10)
        result['Trend_Score'] = result.apply(self._trend_score, axis=1).fillna(10)
        result['Momentum_Score'] = result.apply(self._momentum_score, axis=1).fillna(10)
        result['Risk_Score'] = result.apply(self._risk_score, axis=1).fillna(10)
        result['Value_Volume_Score'] = result.apply(self._value_volume_score, axis=1).fillna(10)

        # Weighted composite (normalise to 0-100 scale)
        # Each category score is 0-20.  Weight of 20 means "standard contribution".
        # Scale: score_i * (weight_i / 20) so that default weight=20 leaves score unchanged.
        # Sum of 5 categories each 0-20 gives 0-100 when all weights are 20.
        result['Composite_Score'] = (
            result['RS_Score'] * (self.weights['rs_weight'] / 20.0) +
            result['Trend_Score'] * (self.weights['trend_weight'] / 20.0) +
            result['Momentum_Score'] * (self.weights['momentum_weight'] / 20.0) +
            result['Risk_Score'] * (self.weights['risk_weight'] / 20.0) +
            result['Value_Volume_Score'] * (self.weights['value_volume_weight'] / 20.0)
        )

        result['Composite_Score'] = result['Composite_Score'].clip(0, 100).round(1)
        result['Score_Rank'] = result['Composite_Score'].rank(ascending=False, method='min', na_option='bottom').astype('Int64')

        return result

    # ------------------------------------------------------------------
    # Category scorers – each returns 0-20
    # ------------------------------------------------------------------
    def _rs_score(self, row) -> float:
        """Relative Strength Score (0-20). RS is the single most important factor.
        RS is in percentage points (stock_return - benchmark_return) * 100 over
        the configured rs_calculation_period (default 90 days).
        Typical range: -20 to +20."""
        rs = _safe(row, 'RS', 0.0)
        score = 10.0  # neutral baseline

        # RS absolute value contribution (0 to +/-8 points)
        # Thresholds in percentage points over the RS calculation period
        if rs > 10.0:
            score += 8  # strong outperformer: max points
        elif rs > 5.0:
            score += 4 + (rs - 5.0) * 0.8  # scale 4-8
        elif rs > 0.0:
            score += rs * 0.8  # scale 0-4
        elif rs > -5.0:
            score += rs * 0.8  # scale 0 to -4
        elif rs > -10.0:
            score += -4 + (rs + 5.0) * 0.8  # scale -4 to -8
        else:
            score += -8  # deep underperformer: max penalty

        # RS rank bonus — top quartile gets +2, bottom quartile gets -2
        if rs > 7.0:
            score += 2
        elif rs < -7.0:
            score -= 2

        return np.clip(score, 0, 20)

    def _trend_score(self, row) -> float:
        """Trend Score (0-20). Evaluates CMP position relative to key moving averages."""
        cmp = _safe(row, 'CMP', 0)
        if cmp <= 0:
            return 10.0

        score = 0.0
        ma_checks = [
            ('WEMA21', 4),   # 4 points for above Weekly EMA 21
            ('WEMA30', 4),   # 4 points for above Weekly EMA 30
            ('SMA50', 4),    # 4 points for above SMA 50 (current, not displaced)
            ('SMA200', 4),   # 4 points for above SMA 200 (current, not displaced)
        ]

        for ma_col, points in ma_checks:
            ma_val = _safe(row, ma_col, 0)
            if ma_val <= 0:
                score += points / 2  # neutral if MA not available
            elif cmp > ma_val:
                score += points
            elif cmp > ma_val * 0.98:  # within 2% — partial credit
                score += points * 0.5

        # Bonus for CMP well above all MAs (+2) or well below all (-penalty already 0)
        above_count = sum(1 for col in ['WEMA21', 'WEMA30', 'SMA50', 'SMA200']
                          if _safe(row, col, 0) > 0 and cmp > _safe(row, col, 0))
        if above_count == 4:
            score = min(score + 4, 20)

        return np.clip(score, 0, 20)

    def _momentum_score(self, row) -> float:
        """Momentum Score (0-20). Uses Minervini stage + Trend Template scoring."""
        stage = _safe(row, 'Stage', 1)
        tt_score = _safe(row, 'TT_Score', 0)
        score = 5.0  # conservative baseline

        # Stage-based contribution (primary driver)
        if stage == 2:
            if tt_score >= 7:
                score += 10  # Full Trend Template — top momentum
            elif tt_score >= 6:
                score += 8   # Strong Stage 2
            else:
                score += 6   # Early Stage 2
        elif stage == 1:
            if tt_score >= 5:
                score += 4  # Basing with some criteria met — potential breakout
            else:
                score += 2  # Deep basing — neutral
        elif stage == 3:
            score += 1  # Topping — losing momentum
        elif stage == 4:
            score += 0  # Declining — no momentum credit

        # Daily change contribution (kept — captures immediate momentum)
        daily_chg = _safe(row, 'Daily_Change_%', 0)
        if daily_chg > 2:
            score += 3
        elif daily_chg > 0:
            score += 1.5
        elif daily_chg < -2:
            score -= 2
        elif daily_chg < 0:
            score -= 1

        return np.clip(score, 0, 20)

    def _risk_score(self, row) -> float:
        """Risk Score (0-20). Higher score = better risk-adjusted profile."""
        score = 10.0

        # Sharpe ratio contribution
        sharpe = _safe(row, 'Sharpe_Ratio', 0)
        if sharpe > 2:
            score += 5
        elif sharpe > 1:
            score += 4
        elif sharpe > 0.5:
            score += 2
        elif sharpe > 0:
            score += 1
        elif sharpe > -0.5:
            score -= 1
        elif sharpe > -1:
            score -= 3
        else:
            score -= 5

        # Sortino ratio contribution
        sortino = _safe(row, 'Sortino_Ratio', 0)
        if sortino > 2:
            score += 4
        elif sortino > 1:
            score += 3
        elif sortino > 0.5:
            score += 1
        elif sortino < 0:
            score -= 3

        # Volatility penalty
        vol = _safe(row, 'Standard_Deviation', 0)
        if vol > 40:
            score -= 3
        elif vol > 30:
            score -= 2
        elif vol > 20:
            score -= 1
        elif vol < 10:
            score += 1

        return np.clip(score, 0, 20)

    def _value_volume_score(self, row) -> float:
        """Value & Volume Score (0-20)."""
        score = 10.0

        # 52-week position — near 52w low with improving signals = value
        h52_chg = _safe(row, '52wHCh%', 0)
        l52_chg = _safe(row, '52wLCh%', 0)

        # Closer to 52w high is better (less negative 52wHCh%)
        if h52_chg > -5:
            score += 3  # within 5% of 52w high
        elif h52_chg > -15:
            score += 1
        elif h52_chg < -30:
            score -= 2  # very far from high

        # Distance from 52w low — higher is better but extreme could be overextended
        if 10 < l52_chg < 50:
            score += 2  # healthy above low
        elif l52_chg <= 5:
            score -= 1  # near 52w low

        # DMA200 extension penalty
        dma_ext = _safe(row, 'DMA200_Extension_Pct', 0)
        if abs(dma_ext) > 30:
            score -= 2  # overextended either direction

        # Relative volume bonus
        rel_vol = _safe(row, 'Relative_Volume', 0)
        if rel_vol >= 2.0:
            score += 2  # unusual volume interest
        elif rel_vol >= 1.5:
            score += 1

        # Week vs month volume trend
        wk_ratio = _safe(row, 'Week_Threshold_Ratio', 0)
        if wk_ratio > 1.0:
            score += 1  # recent volume pickup

        return np.clip(score, 0, 20)


def score_portfolio(comprehensive_dataset: pd.DataFrame, config_overrides: Optional[Dict] = None) -> pd.DataFrame:
    """Convenience function to score a comprehensive dataset."""
    scorer = StockScorer(config_overrides)
    return scorer.score_dataset(comprehensive_dataset)
