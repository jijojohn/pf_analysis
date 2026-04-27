#!/usr/bin/env python3
"""
Technical Indicators Module
Calculates various technical analysis indicators using pandas/numpy
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from config_manager import get_config

class TechnicalIndicators:
    """Technical analysis indicators calculation"""
    
    def __init__(self):
        self.config = get_config()
        self.tech_config = self.config.get_technical_config()
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average (TradingView-compatible: adjust=False)"""
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int = None) -> pd.Series:
        """Relative Strength Index — Wilder's smoothing (RMA), TradingView-compatible"""
        if period is None:
            period = self.tech_config.rsi_period
            
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Wilder's RMA: ewm(alpha=1/period, adjust=False) — matches TradingView's rma()
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = TechnicalIndicators.calculate_ema(data, fast)
        ema_slow = TechnicalIndicators.calculate_ema(data, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Bollinger Bands — TradingView-compatible (population std dev, ddof=0)"""
        sma = TechnicalIndicators.calculate_sma(data, period)
        std = data.rolling(window=period).std(ddof=0)
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> Dict[str, pd.Series]:
        """Stochastic Oscillator — Slow Stochastic, TradingView-compatible (K=14, D=3, Smooth=3)"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        raw_k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        k_percent = raw_k.rolling(window=smooth_k).mean()  # Slow %K = SMA of raw %K
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range — Wilder's smoothing (RMA), TradingView-compatible"""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Wilder's RMA: ewm(alpha=1/period, adjust=False) — matches TradingView default
        atr = true_range.ewm(alpha=1/period, adjust=False).mean()
        
        return atr
    
    @staticmethod
    def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))
        
        return williams_r
    
    @staticmethod
    def calculate_volatility(data: pd.Series, period: int = 30) -> float:
        """Calculate volatility (standard deviation of returns)"""
        returns = data.pct_change(fill_method=None).dropna()
        return returns.rolling(window=period).std().iloc[-1] * np.sqrt(252)  # Annualized

