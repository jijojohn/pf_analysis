#!/usr/bin/env python3
"""
Interactive Dataset Filter Module
Provides filtering capabilities and interactive visualizations for comprehensive dataset
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime, date
import os
from config_manager import get_config
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works


class InteractiveFilter:
    """Interactive filtering and visualization for comprehensive dataset"""
    
    def __init__(self, comprehensive_dataset: pd.DataFrame):
        self.dataset = comprehensive_dataset.copy()
        self.filtered_dataset = self.dataset  # view, not copy — apply_filter replaces this
        self.config = get_config()
        self.filter_config = self.config.get_filter_config()
        self.tech_config = self.config.get_technical_config()
        
        # Define available filter criteria using configuration
        self.filter_criteria = self._create_filter_criteria()
        
        # Pre-compute which filters yield non-empty results (for nav link generation)
        self._nonempty_filters = set()
        for name, fn in self.filter_criteria.items():
            try:
                if not fn(self.dataset).empty:
                    self._nonempty_filters.add(name)
            except Exception:
                pass
    
    def _get_volume_config(self, key: str, default: float) -> float:
        """Get volume filter configuration value"""
        volume_config = self.config.get_setting("filter_thresholds.volume_filters", {})
        return volume_config.get(key, default)
    
    def _get_extension_config(self, key: str, default: float) -> float:
        """Get price extension configuration value"""
        extension_config = self.config.get_setting("filter_thresholds.price_extension", {})
        return extension_config.get(key, default)
    
    def _create_filter_criteria(self) -> Dict:
        """Create filter criteria using configuration settings"""
        return {
            # CMP vs WEMA filters
            "Stocks Below WEMA21": lambda df: df[df['CMP'] < df['WEMA21']],
            "Stocks Above WEMA21": lambda df: df[df['CMP'] > df['WEMA21']],
            "Stocks Below WEMA30": lambda df: df[df['CMP'] < df['WEMA30']],
            "Stocks Above WEMA30": lambda df: df[df['CMP'] > df['WEMA30']],
            
            # CMP vs DSMA filters
            "Stocks Below DSMA50": lambda df: df[df['CMP'] < df['DSMA50']],
            "Stocks Above DSMA50": lambda df: df[df['CMP'] > df['DSMA50']],
            "Stocks Below DSMA200": lambda df: df[df['CMP'] < df['DSMA200']],
            "Stocks Above DSMA200": lambda df: df[df['CMP'] > df['DSMA200']],
            
            # 52-Week High Change % filters using configuration
            **{f"52wHCh% > {threshold}%": lambda df, t=threshold: df[df['52wHCh%'] > t] 
               for threshold in self.filter_config.high_change_thresholds},
            "Near 52-Week High (within 5%)": lambda df: df[df['52wHCh%'] >= -5],
            "Near 52-Week High (within 10%)": lambda df: df[df['52wHCh%'] >= -10],
            
            # 52-Week Low Change % filters using configuration  
            **{f"52wLCh% < {threshold}%": lambda df, t=threshold: df[df['52wLCh%'] < t] 
               for threshold in self.filter_config.low_change_thresholds},
            "Near 52-Week Low (within 5%)": lambda df: df[df['52wLCh%'] <= 5],
            "Near 52-Week Low (within 10%)": lambda df: df[df['52wLCh%'] <= 10],
            
            # RSI filters using configuration
            f"RSI Below 50": lambda df: df[df['RSI'] < 50],
            f"RSI Above 50": lambda df: df[df['RSI'] > 50],
            f"Oversold (RSI < {self.tech_config.rsi_oversold})": lambda df: df[df['RSI'] < self.tech_config.rsi_oversold],
            f"Overbought (RSI > {self.tech_config.rsi_overbought})": lambda df: df[df['RSI'] > self.tech_config.rsi_overbought],
            f"RSI Neutral ({self.tech_config.rsi_oversold}-{self.tech_config.rsi_overbought})": lambda df: df[(df['RSI'] >= self.tech_config.rsi_oversold) & (df['RSI'] <= self.tech_config.rsi_overbought)],
            
            # Relative Strength (RS) filters using configuration
            f"Strong RS (RS > {self.filter_config.rs_strong})": lambda df: df[df['RS'] > self.filter_config.rs_strong],
            f"Weak RS (RS < {self.filter_config.rs_weak})": lambda df: df[df['RS'] < self.filter_config.rs_weak],
            f"Very Strong RS (RS > {self.filter_config.rs_very_strong})": lambda df: df[df['RS'] > self.filter_config.rs_very_strong],
            f"Very Weak RS (RS < {self.filter_config.rs_very_weak})": lambda df: df[df['RS'] < self.filter_config.rs_very_weak],
            
            # Volatility and performance filters
            "High Volatility (>3%)": lambda df: df[df['Standard_Deviation'] > 3],
            "Low Volatility (<1%)": lambda df: df[df['Standard_Deviation'] < 1],
            "Positive Sharpe Ratio": lambda df: df[df['Sharpe_Ratio'] > 0],
            "Negative Sharpe Ratio": lambda df: df[df['Sharpe_Ratio'] < 0],
            
            # Sortino Ratio filters (risk-adjusted returns using downside deviation)
            "Positive Sortino Ratio": lambda df: df[df['Sortino_Ratio'] > 0],
            "Negative Sortino Ratio": lambda df: df[df['Sortino_Ratio'] < 0],
            "Sortino Ratio > 1": lambda df: df[df['Sortino_Ratio'] > 1],
            "Sortino Ratio < 1": lambda df: df[(df['Sortino_Ratio'] < 1) & (df['Sortino_Ratio'] > 0)],
            "Sortino Ratio > 2": lambda df: df[df['Sortino_Ratio'] > 2],
            
            # Portfolio performance filters
            "In Profit": lambda df: df[df['Profit/Loss'] > 0],
            "In Loss": lambda df: df[df['Profit/Loss'] < 0],
            "High Allocation (>20%)": lambda df: df[df['Percentage_Allocation'] > 20],
            "Low Allocation (<5%)": lambda df: df[df['Percentage_Allocation'] < 5],
            
            # Combined technical filters
            "Bullish Trend (Above WEMA21 & WEMA30)": lambda df: df[(df['CMP'] > df['WEMA21']) & (df['CMP'] > df['WEMA30'])],
            "Bearish Trend (Below WEMA21 & WEMA30)": lambda df: df[(df['CMP'] < df['WEMA21']) & (df['CMP'] < df['WEMA30'])],
            "Above All Moving Averages": lambda df: df[(df['CMP'] > df['WEMA21']) & (df['CMP'] > df['WEMA30']) & (df['CMP'] > df['DSMA50']) & (df['CMP'] > df['DSMA200'])],
            "Below All Moving Averages": lambda df: df[(df['CMP'] < df['WEMA21']) & (df['CMP'] < df['WEMA30']) & (df['CMP'] < df['DSMA50']) & (df['CMP'] < df['DSMA200'])],
            
            # Volume filters
            f"High Relative Volume (>= {self._get_volume_config('relative_volume_threshold', 3.0)}x)": 
                lambda df: df[df.get('Relative_Volume', 0) >= self._get_volume_config('relative_volume_threshold', 3.0)],
            "Week Volume > 2x Month Average": 
                lambda df: df[df.get('Week_Threshold_Ratio', 0) > 1.0],
            f"Price Extended from 200 DMA (> {self._get_extension_config('dma_200_extension_threshold', 70.0)}%)": 
                lambda df: df[df.get('DMA200_Extension_Pct', 0) > self._get_extension_config('dma_200_extension_threshold', 70.0)],
            
            # Minervini Stage filters
            "Stage 2 — Advancing (Buy Zone)": lambda df: df[df.get('Stage', 0) == 2] if 'Stage' in df.columns else df.iloc[0:0],
            "Stage 1 — Basing (Watchlist)": lambda df: df[df.get('Stage', 0) == 1] if 'Stage' in df.columns else df.iloc[0:0],
            "Stage 3 — Topping (Take Profits)": lambda df: df[df.get('Stage', 0) == 3] if 'Stage' in df.columns else df.iloc[0:0],
            "Stage 4 — Declining (Exit)": lambda df: df[df.get('Stage', 0) == 4] if 'Stage' in df.columns else df.iloc[0:0],
            "Trend Template 7+/8 (Strongest Setups)": lambda df: df[df.get('TT_Score', 0) >= 7] if 'TT_Score' in df.columns else df.iloc[0:0],
            "Trend Template 6+/8 (Strong Setups)": lambda df: df[df.get('TT_Score', 0) >= 6] if 'TT_Score' in df.columns else df.iloc[0:0],
            
            # Higher High / Higher Low swing filters
            "Higher High & Higher Low (Bullish Swing)": lambda df: df[(df.get('HH', False) == True) & (df.get('HL', False) == True)] if 'HH' in df.columns else df.iloc[0:0],
            "Higher Low Only (Accumulation)": lambda df: df[(df.get('HL', False) == True) & (df.get('HH', False) == False)] if 'HL' in df.columns else df.iloc[0:0],
            "Lower Low (Bearish — Exit Signal)": lambda df: df[(df.get('HL', False) == False) & (df.get('HH', False) == False)] if 'HL' in df.columns else df.iloc[0:0],
            "Higher High Only (Topping Risk)": lambda df: df[(df.get('HH', False) == True) & (df.get('HL', False) == False)] if 'HH' in df.columns else df.iloc[0:0],
            
            # Default filter
            "All Stocks": lambda df: df  # No filter
        }
    
    @staticmethod
    def _safe_filename(name: str) -> str:
        """Convert a filter name to a browser-safe filename component."""
        return (name
                .replace(" ", "_")
                .replace("(", "")
                .replace(")", "")
                .replace("%", "pct")
                .replace(">", "_greater_than_")
                .replace("<", "_less_than_")
                .replace("=", "_equals_")
                .replace("&", "_and_")
                .replace("/", "_or_")
                .replace(":", "_")
                .replace("-", "_")
                .replace(".", "_")
                .replace(",", "_")
                .replace("'", "")
                .replace('"', ""))
    
    def apply_filter(self, filter_name: str) -> pd.DataFrame:
        """Apply selected filter to dataset"""
        if filter_name in self.filter_criteria:
            self.filtered_dataset = self.filter_criteria[filter_name](self.dataset)
            print(f"🔍 Applied filter: '{filter_name}'")
            print(f"📊 Filtered dataset: {len(self.filtered_dataset)} stocks from {len(self.dataset)} total")
            return self.filtered_dataset
        else:
            print(f"❌ Unknown filter: {filter_name}")
            return self.dataset
    
    def get_available_filters(self) -> List[str]:
        """Get list of available filter criteria"""
        return list(self.filter_criteria.keys())
    
    def _get_filter_specific_guidance(self, filter_name: str) -> dict:
        """Get filter-specific guidance for report headers"""
        guidance = {
            "Week Volume > 2x Month Average": {
                "what": "Stocks where the last 5-day average volume exceeds 2x the monthly (21-day) average volume. This identifies gradual volume increases during the current week, suggesting building accumulation or emerging market interest.",
                "how": "• <strong>Check volume columns:</strong> Compare Week_Avg_Volume vs Volume_Threshold_2x (2x monthly average)<br>• <strong>Volume ratio:</strong> Week_Threshold_Ratio >1.0 means current week exceeds the 2x monthly threshold<br>• <strong>Gradual buildup:</strong> This filter is more sensitive than yearly comparisons, catching early trends<br>• <strong>Confirm with price:</strong> Look for steady price advance or base-building patterns<br>• <strong>Monitor trend:</strong> Use WEMA21/30 to confirm if volume increase accompanies uptrend",
                "action": "• <strong>Ratio 1.0-1.2:</strong> Moderate buildup - early accumulation signal, monitor closely<br>• <strong>Ratio 1.2-1.5:</strong> Strong buildup - increasing interest, consider gradual entry<br>• <strong>Ratio >1.5:</strong> Significant surge - investigate catalyst, potential breakout imminent<br>• <strong>With uptrend (above WEMAs):</strong> Bullish accumulation - favorable entry on pullbacks<br>• <strong>With basing pattern:</strong> Potential breakout setup - prepare for position entry<br>• <strong>With downtrend:</strong> Distribution or capitulation - exercise caution, wait for reversal"
            },
            f"High Relative Volume (>= {self._get_volume_config('relative_volume_threshold', 3.0)}x)": {
                "what": f"Stocks with current day volume at least {self._get_volume_config('relative_volume_threshold', 3.0)}x their 20-day average. Identifies single-day volume spikes often caused by news, earnings, or institutional activity.",
                "how": "• <strong>Relative_Volume column:</strong> Shows current volume vs 20-day average<br>• <strong>Check Daily_Change_%:</strong> Understand if volume spike is on up or down move<br>• <strong>Review recent news:</strong> Identify catalyst for unusual volume<br>• <strong>Compare with Week_Year ratio:</strong> Distinguish single-day spike from sustained increase",
                "action": "• <strong>With positive price:</strong> Potential breakout - wait for confirmation or enter with tight stop<br>• <strong>With negative price:</strong> Panic selling or distribution - avoid or short with caution<br>• <strong>Research catalyst:</strong> News-driven spikes often reverse, structural changes persist<br>• <strong>Set alerts:</strong> Monitor if elevated volume continues over multiple days"
            },
            f"Price Extended from 200 DMA (> {self._get_extension_config('dma_200_extension_threshold', 70.0)}%)": {
                "what": f"Stocks trading more than {self._get_extension_config('dma_200_extension_threshold', 70.0)}% above their 200-day moving average. Indicates strong momentum but also potential overextension and mean reversion risk.",
                "how": "• <strong>DMA200_Extension_Pct:</strong> Shows percentage above/below 200 DMA<br>• <strong>Check RSI:</strong> RSI >70 confirms overbought conditions<br>• <strong>Review allocation:</strong> High allocations in extended stocks increase portfolio risk<br>• <strong>Compare with DSMA200:</strong> Displaced moving average provides dynamic support level",
                "action": "• <strong>Profitable positions:</strong> Consider partial profit-taking to lock in gains<br>• <strong>RSI >70:</strong> High probability of pullback - raise stops or reduce position<br>• <strong>New entries:</strong> Wait for pullback to 50% retracement or key support<br>• <strong>Trend followers:</strong> Trail stop below recent swing lows to protect gains"
            },
            "In Profit": {
                "what": "All stocks currently showing positive returns (Profit/Loss > 0). Helps identify winners in your portfolio for profit-taking or position management decisions.",
                "how": "• <strong>Sort by Profit/Loss:</strong> Identify biggest winners<br>• <strong>Check Allocation %:</strong> Ensure winners haven't become oversized<br>• <strong>Review Sharpe Ratio:</strong> Verify risk-adjusted performance<br>• <strong>Monitor RSI & extension:</strong> Assess if stocks are overextended",
                "action": "• <strong>Large gains (>30%):</strong> Take partial profits, let remainder run<br>• <strong>Oversized positions (>15%):</strong> Trim to maintain diversification<br>• <strong>High RSI (>70):</strong> Set trailing stops to protect gains<br>• <strong>Strong fundamentals:</strong> Hold winners, don't sell too early"
            },
            "In Loss": {
                "what": "All stocks currently showing negative returns (Profit/Loss < 0). Critical for loss management, stop-loss decisions, and portfolio cleanup.",
                "how": "• <strong>Sort by Profit/Loss:</strong> Identify biggest losers<br>• <strong>Check thesis:</strong> Determine if loss is temporary or fundamental change<br>• <strong>Review RSI:</strong> RSI <30 may indicate oversold bounce opportunity<br>• <strong>Analyze Standard_Deviation:</strong> High volatility increases risk",
                "action": "• <strong>Small losses (<-10%):</strong> Re-evaluate thesis, hold if intact<br>• <strong>Medium losses (-10% to -20%):</strong> Strict review - exit if thesis broken<br>• <strong>Large losses (>-20%):</strong> Strong sell candidate unless high conviction<br>• <strong>Averaging down:</strong> Only if fundamentals strong and RSI <30"
            },
            "RSI > 70": {
                "what": "Stocks with RSI (Relative Strength Index) above 70, indicating overbought conditions. Momentum is strong but pullback risk is elevated.",
                "how": "• <strong>RSI column:</strong> Shows current momentum reading<br>• <strong>Check Daily_Change_%:</strong> Assess if momentum is accelerating<br>• <strong>Review price vs WEMA21/30:</strong> Confirm uptrend strength<br>• <strong>Compare allocations:</strong> High RSI stocks shouldn't dominate portfolio",
                "action": "• <strong>RSI 70-80:</strong> Overbought but can continue - trail stops, partial profit<br>• <strong>RSI >80:</strong> Extremely overbought - high reversal risk, take profits<br>• <strong>In profit:</strong> Raise stops to breakeven or recent support<br>• <strong>New positions:</strong> Wait for RSI to cool below 60 before entering"
            },
            "RSI < 30": {
                "what": "Stocks with RSI below 30, indicating oversold conditions. Potential bounce candidates but confirm downtrend hasn't broken fundamentals.",
                "how": "• <strong>RSI column:</strong> Shows current momentum reading<br>• <strong>Check loss position:</strong> In Loss stocks may have better bounce potential<br>• <strong>Review 52wLCh%:</strong> How close to 52-week lows?<br>• <strong>Confirm with volume:</strong> Low volume selloff more likely to reverse",
                "action": "• <strong>RSI 20-30:</strong> Oversold, watch for reversal signals before entry<br>• <strong>RSI <20:</strong> Extremely oversold - potential bounce but verify no bad news<br>• <strong>Quality stocks:</strong> Consider averaging down in small increments<br>• <strong>Weak fundamentals:</strong> Avoid catching falling knife, let dust settle"
            },
            "All Stocks": {
                "what": "Complete unfiltered portfolio view showing all stocks with comprehensive technical indicators, risk metrics, and performance data.",
                "how": "• <strong>Sort by any metric:</strong> Click column headers for multi-dimensional analysis<br>• <strong>Compare across indicators:</strong> RSI, RS, Sharpe Ratio, Allocation<br>• <strong>Use as baseline:</strong> Compare against specific filter results<br>• <strong>Export data:</strong> Download comprehensive dataset for custom analysis",
                "action": "• <strong>Scan RSI extremes:</strong> Identify overbought (>70) and oversold (<30) stocks<br>• <strong>Review allocations:</strong> Ensure no single stock exceeds 20% of portfolio<br>• <strong>Check losers:</strong> Stocks with negative Sharpe Ratio need attention<br>• <strong>Apply filters:</strong> Use specific filters to drill into subsets of interest"
            },
            "Bullish Trend (Above WEMA21 & WEMA30)": {
                "what": "Stocks trading above both WEMA21 and WEMA30 moving averages, indicating short to intermediate-term bullish momentum and uptrend confirmation.",
                "how": "• <strong>Verify trend:</strong> Both moving averages should be sloping upward<br>• <strong>Check Daily_Change_%:</strong> Positive daily changes confirm momentum<br>• <strong>Review allocation:</strong> Consider overweighting strong trending stocks<br>• <strong>Monitor RSI:</strong> Avoid entries when RSI >70 (overheated)",
                "action": "• <strong>Existing positions:</strong> Hold and let trends run, trail stops below WEMAs<br>• <strong>New entries:</strong> Buy on pullbacks to WEMA21 support<br>• <strong>Exit signal:</strong> Close below WEMA21 warrants profit-taking<br>• <strong>Portfolio allocation:</strong> Can maintain higher weights in strong uptrends"
            },
            "Bearish Trend (Below WEMA21 & WEMA30)": {
                "what": "Stocks trading below both WEMA21 and WEMA30, signaling downtrends and potential continued weakness until trend reversal confirmed.",
                "how": "• <strong>Identify weakness:</strong> Both WEMAs acting as resistance<br>• <strong>Check RSI:</strong> RSI <30 may signal oversold bounce opportunity<br>• <strong>Review P/L:</strong> Determine if stop-loss levels breached<br>• <strong>Monitor volume:</strong> High volume selloff more concerning than low volume drift",
                "action": "• <strong>Cut losses:</strong> Exit or reduce positions if fundamental thesis broken<br>• <strong>Oversold bounce:</strong> Only trade if RSI <20 and quality stock<br>• <strong>Wait for confirmation:</strong> Require close above WEMA21 before re-entering<br>• <strong>Reduce allocation:</strong> Minimize exposure to downtrending stocks"
            },
            "Above All Moving Averages": {
                "what": "Stocks trading above WEMA21, WEMA30, DSMA50, and DSMA200 - the strongest trend confirmation indicating all timeframes are bullish.",
                "how": "• <strong>Confirm multi-timeframe trend:</strong> All MAs sloping upward is ideal<br>• <strong>Check extension:</strong> Review DMA200_Extension_Pct for overextension risk<br>• <strong>Monitor momentum:</strong> RSI and Daily_Change_% show trend strength<br>• <strong>Assess allocations:</strong> These leaders may deserve higher weights",
                "action": "• <strong>Core holdings:</strong> Can hold larger positions in these strongest stocks<br>• <strong>Pullback entries:</strong> Buy dips to DSMA50 or WEMA30 support<br>• <strong>Trail stops:</strong> Use DSMA50 or WEMA30 as dynamic stop levels<br>• <strong>Rebalancing:</strong> Take partial profits if allocation exceeds 20%"
            },
            "Below All Moving Averages": {
                "what": "Stocks below all key moving averages (WEMA21, WEMA30, DSMA50, DSMA200) - strongest bearish signal requiring caution or exit.",
                "how": "• <strong>Assess damage:</strong> Check Profit/Loss and drawdown severity<br>• <strong>Review fundamentals:</strong> Determine if decline is technical or fundamental<br>• <strong>Check RSI:</strong> Extreme oversold (RSI <20) may indicate capitulation<br>• <strong>Monitor for reversal:</strong> Need closes above at least WEMA21 to rebuild trust",
                "action": "• <strong>High priority review:</strong> These are your weakest positions<br>• <strong>Consider exits:</strong> Unless strong fundamental conviction, exit or reduce size<br>• <strong>Strict stops:</strong> Any further decline below recent lows is final exit signal<br>• <strong>Reallocation:</strong> Move capital to Above All Moving Averages stocks"
            },
            "Near 52-Week High (within 5%)": {
                "what": "Stocks within 5% of their 52-week highs, showing extreme relative strength and potential breakout candidates or overextension risk.",
                "how": "• <strong>Check 52wHCh%:</strong> Values between -5% to 0% indicate proximity to highs<br>• <strong>Review volume:</strong> High volume near highs suggests accumulation<br>• <strong>Monitor RSI:</strong> RSI >70 increases pullback risk<br>• <strong>Assess profit level:</strong> Significant gains may warrant profit-taking",
                "action": "• <strong>Breakout watch:</strong> New highs with volume may signal continuation<br>• <strong>Profit-taking:</strong> Take partial profits if RSI >75 or allocation >15%<br>• <strong>Tight stops:</strong> Trail stops to lock in gains if stock breaks to new high<br>• <strong>New entries:</strong> Wait for breakout and retest before adding positions"
            },
            "Near 52-Week Low (within 5%)": {
                "what": "Stocks within 5% of 52-week lows, indicating significant weakness. Can be value opportunities or continued deterioration depending on context.",
                "how": "• <strong>Check 52wLCh%:</strong> Values between 0% to 5% show proximity to lows<br>• <strong>Review RSI:</strong> RSI <30 may indicate oversold capitulation<br>• <strong>Analyze fundamentals:</strong> Determine if decline is justified<br>• <strong>Check volume:</strong> Climax selling on high volume can mark bottoms",
                "action": "• <strong>Quality stocks:</strong> RSI <20 with good fundamentals = potential value<br>• <strong>Falling knives:</strong> Avoid stocks with deteriorating fundamentals<br>• <strong>Staged entry:</strong> If accumulating, do so in small increments<br>• <strong>Strict stops:</strong> Exit immediately if stock breaks to new 52-week low"
            },
            "High Volatility (>3%)": {
                "what": "Stocks with standard deviation above 3%, indicating high daily price swings and elevated risk requiring larger position sizing caution.",
                "how": "• <strong>Standard_Deviation column:</strong> Shows average daily volatility percentage<br>• <strong>Check Sharpe Ratio:</strong> Determine if volatility is compensated by returns<br>• <strong>Review allocation:</strong> High volatility stocks should have smaller positions<br>• <strong>Monitor Daily_Change_%:</strong> Track magnitude of recent swings",
                "action": "• <strong>Position sizing:</strong> Reduce allocation to 5-10% maximum per stock<br>• <strong>Wider stops:</strong> Use 2-3x normal stop distance to avoid whipsaws<br>• <strong>Options strategies:</strong> Consider hedging with protective puts<br>• <strong>Sharpe <0.5:</strong> High volatility without returns = exit candidates"
            },
            "Low Volatility (<1%)": {
                "what": "Stocks with standard deviation below 1%, showing stable price action suitable for conservative investors or base-building phases.",
                "how": "• <strong>Standard_Deviation:</strong> Low values indicate price stability<br>• <strong>Check trend:</strong> Determine if consolidating in uptrend or downtrend<br>• <strong>Review volume:</strong> Low volatility + low volume may signal lack of interest<br>• <strong>Assess breakout potential:</strong> Tight ranges often precede big moves",
                "action": "• <strong>Coiled spring:</strong> Low volatility can precede volatility expansion<br>• <strong>Monitor for breakouts:</strong> Set alerts for volume surges or range breaks<br>• <strong>Conservative allocation:</strong> Safe for larger position sizes if desired<br>• <strong>Accumulation phase:</strong> Stable prices good for building positions gradually"
            },
            "High Allocation (>20%)": {
                "what": "Stocks representing more than 20% of portfolio value, indicating concentration risk that violates diversification principles.",
                "how": "• <strong>Percentage_Allocation:</strong> Shows current portfolio weight<br>• <strong>Review performance:</strong> Often result of strong gains, not new capital<br>• <strong>Check RSI & extension:</strong> Overweight positions near extremes are risky<br>• <strong>Assess conviction:</strong> Ensure high allocation is intentional, not neglect",
                "action": "• <strong>Mandatory rebalancing:</strong> Trim positions above 20% to 15% or below<br>• <strong>Take profits:</strong> Lock in gains by selling enough shares to reduce weight<br>• <strong>Trail stops:</strong> Protect remaining position with tight trailing stops<br>• <strong>Risk management:</strong> Single stock should never exceed 25% of portfolio"
            },
            "Low Allocation (<5%)": {
                "what": "Stocks representing less than 5% of portfolio, including small positions and potential candidates for elimination or scaling up.",
                "how": "• <strong>Percentage_Allocation:</strong> Small position sizes<br>• <strong>Review Sharpe Ratio:</strong> Determine if worth keeping<br>• <strong>Check conviction:</strong> Small positions often indicate low confidence<br>• <strong>Assess opportunity cost:</strong> Compare to better opportunities",
                "action": "• <strong>Negative Sharpe:</strong> Close small losing positions - opportunity cost too high<br>• <strong>Positive Sharpe:</strong> Consider adding to winners if thesis strengthens<br>• <strong>Portfolio cleanup:</strong> Eliminate positions below 2% unless strategic<br>• <strong>Focus capital:</strong> Concentrate on highest conviction 10-15 positions"
            },
            "Positive Sharpe Ratio": {
                "what": "Stocks with Sharpe Ratio >0, meaning returns exceed risk. Higher values indicate better risk-adjusted performance worth maintaining.",
                "how": "• <strong>Sharpe_Ratio column:</strong> Measures risk-adjusted returns<br>• <strong>Sort descending:</strong> Identify best risk-adjusted performers<br>• <strong>Compare similar stocks:</strong> Sharpe Ratio enables apples-to-apples comparison<br>• <strong>Review allocations:</strong> High Sharpe stocks can justify higher weights",
                "action": "• <strong>Sharpe >1.0:</strong> Excellent risk-adjusted returns - consider increasing allocation<br>• <strong>Sharpe 0.5-1.0:</strong> Good performance - maintain or slightly increase<br>• <strong>Sharpe 0-0.5:</strong> Marginal - monitor for improvement or deterioration<br>• <strong>Portfolio construction:</strong> Overweight highest Sharpe Ratio stocks"
            },
            "Negative Sharpe Ratio": {
                "what": "Stocks with Sharpe Ratio <0, meaning losses or returns below risk-free rate. These positions destroy risk-adjusted returns and require action.",
                "how": "• <strong>Sharpe_Ratio column:</strong> Negative values indicate underperformance<br>• <strong>Check Profit/Loss:</strong> Quantify actual losses<br>• <strong>Review thesis:</strong> Determine if problem is temporary or structural<br>• <strong>Compare alternatives:</strong> Identify better risk-adjusted opportunities",
                "action": "• <strong>Immediate review:</strong> All negative Sharpe positions need evaluation<br>• <strong>Exit priority:</strong> Close positions with Sharpe <-0.5 unless strong conviction<br>• <strong>Opportunity cost:</strong> Capital better deployed in positive Sharpe stocks<br>• <strong>Portfolio drag:</strong> Negative Sharpe stocks hurt overall portfolio performance"
            },
            "Positive Sortino Ratio": {
                "what": "Stocks with Sortino Ratio >0, meaning returns exceed downside risk. Sortino is superior to Sharpe as it only penalizes harmful volatility (downside), not upside volatility.",
                "how": "• <strong>Sortino_Ratio column:</strong> Measures risk-adjusted returns using downside deviation<br>• <strong>Sort descending:</strong> Identify best performers relative to downside risk<br>• <strong>Compare with Sharpe:</strong> Sortino often higher for asymmetric return profiles<br>• <strong>Review allocations:</strong> High Sortino stocks can justify higher weights",
                "action": "• <strong>Sortino >2.0:</strong> Excellent downside-adjusted returns - strong core holdings<br>• <strong>Sortino 1.0-2.0:</strong> Very good performance - maintain or increase allocation<br>• <strong>Sortino 0-1.0:</strong> Positive but modest - monitor for improvement<br>• <strong>Portfolio construction:</strong> Prioritize stocks with highest Sortino ratios"
            },
            "Negative Sortino Ratio": {
                "what": "Stocks with Sortino Ratio <0, indicating losses with negative downside-adjusted returns. High priority for review and potential exit.",
                "how": "• <strong>Sortino_Ratio column:</strong> Negative values show poor downside risk management<br>• <strong>Check Profit/Loss:</strong> Quantify actual losses and downside capture<br>• <strong>Compare alternatives:</strong> Find stocks with positive Sortino ratios<br>• <strong>Review fundamentals:</strong> Determine if reversible or structural issue",
                "action": "• <strong>Immediate review:</strong> All negative Sortino positions need evaluation<br>• <strong>Exit priority:</strong> Close positions with Sortino <-1.0 unless exceptional conviction<br>• <strong>Risk management:</strong> These stocks disproportionately hurt during downturns<br>• <strong>Opportunity cost:</strong> Capital better deployed in positive Sortino stocks"
            },
            "Sortino Ratio > 1": {
                "what": "Stocks with Sortino Ratio above 1, indicating strong risk-adjusted returns relative to downside risk. These stocks provide good returns without excessive downside volatility.",
                "how": "• <strong>Sortino > 1:</strong> Returns significantly exceed downside risk<br>• <strong>Compare to Sharpe:</strong> If Sortino much higher, stock has favorable upside asymmetry<br>• <strong>Check trend:</strong> Verify with moving average alignment<br>• <strong>Review allocation:</strong> Can justify larger position sizes",
                "action": "• <strong>Sortino 1.0-1.5:</strong> Good risk-adjusted performance - maintain positions<br>• <strong>Sortino 1.5-2.0:</strong> Very good - consider increasing allocation<br>• <strong>Sortino >2.0:</strong> Excellent - core holdings, can be 10-15% positions<br>• <strong>Portfolio building:</strong> Build portfolio around Sortino >1 stocks"
            },
            "Sortino Ratio > 2": {
                "what": "Stocks with Sortino Ratio above 2, elite performers with exceptional downside risk management. Top tier holdings for core portfolio allocation.",
                "how": "• <strong>Sortino > 2:</strong> Exceptional risk-adjusted returns with minimal downside<br>• <strong>Verify sustainability:</strong> Check if recent performance spike or consistent<br>• <strong>Review allocations:</strong> These stocks deserve higher weights<br>• <strong>Monitor for changes:</strong> Watch for Sortino deterioration as early warning",
                "action": "• <strong>Core holdings:</strong> Can allocate 10-20% per position if multiple stocks qualify<br>• <strong>Portfolio anchor:</strong> Build portfolio around these elite performers<br>• <strong>Rebalancing:</strong> Allow these winners to run, only trim if exceed 20% allocation<br>• <strong>Risk management:</strong> Trail stops below key moving averages to protect gains<br>• <strong>New capital:</strong> Prioritize deployment into Sortino >2 stocks on pullbacks"
            },
            "Sortino Ratio < 1": {
                "what": "Stocks with Sortino Ratio between 0 and 1, showing positive returns but modest downside-adjusted performance. Requires monitoring for improvement.",
                "how": "• <strong>Sortino 0-1:</strong> Returns exceed downside risk but not by large margin<br>• <strong>Compare to Sharpe:</strong> If both are low, stock lacks strong risk-adjusted returns<br>• <strong>Check trend:</strong> Is Sortino improving or deteriorating?<br>• <strong>Review allocation:</strong> Should not be large positions unless conviction is high",
                "action": "• <strong>Sortino 0.5-1.0:</strong> Acceptable but monitor - look for improvement trend<br>• <strong>Sortino 0-0.5:</strong> Marginal performance - consider better alternatives<br>• <strong>Portfolio weight:</strong> Keep positions modest (5-10% max) unless thesis very strong<br>• <strong>Action plan:</strong> Set watchlist for Sortino to improve above 1.0 or exit if deteriorates<br>• <strong>Comparison:</strong> Regularly compare against Sortino >1 opportunities for reallocation"
            },
            f"Strong RS (RS > {self.filter_config.rs_strong})": {
                "what": f"Stocks with Relative Strength above {self.filter_config.rs_strong}, outperforming the market average. Strong momentum candidates for continued outperformance.",
                "how": "• <strong>RS column:</strong> Compares stock performance vs market average<br>• <strong>Check trend:</strong> Verify with moving averages alignment<br>• <strong>Monitor RSI:</strong> Strong RS with low RSI = best opportunities<br>• <strong>Review allocation:</strong> Market leaders can justify higher weights",
                "action": f"• <strong>RS >{self.filter_config.rs_very_strong}:</strong> Very strong - core holdings, maintain or increase allocation<br>• <strong>RS {self.filter_config.rs_strong}-{self.filter_config.rs_very_strong}:</strong> Strong - good holds, trail stops to protect gains<br>• <strong>Rotation strategy:</strong> Rotate from weak RS to strong RS stocks<br>• <strong>New capital:</strong> Prioritize deployment into strongest RS stocks"
            },
            f"Weak RS (RS < {self.filter_config.rs_weak})": {
                "what": f"Stocks with Relative Strength below {self.filter_config.rs_weak}, underperforming the market. Warning signal requiring defensive action or exit.",
                "how": "• <strong>RS column:</strong> Values below market average indicate underperformance<br>• <strong>Check trend:</strong> Confirm if in confirmed downtrend<br>• <strong>Review fundamentals:</strong> Determine cause of weakness<br>• <strong>Assess alternatives:</strong> Compare to Strong RS opportunities",
                "action": f"• <strong>RS <{self.filter_config.rs_very_weak}:</strong> Very weak - strong exit candidates<br>• <strong>RS {self.filter_config.rs_very_weak}-{self.filter_config.rs_weak}:</strong> Weak - reduce allocation, tight stops<br>• <strong>Reallocate capital:</strong> Move funds to Strong RS stocks<br>• <strong>Hold only if:</strong> Clear fundamental catalyst expected soon"
            }
        }
        
        # Add Moving Average filters
        guidance.update({
            "Stocks Below WEMA21": {
                "what": "Stocks trading below their 21-period Wilder's Exponential Moving Average, indicating short-term weakness or pullback phase.",
                "how": "• <strong>Compare CMP vs WEMA21:</strong> Negative divergence shows weakness<br>• <strong>Check other MAs:</strong> If above WEMA30/DSMA50, may be temporary pullback<br>• <strong>Monitor RSI:</strong> RSI <30 may indicate oversold bounce opportunity<br>• <strong>Review volume:</strong> Low volume decline less concerning than high volume",
                "action": "• <strong>Short-term traders:</strong> Avoid longs until price reclaims WEMA21<br>• <strong>Existing positions:</strong> Tighten stops or take partial profits<br>• <strong>Buy opportunities:</strong> If above longer MAs, pullback to WEMA21 = potential entry<br>• <strong>Exit signal:</strong> Break of WEMA30 confirms deeper correction"
            },
            "Stocks Above WEMA21": {
                "what": "Stocks above 21-period Wilder's EMA, showing short-term bullish momentum and near-term trend strength suitable for continuation strategies.",
                "how": "• <strong>CMP > WEMA21:</strong> Bullish short-term signal<br>• <strong>Check slope:</strong> Rising WEMA21 confirms uptrend<br>• <strong>Monitor pullbacks:</strong> Dips toward WEMA21 are buying opportunities<br>• <strong>Confirm with RSI:</strong> RSI 40-70 range indicates healthy momentum",
                "action": "• <strong>Existing positions:</strong> Hold and trail stops below WEMA21<br>• <strong>New entries:</strong> Buy pullbacks to WEMA21 support<br>• <strong>Trend following:</strong> Stay long as price remains above WEMA21<br>• <strong>Exit:</strong> Close below WEMA21 is warning, below WEMA30 is exit signal"
            },
            "Stocks Below WEMA30": {
                "what": "Stocks below 30-period Wilder's EMA, indicating intermediate-term weakness and potential developing downtrend requiring caution.",
                "how": "• <strong>CMP < WEMA30:</strong> Intermediate weakness confirmed<br>• <strong>Check WEMA21:</strong> If both WEMAs broken, trend change likely<br>• <strong>Review Profit/Loss:</strong> Assess if losses are acceptable<br>• <strong>Monitor for bounce:</strong> Oversold RSI + quality stock = watch for reversal",
                "action": "• <strong>Below both WEMAs:</strong> Strong exit or reduce position signal<br>• <strong>Tighten stops:</strong> Use recent swing lows as stop-loss levels<br>• <strong>Reassess thesis:</strong> Determine if weakness is temporary or structural<br>• <strong>Wait for recovery:</strong> Require close above WEMA30 before re-entering"
            },
            "Stocks Above WEMA30": {
                "what": "Stocks above 30-period Wilder's EMA, confirming intermediate-term uptrend and suitable for swing trading strategies with good risk/reward.",
                "how": "• <strong>CMP > WEMA30:</strong> Intermediate uptrend intact<br>• <strong>Best with WEMA21:</strong> Above both WEMAs = strong bullish configuration<br>• <strong>Use as support:</strong> WEMA30 often acts as pullback support level<br>• <strong>Monitor momentum:</strong> Rising WEMA30 slope confirms trend strength",
                "action": "• <strong>Core positions:</strong> Maintain higher allocations in these stocks<br>• <strong>Pullback entries:</strong> Buy dips to WEMA30 support<br>• <strong>Dynamic stops:</strong> Trail stops below WEMA30 to protect gains<br>• <strong>Trend strength:</strong> Can hold through minor WEMA21 violations if WEMA30 holds"
            },
            "Stocks Below DSMA50": {
                "what": "Stocks below 50-day Displaced Moving Average, signaling intermediate-term trend weakness and potential transition to downtrend.",
                "how": "• <strong>CMP < DSMA50:</strong> Losing key support level<br>• <strong>Check DSMA200:</strong> If both broken, significant weakness<br>• <strong>Volume analysis:</strong> High volume break = serious, low volume = possible retest<br>• <strong>RSI context:</strong> Deep oversold may create bounce opportunity",
                "action": "• <strong>Reduce exposure:</strong> Lighten positions or exit if below multiple MAs<br>• <strong>Wait for recovery:</strong> Need sustained move back above DSMA50<br>• <strong>Reassess trend:</strong> May be transitioning from uptrend to downtrend<br>• <strong>Capital preservation:</strong> Better opportunities likely exist elsewhere"
            },
            "Stocks Above DSMA50": {
                "what": "Stocks above 50-day Displaced MA, maintaining intermediate-term uptrend and showing price strength relative to recent history.",
                "how": "• <strong>CMP > DSMA50:</strong> Healthy intermediate trend<br>• <strong>Pullback zones:</strong> DSMA50 often provides support on corrections<br>• <strong>Trend confirmation:</strong> Ideally also above DSMA200 for full trend alignment<br>• <strong>Monitor RSI:</strong> Can hold positions even if RSI dips to 40-50 range",
                "action": "• <strong>Position management:</strong> Hold and add on pullbacks to DSMA50<br>• <strong>Stop placement:</strong> Use DSMA50 as trailing stop reference<br>• <strong>Swing trades:</strong> Good for multi-week holding periods<br>• <strong>Exit criteria:</strong> Decisive close below DSMA50 warrants re-evaluation"
            },
            "Stocks Below DSMA200": {
                "what": "Stocks below 200-day Displaced MA, in long-term downtrend or correction phase. Major warning signal requiring defensive action.",
                "how": "• <strong>CMP < DSMA200:</strong> Long-term trend is bearish<br>• <strong>Check extension:</strong> How far below? Deep oversold may be extreme<br>• <strong>Fundamental review:</strong> Determine if secular decline or cyclical<br>• <strong>Monitor for base:</strong> Bottoming patterns take time to form",
                "action": "• <strong>High priority exits:</strong> Strong sell signal unless deep value or turnaround story<br>• <strong>Avoid new purchases:</strong> Catching falling knife is dangerous<br>• <strong>Require proof:</strong> Need sustained move above DSMA200 for re-entry<br>• <strong>Capital allocation:</strong> Focus on Above DSMA200 stocks instead"
            },
            "Stocks Above DSMA200": {
                "what": "Stocks above 200-day Displaced MA, in confirmed long-term uptrend. Core holding candidates with established bullish bias.",
                "how": "• <strong>CMP > DSMA200:</strong> Long-term trend is bullish<br>• <strong>Major support:</strong> DSMA200 provides key support on corrections<br>• <strong>Check all MAs:</strong> Best when above all moving averages<br>• <strong>Extension risk:</strong> Monitor DMA200_Extension_Pct for overextension",
                "action": "• <strong>Core holdings:</strong> Can maintain larger position sizes<br>• <strong>Buy dips:</strong> Pullbacks to DSMA200 are high-probability entries<br>• <strong>Long-term holds:</strong> Suitable for buy-and-hold strategy<br>• <strong>Trend following:</strong> Stay invested as long as above DSMA200"
            },
            f"RSI Neutral ({self.tech_config.rsi_oversold}-{self.tech_config.rsi_overbought})": {
                "what": f"Stocks with RSI between {self.tech_config.rsi_oversold} and {self.tech_config.rsi_overbought}, showing balanced momentum neither overbought nor oversold. Typically consolidation or ranging markets.",
                "how": "• <strong>RSI range:</strong> Neutral momentum reading<br>• <strong>Trend context:</strong> Check if consolidating in uptrend or downtrend<br>• <strong>Breakout watch:</strong> Neutral RSI often precedes directional move<br>• <strong>Volume analysis:</strong> Low volume = consolidation, rising volume = breakout coming",
                "action": "• <strong>Patience required:</strong> Wait for RSI to break above 60 or below 40<br>• <strong>Range trading:</strong> Can trade between support and resistance<br>• <strong>Breakout preparation:</strong> Set alerts for volume surge or RSI extreme<br>• <strong>Position management:</strong> Maintain current positions but don't aggressively add"
            },
            "RSI Below 50": {
                "what": "Stocks with RSI below 50, showing momentum is below the midpoint. Indicates weakness but not yet oversold conditions.",
                "how": "• <strong>RSI < 50:</strong> Momentum has shifted to bears<br>• <strong>Trend assessment:</strong> Check if temporary pullback or trend change<br>• <strong>Compare to moving averages:</strong> Below MAs + RSI <50 = weakness confirmed<br>• <strong>Monitor for extremes:</strong> If RSI continues to drop below 30, oversold bounce likely",
                "action": "• <strong>Caution advised:</strong> Not strong sell but not buy signal either<br>• <strong>Wait for clarity:</strong> Let RSI reclaim 50+ or drop to oversold<br>• <strong>Tighten stops:</strong> Protect existing positions with trailing stops<br>• <strong>New entries:</strong> Avoid unless clear support levels and bullish catalyst"
            },
            "RSI Above 50": {
                "what": "Stocks with RSI above 50, showing positive momentum above the midpoint. Indicates bullish bias but not yet overbought.",
                "how": "• <strong>RSI > 50:</strong> Momentum favors bulls<br>• <strong>Best with trend:</strong> Above moving averages + RSI >50 = strong setup<br>• <strong>Not yet overbought:</strong> Still room to run before RSI >70 caution zone<br>• <strong>Pullback entries:</strong> Dips to RSI 50-55 are buying opportunities",
                "action": "• <strong>Bullish bias:</strong> Favor long positions in uptrending stocks<br>• <strong>Hold positions:</strong> Let winners run as long as RSI stays above 50<br>• <strong>Add on dips:</strong> Pullbacks to RSI 50-55 are low-risk entries<br>• <strong>Take profits:</strong> Wait for RSI >70 before considering profit-taking"
            },
            f"Oversold (RSI < {self.tech_config.rsi_oversold})": {
                "what": f"Stocks with RSI below {self.tech_config.rsi_oversold}, indicating oversold conditions. Potential bounce candidates but confirm quality before buying weakness.",
                "how": f"• <strong>RSI < {self.tech_config.rsi_oversold}:</strong> Oversold momentum reading<br>• <strong>Quality check:</strong> Good fundamentals increase bounce probability<br>• <strong>Trend context:</strong> Uptrend oversold = opportunity, downtrend oversold = caution<br>• <strong>Volume analysis:</strong> Climax volume on selloff can mark turning point",
                "action": "• <strong>Quality stocks:</strong> Consider scaling into positions<br>• <strong>Wait for turn:</strong> Look for RSI to start rising before entry<br>• <strong>Small positions:</strong> Start with 50% normal size, add if confirms<br>• <strong>Stop loss:</strong> Exit if makes new low after oversold reading"
            },
            f"Overbought (RSI > {self.tech_config.rsi_overbought})": {
                "what": f"Stocks with RSI above {self.tech_config.rsi_overbought}, indicating overbought conditions. Pullback risk elevated, consider profit-taking or tightening stops.",
                "how": f"• <strong>RSI > {self.tech_config.rsi_overbought}:</strong> Overbought momentum<br>• <strong>Check trend:</strong> Strong uptrends can stay overbought for extended periods<br>• <strong>Extension metrics:</strong> Review DMA200_Extension_Pct for additional context<br>• <strong>Volume confirmation:</strong> Rising volume with RSI >70 = caution",
                "action": "• <strong>Take profits:</strong> Partial profit-taking prudent especially if RSI >75<br>• <strong>Trail stops:</strong> Move stops to recent swing lows to protect gains<br>• <strong>Avoid new entries:</strong> Wait for RSI to cool below 60<br>• <strong>Strong trends:</strong> Can hold but be prepared for 5-10% pullback"
            }
        })
        
        # Add 52-week change threshold filters dynamically
        for threshold in self.filter_config.high_change_thresholds:
            guidance[f"52wHCh% > {threshold}%"] = {
                "what": f"Stocks more than {threshold}% above their 52-week high, showing exceptional strength but potential overextension depending on magnitude.",
                "how": f"• <strong>52wHCh% > {threshold}%:</strong> Price extended from recent peak<br>• <strong>Context matters:</strong> Breakout to new highs or pullback from higher level?<br>• <strong>Check RSI:</strong> Extreme RSI >70 increases reversal risk<br>• <strong>Volume analysis:</strong> Confirm breakout with expanding volume",
                "action": f"• <strong>Breakout scenario:</strong> New high + volume = potential continuation<br>• <strong>Pullback scenario:</strong> Already {threshold}% off high = wait for stabilization<br>• <strong>Profit management:</strong> Trail stops if in profit<br>• <strong>New entries:</strong> Wait for pullback and consolidation before buying"
            }
        
        for threshold in self.filter_config.low_change_thresholds:
            guidance[f"52wLCh% < {threshold}%"] = {
                "what": f"Stocks less than {threshold}% above their 52-week low, showing significant weakness. Value opportunity or falling knife depending on fundamentals.",
                "how": f"• <strong>52wLCh% < {threshold}%:</strong> Near recent lows, significant weakness<br>• <strong>Fundamental review:</strong> Determine if justified or oversold<br>• <strong>RSI confirmation:</strong> RSI <20 may indicate capitulation<br>• <strong>Volume analysis:</strong> Selling climax on high volume can mark bottoms",
                "action": f"• <strong>Quality stocks only:</strong> Consider only if fundamentals remain strong<br>• <strong>Wait for turn:</strong> Require RSI upturn or higher low formation<br>• <strong>Small starter positions:</strong> Scale in gradually, don't catch falling knife<br>• <strong>Strict stops:</strong> Exit immediately on new 52-week low"
            }
        
        # Add remaining specific filters
        guidance.update({
            "Near 52-Week High (within 10%)": {
                "what": "Stocks within 10% of 52-week highs, demonstrating relative strength. Can be breakout candidates or due for pullback depending on context.",
                "how": "• <strong>52wHCh% >= -10%:</strong> Strong relative strength position<br>• <strong>Check momentum:</strong> Rising or falling into the highs?<br>• <strong>Volume analysis:</strong> High volume = accumulation, low volume = weak<br>• <strong>Compare RSI:</strong> RSI >70 near highs = caution, RSI 50-70 = healthy",
                "action": "• <strong>Breakout watch:</strong> Monitor for new high on expanding volume<br>• <strong>Existing positions:</strong> Trail stops to lock in gains<br>• <strong>Partial profits:</strong> Consider trimming 25-30% near highs<br>• <strong>New entries:</strong> Wait for breakout and retest or pullback to support"
            },
            "Near 52-Week Low (within 10%)": {
                "what": "Stocks within 10% of 52-week lows, under significant pressure. Potential value plays for contrarians if fundamentals intact, otherwise avoid.",
                "how": "• <strong>52wLCh% <= 10%:</strong> Near recent lows, under pressure<br>• <strong>Fundamental check:</strong> Bad news or just technical weakness?<br>• <strong>RSI levels:</strong> RSI <30 improves odds of bounce<br>• <strong>Support zones:</strong> Look for signs of basing or reversal patterns",
                "action": "• <strong>Contrarian opportunity:</strong> If quality stock with RSI <20, consider small position<br>• <strong>Wait for confirmation:</strong> Need to see higher low or RSI upturn<br>• <strong>Avoid weak fundamentals:</strong> Don't try to catch falling knives<br>• <strong>Set tight stops:</strong> Exit on any new 52-week low"
            },
            f"Very Strong RS (RS > {self.filter_config.rs_very_strong})": {
                "what": f"Stocks with Relative Strength above {self.filter_config.rs_very_strong}, in the top tier of market performers. True market leaders deserving core allocation.",
                "how": f"• <strong>RS > {self.filter_config.rs_very_strong}:</strong> Elite market performance<br>• <strong>Compare across sectors:</strong> Identify leading sectors<br>• <strong>Trend confirmation:</strong> Verify with moving average alignment<br>• <strong>Monitor for exhaustion:</strong> Even leaders need rest - check RSI",
                "action": f"• <strong>Core holdings:</strong> Can allocate 10-15% per position<br>• <strong>Buy dips:</strong> Pullbacks to moving averages are high-probability entries<br>• <strong>Stay invested:</strong> Don't sell leaders prematurely - let winners run<br>• <strong>Rotation risk:</strong> Monitor for RS deterioration as early exit signal"
            },
            f"Very Weak RS (RS < {self.filter_config.rs_very_weak})": {
                "what": f"Stocks with Relative Strength below {self.filter_config.rs_very_weak}, among the weakest market performers. High priority for exits and capital redeployment.",
                "how": f"• <strong>RS < {self.filter_config.rs_very_weak}:</strong> Significant underperformance<br>• <strong>Check sector:</strong> Entire sector weak or just this stock?<br>• <strong>Fundamental review:</strong> Is there path to improvement?<br>• <strong>Opportunity cost:</strong> Compare to Very Strong RS alternatives",
                "action": f"• <strong>Exit priority:</strong> Top candidates for portfolio cleanup<br>• <strong>Reallocate capital:</strong> Move to Very Strong RS stocks<br>• <strong>Hold only if:</strong> Clear near-term catalyst with defined risk<br>• <strong>Stop losses:</strong> Use tight stops - don't let losses expand further"
            }
        })
        
        # Generic guidance for filters not in the dictionary
        default_guidance = {
            "what": f"Stocks that meet the filter criteria: <strong>{filter_name}</strong>. This filtered view helps you focus on specific market conditions or technical setups.",
            "how": "• <strong>Review the table:</strong> Click column headers to sort by any metric<br>• <strong>Compare stocks:</strong> Identify best performers within this filtered set<br>• <strong>Cross-reference:</strong> Check other filters to validate signals<br>• <strong>Monitor changes:</strong> Track how stocks move in/out of this filter over time",
            "action": "• <strong>Verify with multiple indicators:</strong> Don't rely on single filter<br>• <strong>Check allocations:</strong> Ensure diversification across positions<br>• <strong>Set price alerts:</strong> Monitor key stocks for entry/exit signals<br>• <strong>Review regularly:</strong> Market conditions change, reassess filter relevance"
        }
        
        return guidance.get(filter_name, default_guidance)
    
    def generate_filtered_table_html(self, filter_name: str = "All Stocks") -> str:
        """Generate HTML table for filtered dataset"""
        filtered_data = self.apply_filter(filter_name)
        
        if filtered_data.empty:
            return f"""
            <div class="section">
                <h3>&#128202; Filtered Dataset: {filter_name}</h3>
                <p>No stocks match the selected criteria.</p>
            </div>
            """
        
        # Key columns to display
        display_columns = [
            'Symbol', 'CMP', 'Daily_Change_%', 'Stage', 'TT_Score', 'Signal', 'Signal_Confidence', 'Composite_Score', 'Score_Rank',
            'WEMA21', 'WEMA30', 'SMA50', 'SMA150', 'SMA200',
            '52wH', '52wL', '52wHCh%', '52wLCh%', 'DSMA50', 'DSMA200', 'RSI', 'RS',
            'Standard_Deviation', 'Sharpe_Ratio', 'Sortino_Ratio', 'Profit/Loss', 'Percentage_Allocation',
            'Relative_Volume', 'Week_Avg_Volume', 'Month_Avg_Volume', 'Volume_Threshold_2x', 'Week_Threshold_Ratio',
            'DMA200_Extension_Pct',
            '1W%', '1M%', '3M%', '6M%', '1Y%',
            'HH', 'HL', 'Swing_Trend',
            'Stage_Action', 'Signal_Verdict'
        ]
        
        # Filter available columns
        available_columns = [col for col in display_columns if col in filtered_data.columns]
        display_data = filtered_data[available_columns].copy()
        
        # Format numerical columns
        numeric_columns = display_data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in ['Daily_Change_%', '52wHCh%', '52wLCh%', 'Standard_Deviation', 'Percentage_Allocation', 'DMA200_Extension_Pct']:
                display_data[col] = display_data[col].round(2).astype(str) + '%'
            elif col in ['CMP', 'WEMA21', 'WEMA30', '52wH', '52wL', 'DSMA50', 'DSMA200', 'Profit/Loss']:
                display_data[col] = '₹' + display_data[col].round(2).astype(str)
            elif col in ['RS', 'RSI', 'Sharpe_Ratio', 'Sortino_Ratio', 'Relative_Volume', 'Week_Threshold_Ratio']:
                display_data[col] = display_data[col].round(2)
            elif col in ['Composite_Score']:
                display_data[col] = display_data[col].round(1)
            elif col in ['Score_Rank']:
                display_data[col] = display_data[col].fillna(0).astype(int)
            elif col in ['Week_Avg_Volume', 'Month_Avg_Volume', 'Volume_Threshold_2x']:
                # Format volume with comma separators
                display_data[col] = display_data[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
            else:
                display_data[col] = display_data[col].round(2)
        
        # Generate HTML table
        table_html = f"""
        <div class="section">
            <h3>&#128202; Filtered Dataset: {filter_name}</h3>
            <p><strong>Showing {len(filtered_data)} stocks out of {len(self.dataset)} total</strong></p>
            <p class="sort-hint">Click on column headers to sort the table</p>
            
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
        """
        
        # Add column headers with sorting capability
        for col in available_columns:
            table_html += f'<th onclick="sortTable(this)">{col} <span class="sort-arrow">⇅</span></th>'
        table_html += "</tr></thead><tbody>"
        
        # Add data rows
        for _, row in display_data.iterrows():
            table_html += "<tr>"
            for col in available_columns:
                value = row[col]
                # Add conditional formatting
                css_class = ""
                if col == 'Profit/Loss':
                    css_class = "profit" if "₹-" not in str(value) and value != '₹0.0' else "loss"
                elif col == 'Daily_Change_%':
                    if "%" in str(value):
                        val = float(str(value).replace('%', ''))
                        css_class = "positive" if val > 0 else "negative" if val < 0 else ""
                elif col == 'RSI':
                    if float(row[col]) > 70:
                        css_class = "overbought"
                    elif float(row[col]) < 30:
                        css_class = "oversold"
                elif col == 'RS':
                    if float(row[col]) > 0:
                        css_class = "positive"
                    elif float(row[col]) < -0.5:
                        css_class = "negative"
                elif col in ['52wHCh%', '52wLCh%', 'DMA200_Extension_Pct']:
                    if "%" in str(value) and float(str(value).replace('%', '')) > 0:
                        css_class = "positive"
                    else:
                        css_class = "negative"
                elif col == 'Week_Threshold_Ratio':
                    if float(value) > 1.5:
                        css_class = "overbought"  # Significant surge
                    elif float(value) > 1.2:
                        css_class = "positive"  # Strong buildup
                    elif float(value) > 1.0:
                        css_class = ""  # Moderate buildup
                elif col == 'Relative_Volume':
                    if float(value) >= 3.0:
                        css_class = "overbought"  # Extreme spike
                    elif float(value) >= 2.0:
                        css_class = "positive"  # High volume
                elif col == 'Signal':
                    sig = str(value).strip()
                    if sig == 'Buy':
                        css_class = "positive"
                    elif sig == 'Sell':
                        css_class = "negative"
                elif col == 'Composite_Score':
                    try:
                        sc = float(value)
                        if sc >= 65:
                            css_class = "positive"
                        elif sc <= 35:
                            css_class = "negative"
                    except (ValueError, TypeError):
                        pass
                elif col == 'Signal_Verdict':
                    vd = str(value).lower()
                    if 'buy' in vd or 'accumulate' in vd:
                        css_class = "positive"
                    elif 'sell' in vd or 'exit' in vd:
                        css_class = "negative"
                
                table_html += f'<td class="{css_class}">{value}</td>'
            table_html += "</tr>"
        
        table_html += """
                    </tbody>
                </table>
            </div>
        </div>
        """
        
        return table_html
    
    def generate_filtered_cumulative_returns_chart(self, filter_name: str = "All Stocks", 
                                                  historical_data: pd.DataFrame = None) -> str:
        """Generate cumulative portfolio returns chart using equally weighted daily returns"""
        filtered_data = self.apply_filter(filter_name)
        
        if filtered_data.empty or historical_data is None:
            return """
            <div class="chart-container">
                <h4>📈 Cumulative Returns - No Data Available</h4>
                <p>No data available for the selected filter or missing historical data.</p>
            </div>
            """
        
        try:
            # Get symbols from filtered dataset
            filtered_symbols = filtered_data['Symbol'].tolist()
            
            # Prepare historical data with proper date handling
            # System standard: use lowercase 'date' column
            hist_data = historical_data
            
            # Only copy if we need to mutate columns (avoid unnecessary memory use)
            if 'Date' in hist_data.columns and 'date' not in hist_data.columns:
                hist_data = hist_data.rename(columns={'Date': 'date'})
            
            if 'date' in hist_data.columns:
                # Remove NaT values BEFORE setting as index
                # Use assign to avoid mutating the original DataFrame
                hist_data = hist_data.assign(date=pd.to_datetime(hist_data['date'], errors='coerce'))
                hist_data = hist_data[hist_data['date'].notna()]
                
                if hist_data.empty:
                    return """
                    <div class="chart-container">
                        <h4>📈 Cumulative Returns - No Valid Data</h4>
                        <p>No valid date data available for the selected filter.</p>
                    </div>
                    """
                
                hist_data = hist_data.set_index('date')
            
            # Ensure index is DatetimeIndex
            if not isinstance(hist_data.index, pd.DatetimeIndex):
                hist_data.index = pd.to_datetime(hist_data.index, errors='coerce')
                hist_data = hist_data[hist_data.index.notna()]
                
                if hist_data.empty:
                    return """
                    <div class="chart-container">
                        <h4>📈 Cumulative Returns - No Valid Data</h4>
                        <p>No valid date data available for the selected filter.</p>
                    </div>
                    """
            
            # Get last 1 year of data (365 days)
            end_date = hist_data.index.max()
            start_date = end_date - pd.Timedelta(days=365)
            hist_data = hist_data[hist_data.index >= start_date]
            
            # Ensure data is sorted by date
            if not hist_data.empty:
                hist_data.sort_index(inplace=True)
            
            # Calculate daily returns for the stocks in filtered dataset
            portfolio_returns_list = []
            
            # Iterate through the symbols from filtered data
            for symbol in filtered_symbols:
                # Filter historical data for the current stock
                stock_data = hist_data[hist_data['Symbol'] == symbol].copy()
                
                if not stock_data.empty:
                    # Calculate daily return
                    stock_data['Daily_Return'] = stock_data['close'].pct_change(fill_method=None)
                    
                    # Add symbol column (already exists but good for clarity)
                    stock_data['Symbol'] = symbol
                    
                    # Append to the list
                    portfolio_returns_list.append(stock_data[['Daily_Return', 'Symbol']])
            
            if not portfolio_returns_list:
                return """
                <div class="chart-container">
                    <h4>📈 Cumulative Returns - No Historical Data</h4>
                    <p>No historical data available for filtered stocks in the last year.</p>
                </div>
                """
            
            # Concatenate all daily returns into a single DataFrame
            all_daily_returns = pd.concat(portfolio_returns_list)
            
            # Calculate the equally weighted portfolio return
            # Group by date and take the mean of the daily returns for each date
            daily_portfolio_return = all_daily_returns.groupby(all_daily_returns.index)['Daily_Return'].mean().dropna()
            
            # Calculate the cumulative return
            cumulative_portfolio_return = (1 + daily_portfolio_return).cumprod() - 1
            cumulative_portfolio_return_pct = cumulative_portfolio_return * 100
            
            # Create a single Plotly graph for individual stock returns only (no portfolio average)
            fig = go.Figure()
            
            # Add ALL individual stock returns (no portfolio average - user's request)
            colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', 
                     '#17becf', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
            
            # Add individual stock traces for ALL stocks (no smart filtering or average)
            for i, symbol in enumerate(filtered_symbols):
                stock_data = hist_data[hist_data['Symbol'] == symbol].copy()
                if not stock_data.empty:
                    stock_data = stock_data.sort_index()
                    first_price = stock_data['close'].iloc[0]
                    stock_cumulative_return = ((stock_data['close'] / first_price) - 1) * 100
                    
                    fig.add_trace(go.Scatter(
                        x=stock_data.index,
                        y=stock_cumulative_return,
                        mode='lines',
                        name=symbol,
                        line=dict(color=colors[i % len(colors)], width=1.5, dash='dot'),
                        hovertemplate=f'<b>{symbol}</b><br>Date: %{{x}}<br>Return: %{{y:.2f}}%<extra></extra>',
                        showlegend=True,
                        visible='legendonly'  # Start hidden, can be toggled via legend
                    ))
            
            # Add the equal weighted portfolio return line (similar to Portfolio Drag Analysis)
            if len(cumulative_portfolio_return_pct) > 0:
                fig.add_trace(go.Scatter(
                    x=cumulative_portfolio_return_pct.index,
                    y=cumulative_portfolio_return_pct,
                    mode='lines',
                    name='Portfolio Returns',
                    line=dict(color='#1f77b4', width=4),  # Thick blue line for portfolio
                    hovertemplate='<b>Portfolio Returns</b><br>Date: %{x}<br>Return: %{y:.2f}%<extra></extra>',
                    showlegend=True,
                    visible=True,  # Always visible by default
                    legendgroup='portfolio'
                ))
            
            # Update layout with left-side scrollable legend (user's request)
            num_legend_items = len(fig.data)
            
            # Use same layout as Portfolio Drag Analysis chart
            legend_config = dict(
                orientation="v",  # Vertical orientation for many stocks
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(22,27,34,0.9)",
                bordercolor="#30363d",
                borderwidth=1,
                font=dict(size=10, color='#c9d1d9'),
                itemsizing="constant",
                itemwidth=30
            )
            chart_height = 800  # Increased height for better visibility
            chart_width = 1400  # Increased width for large datasets
            
            fig.update_layout(
                title=f'📈 Portfolio & Individual Stock Returns - Click Legend to Show/Hide - {filter_name} ({len(filtered_symbols)} stocks)',
                xaxis_title='Date',
                yaxis_title='Cumulative Return (%)',
                hovermode='closest',
                template='plotly_dark',
                paper_bgcolor='#161b22',
                plot_bgcolor='#0d1117',
                font=dict(color='#c9d1d9'),
                height=chart_height,
                width=chart_width,
                margin=dict(
                    l=60,
                    r=200,
                    t=80,
                    b=80
                ),
                showlegend=True,
                legend=legend_config,
                xaxis=dict(
                    showspikes=True,
                    spikemode='across',
                    spikesnap='cursor',
                    spikethickness=1,
                    spikedash='dot',
                    spikecolor='#8b949e',
                    gridcolor='#21262d',
                    color='#8b949e'
                ),
                yaxis=dict(
                    showspikes=True,
                    spikemode='across',
                    spikesnap='cursor',
                    spikethickness=1,
                    spikedash='dot',
                    spikecolor='#8b949e',
                    gridcolor='#21262d',
                    color='#8b949e'
                )
            )
            
            # Add zero line for reference
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            # Performance Summary
            summary_html = ""
            if len(cumulative_portfolio_return_pct) > 0:
                current_return = cumulative_portfolio_return_pct.iloc[-1]
                max_return = cumulative_portfolio_return_pct.max()
                min_return = cumulative_portfolio_return_pct.min()
                volatility = daily_portfolio_return.std() * 100
                
                summary_html = f"""
                <div class="performance-summary" style="margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h5>📊 Portfolio Performance Summary ({filter_name})</h5>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 15px;">
                        <div style="background: white; padding: 15px; border-radius: 8px; text-align: center;">
                            <h6 style="margin: 0; color: #666;">Current Return</h6>
                            <span style="font-size: 18px; font-weight: bold; color: {'green' if current_return >= 0 else 'red'}">{current_return:.2f}%</span>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 8px; text-align: center;">
                            <h6 style="margin: 0; color: #666;">Max Return</h6>
                            <span style="font-size: 18px; font-weight: bold; color: green">{max_return:.2f}%</span>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 8px; text-align: center;">
                            <h6 style="margin: 0; color: #666;">Min Return</h6>
                            <span style="font-size: 18px; font-weight: bold; color: red">{min_return:.2f}%</span>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 8px; text-align: center;">
                            <h6 style="margin: 0; color: #666;">Volatility</h6>
                            <span style="font-size: 18px; font-weight: bold; color: #666">{volatility:.2f}%</span>
                        </div>
                    </div>
                    <div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px;">
                        <small style="color: #1976d2;">
                            <strong>� Equally Weighted Portfolio:</strong> Returns calculated using daily average returns across all selected stocks. 
                            Individual stocks shown as dotted lines (click legend to show/hide).
                        </small>
                    </div>
                </div>
                """
            
            chart_html = fig.to_html(include_plotlyjs='cdn', div_id=f"cumulative-chart-{filter_name.replace(' ', '-')}")
            
            return f"""
            <div class="chart-container">
                <h4>📈 Cumulative Returns Chart - {filter_name}</h4>
                <p><em>Equally weighted portfolio returns and individual stock performance over the last 12 months</em></p>
                <div style="background: #e8f5e8; padding: 10px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #4caf50;">
                    <small style="color: #2e7d32;">
                        <strong>💡 Legend Display:</strong> 
                        Portfolio Returns (thick blue line) always visible • 
                        {len(filtered_data)} individual stocks (dotted lines) • 
                        Click legend items to show/hide series • Double-click to isolate a single series
                    </small>
                </div>
                {chart_html}
                {summary_html}
            </div>
            """
            
        except Exception as e:
            return f"""
            <div class="chart-container">
                <h4>📈 Cumulative Returns - Error</h4>
                <p>Error generating cumulative returns chart: {str(e)}</p>
            </div>
            """
    
    def generate_comparison_charts(self, filter_name: str = "All Stocks") -> str:
        """Generate comparison charts for filtered dataset"""
        filtered_data = self.apply_filter(filter_name)
        
        if filtered_data.empty:
            return "<p>No data available for comparison charts.</p>"
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Current Price vs WEMA21/WEMA30',
                'RSI Distribution',
                '52-Week Performance',
                'Risk vs Return (Volatility vs Sharpe Ratio)'
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        symbols = filtered_data['Symbol'].tolist()
        
        # Chart 1: Price vs WEMA
        fig.add_trace(
            go.Bar(x=symbols, y=filtered_data['CMP'], name='Current Price', marker_color='blue'),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=symbols, y=filtered_data['WEMA21'], mode='markers+lines', 
                      name='WEMA21', marker_color='orange'),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=symbols, y=filtered_data['WEMA30'], mode='markers+lines',
                      name='WEMA30', marker_color='red'),
            row=1, col=1
        )
        
        # Chart 2: RSI Distribution
        fig.add_trace(
            go.Bar(x=symbols, y=filtered_data['RSI'], name='RSI', marker_color='green'),
            row=1, col=2
        )
        
        # Chart 3: 52-Week Performance
        fig.add_trace(
            go.Bar(x=symbols, y=filtered_data['52wHCh%'], name='52W High %', marker_color='red'),
            row=2, col=1
        )
        fig.add_trace(
            go.Bar(x=symbols, y=filtered_data['52wLCh%'], name='52W Low %', marker_color='green'),
            row=2, col=1
        )
        
        # Chart 4: Risk vs Return
        fig.add_trace(
            go.Scatter(x=filtered_data['Standard_Deviation'], y=filtered_data['Sharpe_Ratio'],
                      mode='markers+text', text=symbols, name='Risk vs Return',
                      marker=dict(size=12, color='purple')),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text=f"📊 Analysis Dashboard: {filter_name}",
            template='plotly_dark',
            paper_bgcolor='#161b22',
            plot_bgcolor='#0d1117',
            font=dict(color='#c9d1d9')
        )
        
        # Add RSI reference lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=1, col=2)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=1, col=2)
        
        # Generate chart HTML (full_html=False to get just the div, not complete HTML document)
        chart_html = fig.to_html(include_plotlyjs='cdn', div_id="comparison-charts", full_html=False)
        
        # Calculate Key Takeaways for comparison analysis
        total_stocks = len(filtered_data)
        
        # Profitable stocks
        pl_col = 'Profit/Loss' if 'Profit/Loss' in filtered_data.columns else 'P&L' if 'P&L' in filtered_data.columns else None
        profitable_count = len(filtered_data[filtered_data[pl_col] > 0]) if pl_col and pl_col in filtered_data.columns else 0
        profitable_pct = (profitable_count / total_stocks * 100) if total_stocks > 0 else 0
        
        # Average P&L percentage
        avg_pl_pct = filtered_data['Profit_Loss_Pct'].mean() if 'Profit_Loss_Pct' in filtered_data.columns else 0
        
        # Average RSI
        rsi_col = 'RSI' if 'RSI' in filtered_data.columns else 'RSI_14' if 'RSI_14' in filtered_data.columns else None
        avg_rsi = filtered_data[rsi_col].mean() if rsi_col and rsi_col in filtered_data.columns else 0
        
        # Average Sharpe Ratio
        avg_sharpe = filtered_data['Sharpe_Ratio'].mean() if 'Sharpe_Ratio' in filtered_data.columns else 0
        
        # Average Sortino Ratio
        avg_sortino = filtered_data['Sortino_Ratio'].mean() if 'Sortino_Ratio' in filtered_data.columns else 0
        
        # Create Key Takeaways HTML
        key_takeaways_html = f"""
        <div style="margin-top: 30px; padding: 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <h4 style="color: white; margin: 0 0 20px 0; font-size: 1.3em; border-bottom: 2px solid rgba(255,255,255,0.3); padding-bottom: 10px;">
                📊 Key Takeaways - Comparison Analysis
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div style="background: rgba(255,255,255,0.95); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">Total Stocks</div>
                    <div style="color: #2c3e50; font-size: 1.8em; font-weight: bold;">{total_stocks}</div>
                </div>
                <div style="background: rgba(255,255,255,0.95); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">Profitable</div>
                    <div style="color: {'#27ae60' if profitable_pct >= 50 else '#e74c3c'}; font-size: 1.8em; font-weight: bold;">{profitable_count} ({profitable_pct:.1f}%)</div>
                </div>
                <div style="background: rgba(255,255,255,0.95); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">Avg P&L%</div>
                    <div style="color: {'#27ae60' if avg_pl_pct >= 0 else '#e74c3c'}; font-size: 1.8em; font-weight: bold;">{avg_pl_pct:+.2f}%</div>
                </div>
                <div style="background: rgba(255,255,255,0.95); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">Avg RSI</div>
                    <div style="color: {'#e74c3c' if avg_rsi > 70 else '#27ae60' if avg_rsi < 30 else '#2c3e50'}; font-size: 1.8em; font-weight: bold;">{avg_rsi:.1f}</div>
                </div>
                <div style="background: rgba(255,255,255,0.95); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">Avg Sharpe</div>
                    <div style="color: {'#27ae60' if avg_sharpe > 1 else '#e67e22' if avg_sharpe > 0 else '#e74c3c'}; font-size: 1.8em; font-weight: bold;">{avg_sharpe:.2f}</div>
                </div>
                <div style="background: rgba(255,255,255,0.95); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">Avg Sortino</div>
                    <div style="color: {'#27ae60' if avg_sortino > 1 else '#e67e22' if avg_sortino > 0 else '#e74c3c'}; font-size: 1.8em; font-weight: bold;">{avg_sortino:.2f}</div>
                </div>
            </div>
            <div style="margin-top: 15px; padding: 12px; background: rgba(255,255,255,0.1); border-radius: 6px; color: white; font-size: 0.9em;">
                <strong>💡 Insight:</strong> 
                {'✅ Strong portfolio with majority profitable stocks' if profitable_pct >= 60 else '⚠️ Review losing positions for exit opportunities' if profitable_pct < 40 else '📊 Balanced mix of winners and losers'}
                {' | 🔥 High momentum (RSI > 70)' if avg_rsi > 70 else ' | ❄️ Oversold conditions (RSI < 30)' if avg_rsi < 30 else ' | ⚖️ Neutral momentum'}
                {' | ⭐ Excellent risk-adjusted returns' if avg_sharpe > 1 and avg_sortino > 1 else ' | ⚠️ Below-market risk-adjusted returns' if avg_sharpe < 0 else ''}
            </div>
        </div>
        """
        
        # --- What's Working / Needs Attention analysis ---
        working_html = self._generate_working_vs_attention(filtered_data)
        
        # --- Per-stock Verdict table (if scoring data present) ---
        verdict_html = self._generate_verdict_table(filtered_data)
        
        return chart_html + key_takeaways_html + working_html + verdict_html
    
    # ------------------------------------------------------------------
    # Helper: "What's Working" / "Needs Attention" analysis
    # ------------------------------------------------------------------
    def _generate_working_vs_attention(self, df: pd.DataFrame) -> str:
        """Generate a two-column 'What's Working / Needs Attention' card."""
        if df.empty:
            return ""
        working = []
        attention = []

        # P&L
        pnl_col = 'Profit/Loss' if 'Profit/Loss' in df.columns else None
        if pnl_col:
            profitable = df[df[pnl_col] > 0]
            losing = df[df[pnl_col] < 0]
            if len(profitable) > len(losing):
                working.append(f"{len(profitable)} stocks in profit — majority of portfolio is green")
            if len(losing) > 0:
                worst = losing.nsmallest(3, pnl_col)
                names = ', '.join(worst['Symbol'].tolist())
                attention.append(f"{len(losing)} stocks in loss — biggest drags: {names}")

        # RS
        if 'RS' in df.columns:
            strong = df[df['RS'] > 0]
            weak = df[df['RS'] < 0]
            if len(strong) > len(weak):
                working.append(f"{len(strong)} stocks outperforming benchmark (RS > 0)")
            if len(weak) > len(df) * 0.4:
                attention.append(f"{len(weak)} stocks underperforming benchmark — review allocation")

        # RSI extremes
        if 'RSI' in df.columns:
            overbought = df[df['RSI'] > 70]
            oversold = df[df['RSI'] < 30]
            if len(overbought) > 0:
                attention.append(f"{len(overbought)} overbought (RSI>70) — consider trimming or protecting profits")
            if len(oversold) > 0:
                working.append(f"{len(oversold)} oversold (RSI<30) — potential rebound candidates")

        # Trend
        if 'WEMA21' in df.columns and 'WEMA30' in df.columns:
            bullish = df[(df['CMP'] > df['WEMA21']) & (df['CMP'] > df['WEMA30'])]
            bearish = df[(df['CMP'] < df['WEMA21']) & (df['CMP'] < df['WEMA30'])]
            if len(bullish) > len(bearish):
                working.append(f"{len(bullish)} stocks in bullish trend (above WEMA21 & WEMA30)")
            if len(bearish) > 0:
                attention.append(f"{len(bearish)} stocks in bearish trend — below both WEMAs")

        # Risk
        if 'Sharpe_Ratio' in df.columns:
            good_sharpe = df[df['Sharpe_Ratio'] > 1]
            neg_sharpe = df[df['Sharpe_Ratio'] < 0]
            if len(good_sharpe) > 0:
                working.append(f"{len(good_sharpe)} stocks with strong risk-adjusted returns (Sharpe > 1)")
            if len(neg_sharpe) > 0:
                attention.append(f"{len(neg_sharpe)} stocks with negative Sharpe — risk outweighs reward")

        def _li(items, fallback):
            if not items:
                return f"<li>{fallback}</li>"
            return ''.join(f'<li>{i}</li>' for i in items)

        return f"""
        <div style="margin-top:20px; display:grid; grid-template-columns:1fr 1fr; gap:15px;">
          <div style="background:#1b5e20; padding:18px; border-radius:10px; color:#e8f5e9;">
            <h4 style="margin:0 0 10px 0; color:#a5d6a7;">✅ What's Working</h4>
            <ul style="margin:0; padding-left:18px; line-height:1.7;">{_li(working, "No strong positives detected in this filter view")}</ul>
          </div>
          <div style="background:#b71c1c; padding:18px; border-radius:10px; color:#ffcdd2;">
            <h4 style="margin:0 0 10px 0; color:#ef9a9a;">⚠️ Needs Attention</h4>
            <ul style="margin:0; padding-left:18px; line-height:1.7;">{_li(attention, "No critical concerns in this filter view")}</ul>
          </div>
        </div>
        """

    # ------------------------------------------------------------------
    # Helper: Per-stock signal / verdict table
    # ------------------------------------------------------------------
    def _generate_verdict_table(self, df: pd.DataFrame) -> str:
        """Generate a compact per-stock verdict table if scoring columns exist."""
        needed = {'Symbol', 'Composite_Score', 'Signal', 'Signal_Confidence', 'Signal_Verdict'}
        if not needed.issubset(set(df.columns)):
            return ""  # scoring not yet applied

        rows = ""
        for _, r in df.sort_values('Composite_Score', ascending=False).iterrows():
            score = r['Composite_Score']
            signal = r['Signal']
            sig_color = {'Strong Buy': '#4CAF50', 'Buy': '#8BC34A', 'Hold': '#FF9800',
                         'Sell': '#FF5722', 'Strong Sell': '#f44336'}.get(signal, '#8b949e')
            rows += f"""<tr>
                <td>{r['Symbol']}</td>
                <td style="font-weight:bold;color:{'#4CAF50' if score>=65 else '#FF9800' if score>=40 else '#f44336'}">{score:.0f}</td>
                <td style="color:{sig_color};font-weight:bold">{signal}</td>
                <td>{r['Signal_Confidence']}</td>
                <td style="font-size:0.85em">{r['Signal_Verdict']}</td>
            </tr>"""

        return f"""
        <div style="margin-top:20px; background:linear-gradient(135deg,#1a1a2e,#16213e); padding:20px; border-radius:12px; border:1px solid #30363d;">
            <h4 style="color:#58a6ff; margin:0 0 12px 0;">🎯 Per-Stock Verdict & Score</h4>
            <p style="color:#8b949e; font-size:0.85em; margin-bottom:12px;">
                Composite Score (0-100) combines Relative Strength, Trend, Momentum, Risk and Value/Volume metrics equally.
                Signal confidence (★) reflects how many indicator categories agree.
            </p>
            <table style="width:100%; border-collapse:collapse; font-size:0.9em;">
            <thead><tr style="background:#21262d;">
                <th style="padding:8px;color:#58a6ff;text-align:left">Symbol</th>
                <th style="padding:8px;color:#58a6ff;text-align:center">Score</th>
                <th style="padding:8px;color:#58a6ff;text-align:center">Signal</th>
                <th style="padding:8px;color:#58a6ff;text-align:center">Confidence</th>
                <th style="padding:8px;color:#58a6ff;text-align:left">Verdict</th>
            </tr></thead>
            <tbody>{rows}</tbody>
            </table>
        </div>
        """

    def save_filtered_report(self, filter_name: str = "All Stocks", 
                           historical_data: pd.DataFrame = None,
                           output_dir: str = "reports") -> str:
        """Generate and save complete filtered report. Returns None if filter yields 0 stocks."""
        # Check if filter produces any results before generating report
        filtered_data = self.apply_filter(filter_name)
        if filtered_data.empty:
            print(f"⏭️  Skipping report for '{filter_name}' — 0 stocks match this filter")
            return None
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = date.today().strftime('%Y%m%d')
        safe_filter_name = self._safe_filename(filter_name)
        filename = f"filtered_report_{safe_filter_name}_{timestamp}.html"
        filepath = os.path.join(output_dir, filename)
        
        # Get filter-specific guidance
        guidance = self._get_filter_specific_guidance(filter_name)
        
        # Generate components
        table_html = self.generate_filtered_table_html(filter_name)
        cumulative_chart = self.generate_filtered_cumulative_returns_chart(filter_name, historical_data)
        comparison_charts = self.generate_comparison_charts(filter_name)
        
        # Create complete HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Filtered Portfolio Report - {filter_name}</title>
            <style>
                {get_base_css()}
            </style>
            <script>
                {get_sortable_table_js()}
            </script>
        </head>
        <body>
            {get_nav_bar(f"Filter: {filter_name}")}
            <div class="container">
                <h1>&#127919; Filtered Portfolio Analysis</h1>
                <h2 style="text-align:center;border-bottom:none;">Filter: {filter_name}</h2>
                <p class="subtitle">Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                
                {get_how_it_works("How This Report Works", [
                    ("What This Shows", guidance['what']),
                    ("How to Use It", guidance['how']),
                    ("Recommended Actions", guidance['action']),
                ])}
                
                <div class="filter-selector">
                    <h3>&#128203; Available Filters:</h3>
                    <ul>
        """
        
        for filter_option in self.get_available_filters():
            # Only link to filters that actually produced data
            if filter_option not in self._nonempty_filters:
                continue
            status = "✅ ACTIVE" if filter_option == filter_name else ""
            safe_name = self._safe_filename(filter_option)
            filter_filename = f"filtered_report_{safe_name}_{timestamp}.html"
            html_content += f'<li><a href="{filter_filename}">{filter_option}</a> {status}</li>'
        
        html_content += f"""
                    </ul>
                </div>
                
                {table_html}
                
                <div class="chart-section">
                    <h3>&#128200; Cumulative Returns Chart</h3>
                    {cumulative_chart}
                </div>
                
                <div class="chart-section">
                    <h3>&#128202; Comparison Analysis</h3>
                    {comparison_charts}
                </div>
                
                <div class="footer">
                    Portfolio Analysis System - Interactive Filtering &bull; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"💾 Filtered report saved: {filepath}")
        return filepath