class TechnicalAnalyzer:
    """Main technical analysis class"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.config = get_config()
        self.benchmark_config = self.config.get_benchmark_config()
        self.tech_config = self.config.get_technical_config()
    
    def analyze_stock(self, data: pd.DataFrame, symbol: str) -> Dict:
        """Comprehensive technical analysis for a stock"""
        if data.empty:
            return {}
        
        analysis = {'Symbol': symbol}
        
        try:
            # Basic price metrics
            analysis.update(self._calculate_basic_metrics(data))
            
            # Technical indicators
            analysis.update(self._calculate_technical_indicators(data))
            
            # Risk metrics
            analysis.update(self._calculate_risk_metrics(data))
            
        except Exception as e:
            print(f"⚠️  Error analyzing {symbol}: {e}")
        
        return analysis
    
    def calculate_relative_strength(self, price_data: pd.DataFrame, benchmark_data: pd.DataFrame = None) -> float:
        """Calculate Relative Strength (RS) vs configurable benchmark with dynamic period adjustment"""
        try:
            # Use configured RS calculation period
            rs_period = self.benchmark_config.rs_calculation_period
            smoothing_period = self.benchmark_config.rs_smoothing_period
            
            # Check if benchmark data is available and has sufficient records
            if benchmark_data is None or len(benchmark_data) < 2:
                # Use simple price momentum as RS if no benchmark or insufficient benchmark data
                if len(price_data) < 2:
                    return 0.0
                
                # Adjust smoothing period based on available data
                effective_smoothing = min(smoothing_period, len(price_data) // 2)
                if effective_smoothing < 2:
                    effective_smoothing = 1
                
                return_data = price_data['close'].pct_change(fill_method=None).fillna(0)
                if effective_smoothing > 1:
                    recent_returns = return_data.tail(effective_smoothing).mean()
                else:
                    recent_returns = return_data.iloc[-1]
                return recent_returns * 100
            
            # Dynamically adjust periods based on available data
            # Use the minimum of: configured period, stock data length, benchmark data length
            available_period = min(len(price_data), len(benchmark_data))
            
            # Need at least 5 days for meaningful RS calculation
            if available_period < 5:
                return 0.0
            
            # Adjust rs_period dynamically
            if available_period < rs_period:
                effective_rs_period = max(5, available_period - 1)  # Leave 1 record margin
            else:
                effective_rs_period = rs_period
            
            # Adjust smoothing period dynamically (should be much smaller than calculation period)
            effective_smoothing = min(smoothing_period, effective_rs_period // 3)
            if effective_smoothing < 1:
                effective_smoothing = 1
            
            # Calculate relative strength vs benchmark using smoothed rolling approach
            # Smoothing: compute RS over multiple overlapping sub-windows and average them
            # This reduces noise while keeping the same percentage-point scale
            if effective_smoothing > 1 and effective_rs_period + effective_smoothing <= available_period:
                rs_values = []
                for offset in range(effective_smoothing):
                    end_idx = -(offset + 1) if offset > 0 else -1
                    # Adjust: use .iloc with negative index; for offset=0 use last element
                    stock_end = price_data['close'].iloc[-(offset + 1)] if offset < len(price_data) else None
                    bench_end = benchmark_data['close'].iloc[-(offset + 1)] if offset < len(benchmark_data) else None
                    stock_start = price_data['close'].iloc[-(offset + 1 + effective_rs_period)] if (offset + 1 + effective_rs_period) <= len(price_data) else None
                    bench_start = benchmark_data['close'].iloc[-(offset + 1 + effective_rs_period)] if (offset + 1 + effective_rs_period) <= len(benchmark_data) else None
                    
                    if stock_end is not None and stock_start is not None and bench_end is not None and bench_start is not None:
                        if stock_start > 0 and bench_start > 0:
                            s_ret = (stock_end / stock_start - 1)
                            b_ret = (bench_end / bench_start - 1)
                            rs_values.append((s_ret - b_ret) * 100)
                
                if rs_values:
                    rs = np.mean(rs_values)
                else:
                    # Fallback to single-period calculation
                    stock_return = (price_data['close'].iloc[-1] / price_data['close'].iloc[-effective_rs_period] - 1)
                    benchmark_return = (benchmark_data['close'].iloc[-1] / benchmark_data['close'].iloc[-effective_rs_period] - 1)
                    rs = (stock_return - benchmark_return) * 100
            else:
                # No smoothing: single period RS calculation
                stock_return = (price_data['close'].iloc[-1] / price_data['close'].iloc[-effective_rs_period] - 1)
                benchmark_return = (benchmark_data['close'].iloc[-1] / benchmark_data['close'].iloc[-effective_rs_period] - 1)
                rs = (stock_return - benchmark_return) * 100
            
            return rs
            
        except Exception as e:
            print(f"⚠️  RS calculation error: {e}")
            return 0.0  # Neutral RS
    
    def calculate_obv(self, price_data: pd.DataFrame) -> float:
        """Calculate On Balance Volume (OBV) — vectorised implementation"""
        try:
            if len(price_data) < 2:
                return 0.0

            close = price_data['close'].values
            volume = price_data['volume'].values
            direction = np.sign(np.diff(close))  # +1, 0, -1
            obv = np.concatenate(([0], np.cumsum(direction * volume[1:])))
            return float(obv[-1])
        except:
            return 0.0
    
    def calculate_ad_line(self, price_data: pd.DataFrame) -> float:
        """Calculate Accumulation/Distribution Line (A/D) — vectorised implementation"""
        try:
            if len(price_data) < 1:
                return 0.0

            high = price_data['high'].values
            low = price_data['low'].values
            close = price_data['close'].values
            volume = price_data['volume'].values

            hl_range = high - low
            # Avoid divide-by-zero: replace zeros with 1.0 before dividing,
            # then mask the result to 0 where range was actually zero.
            safe_range = np.where(hl_range != 0, hl_range, 1.0)
            clv = np.where(hl_range != 0,
                           ((close - low) - (high - close)) / safe_range,
                           0.0)
            ad = np.cumsum(clv * volume)
            return float(ad[-1]) if len(ad) > 0 else 0.0
        except:
            return 0.0
    
    def calculate_relative_volume(self, price_data: pd.DataFrame, average_days: int = None) -> float:
        """Calculate Relative Volume (current volume / average volume)
        
        Args:
            price_data: DataFrame with volume column
            average_days: Number of days for average calculation (from config if None)
        
        Returns:
            float: Relative volume ratio (e.g., 3.0 means 3x average volume)
        """
        try:
            if 'volume' not in price_data.columns or len(price_data) < 2:
                return 0.0
            
            # Get configuration if not provided
            if average_days is None:
                volume_config = self.config.get_setting("filter_thresholds.volume_filters", {})
                average_days = volume_config.get("relative_volume_average_days", 20)
            
            # Ensure we have enough data
            if len(price_data) < average_days:
                average_days = len(price_data) - 1
                if average_days < 1:
                    return 0.0
            
            # Current volume (most recent)
            current_volume = price_data['volume'].iloc[-1]
            
            # Average volume over specified period (excluding current day)
            avg_volume = price_data['volume'].iloc[-average_days-1:-1].mean()
            
            # Calculate relative volume
            if avg_volume > 0:
                relative_volume = current_volume / avg_volume
                return relative_volume
            else:
                return 0.0
                
        except Exception as e:
            print(f"⚠️  Error calculating relative volume: {e}")
            return 0.0
    
    def calculate_week_vs_month_volume(self, price_data: pd.DataFrame, 
                                       week_days: int = None, 
                                       month_days: int = None) -> Dict[str, float]:
        """Calculate last 5 days average volume vs 2x monthly average volume
        
        Identifies gradual volume increases by comparing recent 5-day average volume 
        against 2x the monthly (21-day) average volume.
        
        When ratio > 1.0, it indicates recent volume activity is above 2x monthly baseline,
        suggesting accumulation or increasing market interest.
        
        Args:
            price_data: DataFrame with volume column
            week_days: Trading days for recent average (default: 5)
            month_days: Trading days for monthly average (default: 21)
        
        Returns:
            dict: Contains week_avg (last 5 days), month_avg (21 days), threshold (2x month), and ratio
        """
        try:
            if 'volume' not in price_data.columns or len(price_data) < 2:
                return {'week_avg': 0.0, 'month_avg': 0.0, 'threshold': 0.0, 'ratio': 0.0}
            
            # Get configuration if not provided
            if week_days is None or month_days is None:
                volume_config = self.config.get_setting("filter_thresholds.volume_filters", {})
                week_days = volume_config.get("week_volume_days", 5) if week_days is None else week_days
                month_days = volume_config.get("month_volume_days", 21) if month_days is None else month_days
            
            # Need at least week_days of data
            if len(price_data) < week_days:
                return {'week_avg': 0.0, 'month_avg': 0.0, 'threshold': 0.0, 'ratio': 0.0}
            
            # Calculate recent week average volume (last 5 days)
            week_avg_volume = price_data['volume'].tail(week_days).mean()
            
            # Calculate monthly average volume (up to 21 days, or all available data)
            available_month_days = min(month_days, len(price_data))
            month_avg_volume = price_data['volume'].tail(available_month_days).mean()
            
            # Threshold is 2x monthly average
            volume_threshold = 2.0 * month_avg_volume
            
            # Calculate ratio - ratio > 1.0 means recent volume exceeds 2x monthly average
            if volume_threshold > 0:
                volume_ratio = week_avg_volume / volume_threshold
            else:
                volume_ratio = 0.0
            
            return {
                'week_avg': week_avg_volume,
                'month_avg': month_avg_volume,
                'threshold': volume_threshold,
                'ratio': volume_ratio
            }
            
        except Exception as e:
            print(f"⚠️  Error calculating week vs year volume: {e}")
            return {'week_avg': 0.0, 'year_avg': 0.0, 'ratio': 0.0}
    
    def calculate_price_extension_from_dma(self, price_data: pd.DataFrame, dma_period: int = 200) -> float:
        """Calculate how much price is extended from a moving average (as percentage)
        
        Args:
            price_data: DataFrame with close price
            dma_period: Period for the moving average (default 200)
        
        Returns:
            float: Extension percentage (e.g., 70.0 means price is 70% above DMA)
        """
        try:
            if len(price_data) < dma_period:
                # Not enough data for full DMA calculation
                if len(price_data) < 10:
                    return 0.0
                # Use available data
                dma_period = len(price_data)
            
            # Calculate the DMA (could be DSMA with displacement, but using simple SMA for now)
            dma = price_data['close'].rolling(window=dma_period).mean()
            
            # Get current price and DMA value
            current_price = price_data['close'].iloc[-1]
            dma_value = dma.iloc[-1]
            
            # Calculate extension percentage
            if dma_value > 0 and not pd.isna(dma_value):
                extension_pct = ((current_price - dma_value) / dma_value) * 100
                return extension_pct
            else:
                return 0.0
                
        except Exception as e:
            print(f"⚠️  Error calculating price extension from DMA: {e}")
            return 0.0
    
    def _calculate_sortino_ratio(self, price_data: pd.DataFrame, risk_free_rate: float = 0.06) -> float:
        """Calculate Sortino Ratio (risk-adjusted return using only downside deviation)
        
        Args:
            price_data: DataFrame with close price
            risk_free_rate: Annual risk-free rate (default 6%)
        
        Returns:
            float: Sortino ratio
        """
        try:
            if len(price_data) < 30:
                return 0.0
            
            # Calculate daily returns
            returns = price_data['close'].pct_change(fill_method=None).dropna()
            
            if len(returns) == 0:
                return 0.0
            
            # Annualize returns
            avg_return = returns.mean() * 252  # 252 trading days
            
            # Calculate downside deviation (only negative returns)
            negative_returns = returns[returns < 0]
            
            if len(negative_returns) == 0:
                # No negative returns - perfect performance
                return 3.0  # Cap at 3.0 to avoid infinity
            
            downside_std = negative_returns.std() * np.sqrt(252)
            
            if downside_std == 0:
                return 3.0  # Cap at 3.0
            
            # Calculate Sortino ratio
            excess_returns = avg_return - risk_free_rate
            sortino_ratio = excess_returns / downside_std
            
            return sortino_ratio
            
        except Exception as e:
            print(f"⚠️  Error calculating Sortino ratio: {e}")
            return 0.0
    
    def _calculate_period_returns(self, price_data: pd.DataFrame, current_price: float) -> Dict:
        """Calculate returns over 1W, 1M, 3M, 6M, 1Y periods."""
        result = {'1W': 0.0, '1M': 0.0, '3M': 0.0, '6M': 0.0, '1Y': 0.0}
        periods = {'1W': 5, '1M': 21, '3M': 63, '6M': 126, '1Y': 252}
        closes = price_data['close']
        for label, days in periods.items():
            if len(closes) > days:
                past_price = closes.iloc[-(days + 1)]
                if past_price > 0:
                    result[label] = ((current_price - past_price) / past_price) * 100
        return result

    def _detect_hh_hl(self, price_data: pd.DataFrame) -> Dict:
        """Detect Higher High / Higher Low swing pattern using pivot-point detection.
        
        Algorithm (5-bar pivot):
          1. Find swing highs: bars where high is highest within ±5 bars (11-bar window)
          2. Find swing lows: bars where low is lowest within ±5 bars (11-bar window)
          3. Compare last two swing highs → HH if the more recent is higher
          4. Compare last two swing lows → HL if the more recent is higher
          5. Fall back to the most recent 3 months (63 trading days) of data
        
        Swing_Trend:
          - 'Bullish':    HH + HL (healthy uptrend)
          - 'Weakening':  HL only (rising support but no new highs — accumulation)
          - 'Topping':    HH only (new highs but support breaking — distribution)
          - 'Bearish':    neither (lower highs + lower lows — downtrend)
        """
        result = {'HH': False, 'HL': False, 'Swing_Trend': 'Neutral'}
        try:
            PIVOT_BARS = 5          # 5-bar pivot: must be highest/lowest within ±5 bars
            MIN_DATA = PIVOT_BARS * 2 + 1 + 20  # need enough data for at least 2 pivots
            LOOKBACK = 63           # analyse last ~3 months of trading days
            
            if len(price_data) < MIN_DATA:
                return result
            
            data = price_data.iloc[-LOOKBACK:] if len(price_data) > LOOKBACK else price_data
            highs = data['high'].values
            lows = data['low'].values
            n = len(highs)
            
            # --- find pivot highs (swing highs) ---
            swing_highs = []   # list of (index_in_data, value)
            for i in range(PIVOT_BARS, n - PIVOT_BARS):
                window = highs[i - PIVOT_BARS : i + PIVOT_BARS + 1]
                if highs[i] >= window.max():
                    # Accept pivot if this bar is the first occurrence of the max in the window
                    first_max_idx = i - PIVOT_BARS + int(np.argmax(window))
                    if first_max_idx == i:
                        swing_highs.append((i, highs[i]))
            
            # Also consider the most recent bar as a potential partial pivot
            # if it's the highest of the last PIVOT_BARS bars (for recency)
            recent_highs = highs[-PIVOT_BARS:]
            if len(recent_highs) > 0 and highs[-1] >= recent_highs.max():
                # Only add if not already captured and distinct from last swing high
                if not swing_highs or swing_highs[-1][0] < n - PIVOT_BARS:
                    swing_highs.append((n - 1, highs[-1]))
            
            # --- find pivot lows (swing lows) ---
            swing_lows = []    # list of (index_in_data, value)
            for i in range(PIVOT_BARS, n - PIVOT_BARS):
                window = lows[i - PIVOT_BARS : i + PIVOT_BARS + 1]
                if lows[i] <= window.min():
                    # Accept pivot if this bar is the first occurrence of the min in the window
                    first_min_idx = i - PIVOT_BARS + int(np.argmin(window))
                    if first_min_idx == i:
                        swing_lows.append((i, lows[i]))
            
            # Also consider the most recent bar as a potential partial pivot low
            recent_lows = lows[-PIVOT_BARS:]
            if len(recent_lows) > 0 and lows[-1] <= recent_lows.min():
                if not swing_lows or swing_lows[-1][0] < n - PIVOT_BARS:
                    swing_lows.append((n - 1, lows[-1]))
            
            # --- compare last two pivot highs ---
            hh = False
            if len(swing_highs) >= 2:
                hh = swing_highs[-1][1] > swing_highs[-2][1]
            
            # --- compare last two pivot lows ---
            hl = False
            if len(swing_lows) >= 2:
                hl = swing_lows[-1][1] > swing_lows[-2][1]
            
            result['HH'] = hh
            result['HL'] = hl
            
            if hh and hl:
                result['Swing_Trend'] = 'Bullish'
            elif not hh and not hl:
                result['Swing_Trend'] = 'Bearish'
            elif hl and not hh:
                result['Swing_Trend'] = 'Weakening'
            elif hh and not hl:
                result['Swing_Trend'] = 'Topping'
        except Exception:
            pass
        return result

    def generate_comprehensive_dataset(self, portfolio_data: pd.DataFrame, historical_data: pd.DataFrame) -> pd.DataFrame:
        """Generate comprehensive dataset with all requested fields and indicators"""
        print("📊 Generating comprehensive dataset with advanced indicators...")
        
        # Fetch RS benchmark data once for all stocks
        benchmark_data = None
        rs_benchmark_symbol = self.benchmark_config.rs_benchmark_index
        rs_benchmark_name = self.benchmark_config.rs_benchmark_name
        rs_period = self.benchmark_config.rs_calculation_period
        
        print(f"🔍 Fetching RS benchmark data: {rs_benchmark_name} ({rs_benchmark_symbol})")
        print(f"📊 Configured RS period: {rs_period} days (~{rs_period//21} months)")
        try:
            from data_fetcher import get_stock_data_smart
            benchmark_data = get_stock_data_smart(rs_benchmark_symbol, force_update=False)
            if not benchmark_data.empty:
                print(f"✅ RS benchmark data loaded: {len(benchmark_data)} records")
                print(f"   Date range: {benchmark_data.index[0]} to {benchmark_data.index[-1]}")
                if len(benchmark_data) < rs_period:
                    print(f"⚠️  Benchmark has only {len(benchmark_data)} records (need {rs_period})")
                    print(f"   RS calculation will use shorter period: {len(benchmark_data)-1} days")
            else:
                print(f"⚠️  RS benchmark data not available, RS will use simple momentum")
                print(f"💡 Run: python3 update_portfolio_data.py --benchmarks --force")
        except Exception as e:
            print(f"⚠️  Error fetching RS benchmark data: {e}")
            benchmark_data = None
        
        comprehensive_data = []
        
        for _, stock in portfolio_data.iterrows():
            symbol = stock['Symbol']
            
            try:
                # Get price data for the stock from combined DataFrame
                price_data = historical_data[historical_data['Symbol'] == symbol].copy()
                
                if len(price_data) == 0:
                    print(f"   ⚠️ No historical data for {symbol}")
                    continue
                
                # Drop rows where close is NaN (incomplete data from market-open fetches)
                if 'close' in price_data.columns:
                    price_data = price_data.dropna(subset=['close'])
                    if len(price_data) == 0:
                        print(f"   ⚠️ No valid close prices for {symbol} (all NaN)")
                        continue
                
                # Current market data
                current_price = price_data['close'].iloc[-1]
                previous_close = price_data['close'].iloc[-2] if len(price_data) > 1 else current_price
                daily_change_pct = ((current_price - previous_close) / previous_close) * 100 if previous_close > 0 else 0
                
                high_52w = price_data['high'].tail(252).max()  # 252 trading days ≈ 1 year
                low_52w = price_data['low'].tail(252).min()
                
                # Calculate percentage changes from 52w high/low
                high_52w_change = ((current_price - high_52w) / high_52w) * 100
                low_52w_change = ((current_price - low_52w) / low_52w) * 100
                
                # Weekly Exponential Moving Averages (EMA)
                wema_21 = price_data['close'].ewm(span=21, adjust=False).mean().iloc[-1]
                wema_30 = price_data['close'].ewm(span=30, adjust=False).mean().iloc[-1]
                
                # Displaced Simple Moving Averages (DSMA)
                dsma_50 = price_data['close'].rolling(50).mean().shift(10).iloc[-1]  # 10-day displacement
                dsma_200 = price_data['close'].rolling(200).mean().shift(25).iloc[-1]  # 25-day displacement
                
                # Standard (non-displaced) SMAs for Minervini Stage Analysis
                sma_50 = price_data['close'].rolling(50).mean().iloc[-1] if len(price_data) >= 50 else np.nan
                sma_150 = price_data['close'].rolling(150).mean().iloc[-1] if len(price_data) >= 150 else np.nan
                sma_200 = price_data['close'].rolling(200).mean().iloc[-1] if len(price_data) >= 200 else np.nan
                
                # SMA200 slope: % change over last 22 trading days (1 month)
                sma_200_series = price_data['close'].rolling(200).mean()
                if len(price_data) >= 222 and not pd.isna(sma_200_series.iloc[-22]) and sma_200_series.iloc[-22] > 0:
                    sma_200_slope = ((sma_200_series.iloc[-1] - sma_200_series.iloc[-22]) / sma_200_series.iloc[-22]) * 100
                else:
                    sma_200_slope = 0.0
                
                # Portfolio-specific data
                dp_bal = stock.get('DP Bal', 0)
                hold_price = stock.get('Hold Price', current_price)
                # Use Buy Price if available, otherwise use Hold Price
                buy_price = stock.get('Buy Price', hold_price)
                # Updated calculation as requested: DP Balance x (CMP - Buy Price)
                profit_loss = dp_bal * (current_price - buy_price)
                mkt_value = dp_bal * current_price  # DP Balance x CMP
                hold_value = dp_bal * hold_price
                
                # Calculate percentage allocation (assuming total portfolio value)
                total_portfolio_value = portfolio_data['Mkt Value'].sum() if 'Mkt Value' in portfolio_data.columns else 100000
                percentage_allocation = (mkt_value / total_portfolio_value) * 100
                
                # Technical indicators using existing methods
                analysis = self.analyze_stock(price_data, symbol)
                
                rsi = analysis.get('rsi', 50.0)
                standard_deviation = analysis.get('volatility', 0.0) * 100  # Convert to percentage
                sharpe_ratio = analysis.get('sharpe_ratio', 0.0)
                
                # Calculate Sortino Ratio (downside deviation only)
                sortino_ratio = self._calculate_sortino_ratio(price_data)
                
                # Additional indicators
                rs = self.calculate_relative_strength(price_data, benchmark_data)
                obv = self.calculate_obv(price_data)
                ad_line = self.calculate_ad_line(price_data)
                
                # Volume indicators - NEW
                relative_volume = self.calculate_relative_volume(price_data)
                week_vs_month_volume = self.calculate_week_vs_month_volume(price_data)
                dma_200_extension = self.calculate_price_extension_from_dma(price_data, 200)
                
                # Period returns (1W, 1M, 3M, 6M, 1Y)
                period_returns = self._calculate_period_returns(price_data, current_price)
                
                # Higher High / Higher Low swing detection
                hh_hl = self._detect_hh_hl(price_data)
                
                # Create comprehensive record
                stock_data = {
                    'Symbol': symbol,
                    'CMP': round(current_price, 2),
                    'Daily_Change_%': round(daily_change_pct, 2),
                    'WEMA21': round(wema_21, 2) if not pd.isna(wema_21) else current_price,
                    'WEMA30': round(wema_30, 2) if not pd.isna(wema_30) else current_price,
                    '52wH': round(high_52w, 2),
                    '52wL': round(low_52w, 2),
                    '52wHCh%': round(high_52w_change, 2),
                    '52wLCh%': round(low_52w_change, 2),
                    'DSMA50': round(dsma_50, 2) if not pd.isna(dsma_50) else current_price,
                    'DSMA200': round(dsma_200, 2) if not pd.isna(dsma_200) else current_price,
                    'SMA50': round(sma_50, 2) if not pd.isna(sma_50) else current_price,
                    'SMA150': round(sma_150, 2) if not pd.isna(sma_150) else current_price,
                    'SMA200': round(sma_200, 2) if not pd.isna(sma_200) else current_price,
                    'SMA200_Slope': round(sma_200_slope, 4),
                    'DP_Bal': int(dp_bal) if not pd.isna(dp_bal) else 0,
                    'Hold_Price': round(hold_price, 2),
                    'Buy_Price': round(buy_price, 2),
                    'Percentage_Allocation': round(percentage_allocation, 2),
                    'Profit/Loss': round(profit_loss, 2),
                    'Standard_Deviation': round(standard_deviation, 2),
                    'Sharpe_Ratio': round(sharpe_ratio, 2),
                    'Sortino_Ratio': round(sortino_ratio, 2),
                    'RS': round(rs, 2),
                    'RSI': round(rsi, 2),
                    'OBV': int(obv) if not pd.isna(obv) else 0,
                    'AD': int(ad_line) if not pd.isna(ad_line) else 0,
                    # New volume metrics
                    'Relative_Volume': round(relative_volume, 2),
                    'Week_Avg_Volume': int(week_vs_month_volume['week_avg']),
                    'Month_Avg_Volume': int(week_vs_month_volume['month_avg']),
                    'Volume_Threshold_2x': int(week_vs_month_volume['threshold']),
                    'Week_Threshold_Ratio': round(week_vs_month_volume['ratio'], 2),
                    'DMA200_Extension_Pct': round(dma_200_extension, 2),
                    # Period returns
                    '1W%': round(period_returns['1W'], 2),
                    '1M%': round(period_returns['1M'], 2),
                    '3M%': round(period_returns['3M'], 2),
                    '6M%': round(period_returns['6M'], 2),
                    '1Y%': round(period_returns['1Y'], 2),
                    # Higher High / Higher Low swing pattern
                    'HH': hh_hl['HH'],
                    'HL': hh_hl['HL'],
                    'Swing_Trend': hh_hl['Swing_Trend'],
                }
                
                comprehensive_data.append(stock_data)
                print(f"   ✅ Generated comprehensive data for {symbol}")
                    
            except Exception as e:
                print(f"   ❌ Error processing {symbol}: {e}")
                continue
        
        # Convert to DataFrame
        dataset = pd.DataFrame(comprehensive_data)
        
        # Add column aliases for HTML report compatibility
        if not dataset.empty:
            dataset['current_price'] = dataset['CMP']  # Current Market Price
            dataset['rsi'] = dataset['RSI']  # RSI
            dataset['volatility'] = dataset['Standard_Deviation']  # Volatility
            dataset['Allocation_Pct'] = dataset['Percentage_Allocation']  # Allocation percentage
            
            # Calculate Profit/Loss percentage for HTML reports
            # Correct formula: ((CMP - Hold_Price) / Hold_Price) × 100
            if 'CMP' in dataset.columns and 'Hold_Price' in dataset.columns and 'DP_Bal' in dataset.columns:
                # Avoid division by zero
                dataset['Profit_Loss_Pct'] = dataset.apply(
                    lambda row: ((row['CMP'] - row['Hold_Price']) / row['Hold_Price']) * 100 
                    if row['Hold_Price'] > 0 else 0, 
                    axis=1
                )
            else:
                dataset['Profit_Loss_Pct'] = 0
        
        print(f"✅ Comprehensive dataset generated with {len(dataset)} stocks and {len(dataset.columns)} indicators")
        
        return dataset
    
    def _calculate_basic_metrics(self, data: pd.DataFrame) -> Dict:
        """Calculate basic price metrics"""
        metrics = {}
        
        try:
            close_prices = data['close']
            
            # Current price and changes
            metrics['current_price'] = close_prices.iloc[-1]
            metrics['previous_close'] = close_prices.iloc[-2] if len(close_prices) > 1 else close_prices.iloc[-1]
            metrics['price_change'] = metrics['current_price'] - metrics['previous_close']
            metrics['price_change_pct'] = (metrics['price_change'] / metrics['previous_close']) * 100
            
            # 52-week high/low
            metrics['52w_high'] = data['high'].rolling(window=252, min_periods=1).max().iloc[-1]
            metrics['52w_low'] = data['low'].rolling(window=252, min_periods=1).min().iloc[-1]
            metrics['52w_high_pct'] = ((metrics['current_price'] - metrics['52w_high']) / metrics['52w_high']) * 100
            metrics['52w_low_pct'] = ((metrics['current_price'] - metrics['52w_low']) / metrics['52w_low']) * 100
            
            # Volume (if available)
            if 'volume' in data.columns:
                metrics['avg_volume'] = data['volume'].rolling(window=20).mean().iloc[-1]
                metrics['current_volume'] = data['volume'].iloc[-1]
                metrics['volume_ratio'] = metrics['current_volume'] / metrics['avg_volume'] if metrics['avg_volume'] > 0 else 0
            
        except Exception as e:
            print(f"⚠️  Error calculating basic metrics: {e}")
        
        return metrics
    
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate technical indicators"""
        indicators = {}
        
        try:
            close_prices = data['close']
            high_prices = data['high']
            low_prices = data['low']
            
            # Moving averages
            if len(data) >= 20:
                indicators['sma_20'] = self.indicators.calculate_sma(close_prices, 20).iloc[-1]
            if len(data) >= 50:
                indicators['sma_50'] = self.indicators.calculate_sma(close_prices, 50).iloc[-1]
            if len(data) >= 200:
                indicators['sma_200'] = self.indicators.calculate_sma(close_prices, 200).iloc[-1]
            
            # Exponential moving averages
            if len(data) >= 12:
                indicators['ema_12'] = self.indicators.calculate_ema(close_prices, 12).iloc[-1]
            if len(data) >= 26:
                indicators['ema_26'] = self.indicators.calculate_ema(close_prices, 26).iloc[-1]
            if len(data) >= 50:
                indicators['ema_50'] = self.indicators.calculate_ema(close_prices, 50).iloc[-1]
            
            # RSI
            if len(data) >= 14:
                rsi = self.indicators.calculate_rsi(close_prices)
                indicators['rsi'] = rsi.iloc[-1]
            
            # MACD
            if len(data) >= 26:
                macd_data = self.indicators.calculate_macd(close_prices)
                indicators['macd'] = macd_data['macd'].iloc[-1]
                indicators['macd_signal'] = macd_data['signal'].iloc[-1]
                indicators['macd_histogram'] = macd_data['histogram'].iloc[-1]
            
            # Bollinger Bands
            if len(data) >= 20:
                bb_data = self.indicators.calculate_bollinger_bands(close_prices)
                indicators['bb_upper'] = bb_data['upper'].iloc[-1]
                indicators['bb_middle'] = bb_data['middle'].iloc[-1]
                indicators['bb_lower'] = bb_data['lower'].iloc[-1]
                
                # Bollinger Band position
                current_price = close_prices.iloc[-1]
                bb_width = indicators['bb_upper'] - indicators['bb_lower']
                if bb_width > 0:
                    indicators['bb_position'] = (current_price - indicators['bb_lower']) / bb_width
            
            # Stochastic
            if len(data) >= 14:
                stoch_data = self.indicators.calculate_stochastic(high_prices, low_prices, close_prices)
                indicators['stoch_k'] = stoch_data['k'].iloc[-1]
                indicators['stoch_d'] = stoch_data['d'].iloc[-1]
            
            # ATR
            if len(data) >= 14:
                atr = self.indicators.calculate_atr(high_prices, low_prices, close_prices)
                indicators['atr'] = atr.iloc[-1]
            
            # Williams %R
            if len(data) >= 14:
                williams_r = self.indicators.calculate_williams_r(high_prices, low_prices, close_prices)
                indicators['williams_r'] = williams_r.iloc[-1]
                
        except Exception as e:
            print(f"⚠️  Error calculating technical indicators: {e}")
        
        return indicators
    
    def _calculate_risk_metrics(self, data: pd.DataFrame) -> Dict:
        """Calculate risk metrics"""
        risk_metrics = {}
        
        try:
            close_prices = data['close']
            
            # Returns
            returns = close_prices.pct_change(fill_method=None).dropna()
            
            if len(returns) > 1:
                # Volatility (annualized)
                risk_metrics['volatility'] = returns.std() * np.sqrt(252)
                
                # Sharpe ratio (assuming risk-free rate of 6%)
                # NOTE: This is the canonical Sharpe calculation - used throughout system
                risk_free_rate = 0.06
                excess_returns = returns.mean() * 252 - risk_free_rate
                if risk_metrics['volatility'] > 0:
                    risk_metrics['sharpe_ratio'] = excess_returns / risk_metrics['volatility']
                
                # Maximum drawdown
                cumulative_returns = (1 + returns).cumprod()
                rolling_max = cumulative_returns.expanding().max()
                drawdown = (cumulative_returns - rolling_max) / rolling_max
                risk_metrics['max_drawdown'] = drawdown.min()
                
                # Value at Risk (95% confidence)
                risk_metrics['var_95'] = np.percentile(returns, 5)
                
        except Exception as e:
            print(f"⚠️  Error calculating risk metrics: {e}")
        
        return risk_metrics
    
    def get_signal_summary(self, analysis: Dict) -> Dict:
        """Generate trading signals based on technical analysis"""
        signals = {
            'overall': 'NEUTRAL',
            'trend': 'NEUTRAL',
            'momentum': 'NEUTRAL',
            'volatility': 'NORMAL'
        }
        
        try:
            # Trend signals
            current_price = analysis.get('current_price', 0)
            sma_20 = analysis.get('sma_20', 0)
            sma_50 = analysis.get('sma_50', 0)
            
            if current_price > sma_20 > sma_50:
                signals['trend'] = 'BULLISH'
            elif current_price < sma_20 < sma_50:
                signals['trend'] = 'BEARISH'
            
            # Momentum signals
            rsi = analysis.get('rsi', 50)
            if rsi > 70:
                signals['momentum'] = 'OVERBOUGHT'
            elif rsi < 30:
                signals['momentum'] = 'OVERSOLD'
            elif rsi > 50:
                signals['momentum'] = 'BULLISH'
            else:
                signals['momentum'] = 'BEARISH'
            
            # Volatility assessment
            volatility = analysis.get('volatility', 0)
            if volatility > 0.4:  # 40% annualized volatility
                signals['volatility'] = 'HIGH'
            elif volatility < 0.15:  # 15% annualized volatility
                signals['volatility'] = 'LOW'
            
            # Overall signal
            bullish_count = sum([1 for signal in [signals['trend'], signals['momentum']] if 'BULLISH' in signal])
            bearish_count = sum([1 for signal in [signals['trend'], signals['momentum']] if 'BEARISH' in signal])
            
            if bullish_count > bearish_count:
                signals['overall'] = 'BULLISH'
            elif bearish_count > bullish_count:
                signals['overall'] = 'BEARISH'
            
        except Exception as e:
            print(f"⚠️  Error generating signals: {e}")
        
        return signals

if __name__ == "__main__":
    # Test the technical analyzer
    print("🧪 Testing Technical Analyzer...")
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    # Generate sample OHLCV data
    base_price = 100
    returns = np.random.normal(0, 0.02, 100)  # 2% daily volatility
    prices = [base_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    sample_data = pd.DataFrame({
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # Test analysis
    analyzer = TechnicalAnalyzer()
    analysis = analyzer.analyze_stock(sample_data, 'TEST')
    
    print(f"📊 Analysis results for TEST:")
    print(f"   Current Price: ₹{analysis.get('current_price', 0):.2f}")
    print(f"   RSI: {analysis.get('rsi', 0):.2f}")
    print(f"   MACD: {analysis.get('macd', 0):.4f}")
    print(f"   Volatility: {analysis.get('volatility', 0):.2%}")
    
    # Test signals
    signals = analyzer.get_signal_summary(analysis)
    print(f"📈 Trading Signals:")
    print(f"   Overall: {signals['overall']}")
    print(f"   Trend: {signals['trend']}")
    print(f"   Momentum: {signals['momentum']}")
    print(f"   Volatility: {signals['volatility']}")
