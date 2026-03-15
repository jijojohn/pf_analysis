#!/usr/bin/env python3
"""
Portfolio Optimization & Risk Management Report
===============================================
Advanced technical analysis focusing on maximizing returns while minimizing drawdowns.
Includes allocation techniques, rebalancing suggestions, and optimization strategies.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
import plotly.offline as pyo
from datetime import datetime, timedelta
import json
from config_manager import get_config
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

class PortfolioOptimizer:
    """Advanced Portfolio Optimization and Risk Management"""
    
    def __init__(self, comprehensive_dataset: pd.DataFrame, historical_data: pd.DataFrame):
        self.dataset = comprehensive_dataset  # read-only reference, no copy needed
        self.historical_data = historical_data.copy()  # copy needed: date column mutation
        self.config = get_config()
        
        # Prepare historical data with proper date handling
        # System standard: use lowercase 'date' column
        if 'Date' in self.historical_data.columns and 'date' not in self.historical_data.columns:
            self.historical_data.rename(columns={'Date': 'date'}, inplace=True)
        
        if 'date' in self.historical_data.columns:
            self.historical_data['date'] = pd.to_datetime(self.historical_data['date'])
            self.historical_data = self.historical_data.set_index('date')
        
        # Ensure index is datetime type
        if not isinstance(self.historical_data.index, pd.DatetimeIndex):
            self.historical_data.index = pd.to_datetime(self.historical_data.index)
        
        # Get last 1 year of data for analysis
        end_date = self.historical_data.index.max()
        start_date = end_date - pd.Timedelta(days=365)
        self.historical_data = self.historical_data[self.historical_data.index >= start_date]
        self.historical_data.sort_index(inplace=True)
        
        # Calculate returns matrix
        self.returns_matrix = self.calculate_returns_matrix()
        self.correlation_matrix = self.calculate_correlation_matrix()
        
    def calculate_returns_matrix(self) -> pd.DataFrame:
        """Calculate daily returns matrix for all stocks"""
        symbols = self.dataset['Symbol'].tolist()
        returns_data = {}
        
        for symbol in symbols:
            stock_data = self.historical_data[self.historical_data['Symbol'] == symbol].copy()
            if not stock_data.empty:
                stock_data = stock_data.sort_index()
                daily_returns = stock_data['close'].pct_change(fill_method=None).dropna()
                returns_data[symbol] = daily_returns
        
        returns_df = pd.DataFrame(returns_data)
        # Don't fill NaN with 0 - keep them as NaN for proper calculations
        return returns_df
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calculate correlation matrix between stocks"""
        return self.returns_matrix.corr()
    
    def calculate_portfolio_beta(self) -> dict:
        """Calculate portfolio beta (weighted average of individual stock betas)"""
        from data_fetcher import get_stock_data_smart
        
        # Get benchmark data
        benchmark_symbol = self.config.get_setting("benchmark_settings.primary_benchmark", "^NSEI")
        try:
            benchmark_data = get_stock_data_smart(benchmark_symbol, force_update=False)
            if benchmark_data.empty:
                return {'error': 'Benchmark data not available', 'portfolio_beta': float('nan')}
            
            # Calculate benchmark returns
            benchmark_data = benchmark_data.sort_index()
            benchmark_returns = benchmark_data['close'].pct_change(fill_method=None).dropna()
            
            # Get last 1 year of benchmark data
            end_date = benchmark_data.index.max()
            start_date = end_date - pd.Timedelta(days=365)
            benchmark_returns = benchmark_returns[benchmark_returns.index >= start_date]
            
            if len(benchmark_returns) < 20:
                return {'error': 'Insufficient benchmark data', 'portfolio_beta': float('nan')}
            
        except Exception as e:
            return {'error': f'Could not fetch benchmark data: {e}', 'portfolio_beta': float('nan')}
        
        # Calculate beta for each stock
        betas = {}
        total_portfolio_value = self.dataset['Percentage_Allocation'].sum()
        
        for symbol in self.dataset['Symbol']:
            if symbol not in self.returns_matrix.columns:
                continue
            
            stock_returns = self.returns_matrix[symbol]
            
            # Skip if stock returns are all zeros or all NaN
            if stock_returns.isna().all() or (stock_returns == 0).all():
                continue
            
            stock_info = self.dataset[self.dataset['Symbol'] == symbol].iloc[0]
            weight = stock_info['Percentage_Allocation'] / 100.0
            
            # Align returns with benchmark
            aligned_data = pd.DataFrame({
                'stock': stock_returns,
                'benchmark': benchmark_returns
            }).dropna()
            
            # Remove rows where stock return is 0 (from fillna)
            aligned_data = aligned_data[aligned_data['stock'] != 0]
            
            if len(aligned_data) < 20:  # Need at least 20 days of data
                continue
            
            # Calculate beta: Cov(stock, benchmark) / Var(benchmark)
            covariance = aligned_data['stock'].cov(aligned_data['benchmark'])
            benchmark_variance = aligned_data['benchmark'].var()
            
            if benchmark_variance > 0:
                beta = covariance / benchmark_variance
                # Check for NaN/inf in beta or weight - skip if invalid
                if np.isnan(beta) or np.isinf(beta) or np.isnan(weight) or np.isinf(weight):
                    continue
                    
                betas[symbol] = {
                    'beta': round(beta, 3),
                    'weight': round(weight * 100, 2)
                }
        
        if not betas:
            return {'error': 'Could not calculate beta for any stocks', 'portfolio_beta': float('nan')}
        
        # Calculate weighted average portfolio beta
        portfolio_beta = sum(stock['beta'] * stock['weight'] / 100.0 for stock in betas.values())
        
        return {
            'portfolio_beta': round(portfolio_beta, 3),
            'individual_betas': betas,
            'benchmark': benchmark_symbol,
            'interpretation': self._interpret_beta(portfolio_beta)
        }
    
    def _interpret_beta(self, beta: float) -> str:
        """Interpret beta value"""
        if beta < 0.8:
            return "Low Beta - Portfolio is less volatile than market (Defensive)"
        elif beta < 1.2:
            return "Neutral Beta - Portfolio moves in line with market"
        elif beta < 1.5:
            return "High Beta - Portfolio is more volatile than market (Aggressive)"
        else:
            return "Very High Beta - Portfolio is significantly more volatile than market (Very Aggressive)"
    
    def generate_stress_test_scenarios(self) -> dict:
        """Generate stress test scenarios based on portfolio beta"""
        beta_data = self.calculate_portfolio_beta()
        
        if 'error' in beta_data:
            return {'error': beta_data['error']}
        
        portfolio_beta = beta_data['portfolio_beta']
        
        # Define market scenarios
        scenarios = {
            'market_crash_severe': {'name': 'Severe Market Crash', 'market_move': -20},
            'market_crash_moderate': {'name': 'Moderate Market Crash', 'market_move': -10},
            'market_correction': {'name': 'Market Correction', 'market_move': -5},
            'market_rally_moderate': {'name': 'Moderate Market Rally', 'market_move': 5},
            'market_rally_strong': {'name': 'Strong Market Rally', 'market_move': 10},
            'market_bull_run': {'name': 'Bull Run', 'market_move': 20}
        }
        
        results = {}
        for key, scenario in scenarios.items():
            market_move = scenario['market_move']
            expected_portfolio_move = market_move * portfolio_beta
            
            results[key] = {
                'name': scenario['name'],
                'market_move': market_move,
                'expected_portfolio_move': round(expected_portfolio_move, 2),
                'risk_level': self._assess_risk_level(expected_portfolio_move)
            }
        
        return {
            'portfolio_beta': portfolio_beta,
            'benchmark': beta_data['benchmark'],
            'interpretation': beta_data['interpretation'],
            'scenarios': results
        }
    
    def _assess_risk_level(self, expected_move: float) -> str:
        """Assess risk level based on expected portfolio move"""
        if expected_move < -15:
            return "🔴 Critical Risk"
        elif expected_move < -8:
            return "🟠 High Risk"
        elif expected_move < -3:
            return "🟡 Moderate Risk"
        elif expected_move < 0:
            return "🟢 Low Risk"
        else:
            return "🟢 Positive Outlook"
    
    def calculate_risk_metrics(self) -> dict:
        """Calculate comprehensive risk metrics for each stock"""
        risk_metrics = {}
        
        for symbol in self.dataset['Symbol']:
            stock_data = self.historical_data[self.historical_data['Symbol'] == symbol].copy()
            
            if stock_data.empty:
                continue
                
            stock_data = stock_data.sort_index()
            prices = stock_data['close']
            returns = prices.pct_change(fill_method=None).dropna()
            
            # Current stock data from dataset
            stock_info = self.dataset[self.dataset['Symbol'] == symbol].iloc[0]
            
            # Risk calculations
            volatility = returns.std() * np.sqrt(252) * 100  # Annualized volatility
            
            # Drawdown calculations
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max * 100
            max_drawdown = drawdown.min()
            
            # Value at Risk (95% confidence)
            var_95 = np.percentile(returns, 5) * 100
            
            # Sharpe ratio
            # NOTE: This duplicates calculation in technical_indicators.py
            # TODO: Optimization - reuse Sharpe_Ratio from dataset instead of recalculating
            risk_free_rate = 0.06  # 6% risk-free rate
            excess_returns = returns.mean() * 252 - risk_free_rate
            sharpe_ratio = excess_returns / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
            
            # Sortino ratio (uses only downside deviation)
            # NOTE: This duplicates calculation in technical_indicators.py
            # TODO: Optimization - reuse Sortino_Ratio from dataset instead of recalculating
            negative_returns = returns[returns < 0]
            downside_std = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else returns.std() * np.sqrt(252)
            sortino_ratio = excess_returns / downside_std if downside_std > 0 else 0
            
            # Beta calculation (vs portfolio)
            portfolio_returns = self.returns_matrix.mean(axis=1)
            
            # Align the series by their common index
            if len(returns) > 0 and len(portfolio_returns) > 0:
                # Find common dates
                common_index = returns.index.intersection(portfolio_returns.index)
                
                if len(common_index) > 10:  # Need minimum data points
                    aligned_returns = returns.loc[common_index]
                    aligned_portfolio = portfolio_returns.loc[common_index]
                    
                    covariance = np.cov(aligned_returns, aligned_portfolio)[0][1]
                    portfolio_variance = np.var(aligned_portfolio)
                    beta = covariance / portfolio_variance if portfolio_variance > 0 else 1
                else:
                    beta = 1  # Default beta
            else:
                beta = 1  # Default beta
            
            # 52-week metrics (corrected logic)
            current_price = stock_info['CMP']
            high_52w = stock_info['52wH']
            low_52w = stock_info['52wL']
            
            # 52wHCh% = percentage DOWN from 52-week high (negative values)
            from_52w_high = ((current_price - high_52w) / high_52w) * 100
            # 52wLCh% = percentage UP from 52-week low (positive values)
            from_52w_low = ((current_price - low_52w) / low_52w) * 100
            
            # Calculate current return percentage correctly
            # Return % = ((CMP - Hold_Price) / Hold_Price) × 100
            hold_price = stock_info.get('Hold_Price', current_price)
            if hold_price > 0:
                current_return_pct = ((current_price - hold_price) / hold_price) * 100
            else:
                current_return_pct = 0
            
            risk_metrics[symbol] = {
                'volatility': round(volatility, 2),
                'max_drawdown': round(max_drawdown, 2),
                'var_95': round(var_95, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'sortino_ratio': round(sortino_ratio, 2),
                'beta': round(beta, 2),
                'from_52w_high': round(from_52w_high, 2),
                'from_52w_low': round(from_52w_low, 2),
                'current_return': round(current_return_pct, 2),
                'current_allocation': round(stock_info.get('Percentage_Allocation', 0), 2)
            }
        
        return risk_metrics
    
    def optimize_portfolio_weights(self, target_return: float = None) -> dict:
        """Optimize portfolio weights using Modern Portfolio Theory"""
        symbols = list(self.returns_matrix.columns)
        n_assets = len(symbols)
        
        if n_assets == 0:
            return {}
        
        # Calculate expected returns and covariance matrix
        expected_returns = self.returns_matrix.mean() * 252  # Annualized
        cov_matrix = self.returns_matrix.cov() * 252  # Annualized
        
        # Risk-free rate
        risk_free_rate = 0.06
        
        def portfolio_performance(weights):
            portfolio_return = np.sum(expected_returns * weights)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
            return portfolio_return, portfolio_volatility, sharpe_ratio
        
        def negative_sharpe(weights):
            return -portfolio_performance(weights)[2]
        
        # Constraints
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 0.3) for _ in range(n_assets))  # Max 30% in any single stock
        
        # Initial guess (equal weights)
        initial_guess = np.array([1/n_assets] * n_assets)
        
        try:
            # Optimize for maximum Sharpe ratio
            result = minimize(negative_sharpe, initial_guess, method='SLSQP',
                            bounds=bounds, constraints=constraints)
            
            if result.success:
                optimal_weights = result.x
                opt_return, opt_volatility, opt_sharpe = portfolio_performance(optimal_weights)
                
                optimization_results = {
                    'success': True,
                    'optimal_weights': {symbols[i]: round(optimal_weights[i] * 100, 2) 
                                      for i in range(n_assets)},
                    'expected_return': round(opt_return * 100, 2),
                    'volatility': round(opt_volatility * 100, 2),
                    'sharpe_ratio': round(opt_sharpe, 2)
                }
            else:
                optimization_results = {'success': False}
                
        except Exception as e:
            print(f"Optimization error: {e}")
            optimization_results = {'success': False}
        
        return optimization_results
    
    def generate_rebalancing_suggestions(self) -> dict:
        """Generate intelligent rebalancing suggestions"""
        risk_metrics = self.calculate_risk_metrics()
        optimization = self.optimize_portfolio_weights()
        
        suggestions = {
            'reduce_positions': [],  # High risk, low return stocks
            'increase_positions': [],  # Low risk, high return stocks
            'hold_positions': [],    # Well-balanced stocks
            'diversification_opportunities': [],
            'risk_reduction_moves': []
        }
        
        for symbol, metrics in risk_metrics.items():
            current_allocation = metrics['current_allocation']
            optimal_allocation = optimization.get('optimal_weights', {}).get(symbol, 0)
            
            # Risk-adjusted scoring
            risk_score = 0
            if metrics['max_drawdown'] < -20:
                risk_score += 2  # High drawdown penalty
            if metrics['volatility'] > 30:
                risk_score += 2  # High volatility penalty
            if metrics['sharpe_ratio'] < 0:
                risk_score += 3  # Negative Sharpe penalty
            if metrics['from_52w_high'] < -30:
                risk_score += 1  # Deep decline from high
            
            # Return potential scoring
            return_score = 0
            if metrics['current_return'] > 10:
                return_score += 2
            if metrics['sharpe_ratio'] > 1:
                return_score += 2
            if metrics['from_52w_low'] > 50:
                return_score += 1
            
            # Generate suggestions
            if risk_score >= 4:  # High risk
                suggestions['reduce_positions'].append({
                    'symbol': symbol,
                    'current_allocation': current_allocation,
                    'suggested_allocation': max(0, current_allocation * 0.5),
                    'reason': f"High risk (Score: {risk_score}) - Max DD: {metrics['max_drawdown']}%, Vol: {metrics['volatility']}%"
                })
            elif return_score >= 3 and risk_score <= 1:  # High return, low risk
                suggestions['increase_positions'].append({
                    'symbol': symbol,
                    'current_allocation': current_allocation,
                    'suggested_allocation': min(30, current_allocation * 1.5),
                    'reason': f"Strong performance (Score: {return_score}) - Sharpe: {metrics['sharpe_ratio']}, Return: {metrics['current_return']}%"
                })
            else:
                suggestions['hold_positions'].append({
                    'symbol': symbol,
                    'current_allocation': current_allocation,
                    'reason': "Balanced risk-return profile"
                })
        
        # Diversification analysis
        correlation_threshold = 0.7
        high_correlations = []
        
        for i, stock1 in enumerate(self.correlation_matrix.columns):
            for j, stock2 in enumerate(self.correlation_matrix.columns):
                if i < j:  # Avoid duplicates
                    correlation = self.correlation_matrix.loc[stock1, stock2]
                    if abs(correlation) > correlation_threshold:
                        high_correlations.append({
                            'stock1': stock1,
                            'stock2': stock2,
                            'correlation': round(correlation, 2)
                        })
        
        suggestions['diversification_opportunities'] = high_correlations
        
        return suggestions
    
    def generate_allocation_strategies(self) -> dict:
        """Generate different allocation strategy comparisons"""
        risk_metrics = self.calculate_risk_metrics()
        
        strategies = {
            'equal_weight': {},
            'risk_parity': {},
            'momentum_based': {},
            'value_based': {},
            'low_volatility': {}
        }
        
        symbols = list(risk_metrics.keys())
        n_stocks = len(symbols)
        
        if n_stocks == 0:
            return strategies
        
        # Equal Weight Strategy
        equal_allocation = 100 / n_stocks
        strategies['equal_weight'] = {symbol: round(equal_allocation, 2) for symbol in symbols}
        
        # Risk Parity Strategy (inverse volatility weighting)
        volatilities = [risk_metrics[symbol]['volatility'] for symbol in symbols]
        inv_vol_weights = [1/vol if vol > 0 else 0 for vol in volatilities]
        total_inv_vol = sum(inv_vol_weights)
        
        if total_inv_vol > 0:
            strategies['risk_parity'] = {
                symbols[i]: round((inv_vol_weights[i] / total_inv_vol) * 100, 2)
                for i in range(n_stocks)
            }
        
        # Momentum Strategy (based on current returns)
        positive_returns = [(symbol, max(0, risk_metrics[symbol]['current_return'])) 
                           for symbol in symbols]
        total_positive = sum([ret[1] for ret in positive_returns])
        
        if total_positive > 0:
            strategies['momentum_based'] = {
                ret[0]: round((ret[1] / total_positive) * 100, 2)
                for ret in positive_returns
            }
        
        # Value Strategy (based on distance from 52w high)
        value_scores = [(symbol, max(0, -risk_metrics[symbol]['from_52w_high'])) 
                       for symbol in symbols]
        total_value = sum([score[1] for score in value_scores])
        
        if total_value > 0:
            strategies['value_based'] = {
                score[0]: round((score[1] / total_value) * 100, 2)
                for score in value_scores
            }
        
        # Low Volatility Strategy
        max_vol = max(volatilities) if volatilities else 1
        low_vol_scores = [(symbols[i], max_vol - volatilities[i]) for i in range(n_stocks)]
        total_low_vol = sum([score[1] for score in low_vol_scores])
        
        if total_low_vol > 0:
            strategies['low_volatility'] = {
                score[0]: round((score[1] / total_low_vol) * 100, 2)
                for score in low_vol_scores
            }
        
        return strategies
    
    def generate_report(self) -> str:
        """Generate comprehensive portfolio optimization report"""
        print("🔧 Generating Portfolio Optimization Report...")
        
        # Calculate all metrics
        risk_metrics = self.calculate_risk_metrics()
        optimization = self.optimize_portfolio_weights()
        rebalancing = self.generate_rebalancing_suggestions()
        allocation_strategies = self.generate_allocation_strategies()
        
        # NEW: Calculate portfolio beta and stress test
        print("📊 Calculating portfolio beta and stress test scenarios...")
        stress_test = self.generate_stress_test_scenarios()
        
        # Generate report
        report_data = {
            'risk_metrics': risk_metrics,
            'optimization': optimization,
            'rebalancing': rebalancing,
            'allocation_strategies': allocation_strategies,
            'correlation_matrix': self.correlation_matrix.to_dict(),
            'stress_test': stress_test,
            'generation_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        html_content = self.create_html_report(report_data)
        
        # Save report
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"reports/portfolio_optimization_report_{date_str}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Portfolio Optimization Report saved: {filename}")
        return filename
    
    def create_html_report(self, data: dict) -> str:
        """Create comprehensive HTML report"""
        
        # Create visualizations
        charts_html = self.create_optimization_charts(data)
        
        nav = get_nav_bar('Portfolio Optimization')
        how_it_works = get_how_it_works('How This Report Works', [
            ('Risk Analysis Table', 'Sortable table with Return, Volatility, Max Drawdown, Sharpe, Sortino, Beta for each stock'),
            ('MPT Optimization', 'Modern Portfolio Theory optimises allocation to maximise Sharpe ratio (return per unit risk)'),
            ('Correlation Heatmap', 'Green = stocks move together (risk); White = independent (diversification); Red = hedge'),
            ('Stress Test', 'Portfolio Beta shows how your portfolio reacts to market moves; scenarios model various swings'),
            ('Allocation Strategies', 'Equal-weight, Risk-parity, Momentum, Value, Low-volatility alternatives compared'),
            ('Rebalancing', 'Position-specific increase/reduce suggestions based on risk metrics and correlation'),
        ])

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Optimization & Risk Management Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>{get_base_css()}
        .metrics-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:15px; margin:20px 0; }}
        .metric-card {{ background:#161b22; border:1px solid #30363d; padding:16px; border-radius:10px; text-align:center; }}
        .metric-card h3 {{ color:#8b949e; font-size:0.9em; margin-bottom:8px; }}
        .metric-value {{ font-size:1.5em; font-weight:bold; margin:5px 0; }}
        .strategy-comparison {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:15px; margin:20px 0; }}
        .strategy-card {{ background:#161b22; border:1px solid #30363d; border-radius:10px; padding:20px; }}
        .strategy-card h3 {{ text-align:center; background:#21262d; padding:10px; border-radius:6px; color:#58a6ff; margin-bottom:15px; }}
        .allocation-list {{ max-height:200px; overflow-y:auto; }}
        .allocation-item {{ display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #21262d; color:#c9d1d9; }}
        .suggestions-list {{ padding:15px; }}
        .suggestion-item {{ background:#1c2128; margin:10px 0; padding:15px; border-radius:8px; border-left:4px solid #58a6ff; color:#c9d1d9; }}
        .suggestion-reduce {{ border-left-color:#f85149; background:rgba(248,81,73,0.08); }}
        .suggestion-increase {{ border-left-color:#3fb950; background:rgba(63,185,80,0.08); }}
        .collapsible {{ cursor:pointer; padding:10px; width:100%; border:none; text-align:left; outline:none; font-size:1.1em; background:#21262d; color:#58a6ff; border-radius:8px; margin:10px 0; transition:background 0.3s; }}
        .collapsible:hover {{ background:#30363d; }}
        .collapsible::before {{ content:'\\25BC '; font-size:0.8em; margin-right:8px; }}
        .collapsible.active::before {{ content:'\\25B2 '; }}
        .collapsible-content {{ max-height:0; overflow:hidden; transition:max-height 0.3s ease-out; }}
        .collapsible-content.show {{ max-height:2000px; }}
    </style>
    <script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
    <h1>📊 Portfolio Optimization & Risk Management</h1>
    <p class="subtitle">Advanced Technical Analysis &bull; Generated on {data['generation_time']}</p>

{how_it_works}

            <!-- Portfolio Performance Overview -->
            <div class="section">
                <h2>🎯 Current Portfolio Analysis</h2>
                {self.create_portfolio_overview(data)}
            </div>
            
            <!-- Risk Metrics Table -->
            <div class="section">
                <h2>⚠️ Comprehensive Risk Analysis</h2>
                {self.create_risk_metrics_table(data)}
            </div>
            
            <!-- Optimization Results -->
            <div class="section">
                <h2>🔧 Modern Portfolio Theory Optimization</h2>
                {self.create_optimization_section(data)}
            </div>
            
            <!-- Correlation Heatmap -->
            <div class="section">
                <h2>🔗 Portfolio Correlation Analysis</h2>
                <div class="methodology">
                    <strong>Understanding the Heatmap:</strong>
                    Green (&gt;0.7) = stocks move together (risk) | White/Gray (~0) = independent (diversification) | Red (&lt;-0.3) = hedge.
                    Multiple stocks with correlation &gt;0.9 indicates false diversification.
                </div>
                <div id="correlation-heatmap" style="min-height:500px;"></div>
                <script>
                    Plotly.newPlot('correlation-heatmap', {self.create_correlation_heatmap()});
                </script>
            </div>
            
            <!-- Portfolio Beta & Stress Test -->
            <div class="section">
                <h2>⚡ Portfolio Beta & Stress Test Analysis</h2>
                <div class="methodology">
                    <strong>Portfolio Beta:</strong> &lt;1.0 = less volatile than market (defensive) | =1.0 = moves with market | &gt;1.0 = more volatile (aggressive).
                    Use stress test to set position sizes and stop-losses.
                </div>
                {self.create_stress_test_section(data)}
            </div>
            
            <!-- Allocation Strategies -->
            <div class="section">
                <h2>📈 Alternative Allocation Strategies</h2>
                {self.create_allocation_strategies(data)}
            </div>
            
            <!-- Rebalancing Suggestions -->
            <div class="section">
                <h2>⚖️ Intelligent Rebalancing Suggestions</h2>
                {self.create_rebalancing_suggestions(data)}
            </div>
            
            <!-- Charts -->
            <div class="section">
                <h2>📊 Advanced Visualizations</h2>
                {charts_html}
            </div>
        </div>
        
        <div class="footer">
            Portfolio Optimization Report &bull; Generated by Portfolio Analysis System
        </div>
</div>
    
    <script>
        // Collapsible sections functionality
        document.addEventListener('DOMContentLoaded', function() {{
            const collapsibles = document.querySelectorAll('.collapsible');
            collapsibles.forEach(button => {{
                button.addEventListener('click', function() {{
                    this.classList.toggle('active');
                    const content = this.nextElementSibling;
                    if (content.classList.contains('show')) {{
                        content.classList.remove('show');
                    }} else {{
                        content.classList.add('show');
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>
        """
        
        return html_content
    
    def create_portfolio_overview(self, data: dict) -> str:
        """Create portfolio overview section"""
        risk_metrics = data['risk_metrics']
        
        if not risk_metrics:
            return "<p>No portfolio data available for analysis.</p>"
        
        # Calculate portfolio-level metrics with NaN handling
        total_allocation = sum([metrics['current_allocation'] for metrics in risk_metrics.values()])
        returns = [metrics['current_return'] for metrics in risk_metrics.values() if not np.isnan(metrics['current_return'])]
        avg_return = sum(returns) / len(returns) if returns else 0
        avg_volatility = sum([metrics['volatility'] for metrics in risk_metrics.values()]) / len(risk_metrics)
        worst_drawdown = min([metrics['max_drawdown'] for metrics in risk_metrics.values()])
        avg_sharpe = sum([metrics['sharpe_ratio'] for metrics in risk_metrics.values()]) / len(risk_metrics)
        
        # Get data length info
        data_days = len(self.historical_data.index.unique()) if hasattr(self, 'historical_data') else 0
        data_years = round(data_days / 365, 1) if data_days > 0 else 0
        
        return f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Stocks</h3>
                <div class="metric-value neutral">{len(risk_metrics)}</div>
            </div>
            <div class="metric-card">
                <h3>Average Return</h3>
                <div class="metric-value {'positive' if avg_return > 0 else 'negative'}">{avg_return:.2f}%</div>
            </div>
            <div class="metric-card">
                <h3>Average Volatility</h3>
                <div class="metric-value neutral">{avg_volatility:.2f}%</div>
            </div>
            <div class="metric-card">
                <h3>Worst Drawdown</h3>
                <div class="metric-value negative">{worst_drawdown:.2f}%</div>
            </div>
            <div class="metric-card">
                <h3>Average Sharpe Ratio</h3>
                <div class="metric-value {'positive' if avg_sharpe > 0 else 'negative'}">{avg_sharpe:.2f}</div>
            </div>
            <div class="metric-card">
                <h3>Historical Data</h3>
                <div class="metric-value neutral">{data_years} Years ({data_days} days)</div>
            </div>
        </div>
        """
    
    def create_risk_metrics_table(self, data: dict) -> str:
        """Create comprehensive risk metrics table"""
        risk_metrics = data['risk_metrics']
        
        if not risk_metrics:
            return "<p>No risk metrics data available.</p>"
        
        table_rows = ""
        for symbol, metrics in risk_metrics.items():
            volatility_class = 'negative' if metrics['volatility'] > 30 else 'neutral'
            drawdown_class = 'negative' if metrics['max_drawdown'] < -20 else 'neutral'
            sharpe_class = 'positive' if metrics['sharpe_ratio'] > 1 else 'negative' if metrics['sharpe_ratio'] < 0 else 'neutral'
            sortino_class = 'positive' if metrics.get('sortino_ratio', 0) > 1 else 'negative' if metrics.get('sortino_ratio', 0) < 0 else 'neutral'
            return_class = 'positive' if metrics['current_return'] > 0 else 'negative'
            
            table_rows += f"""
            <tr>
                <td><strong>{symbol}</strong></td>
                <td class="{return_class}">{metrics['current_return']}%</td>
                <td class="{volatility_class}">{metrics['volatility']}%</td>
                <td class="{drawdown_class}">{metrics['max_drawdown']}%</td>
                <td class="{sharpe_class}">{metrics['sharpe_ratio']}</td>
                <td class="{sortino_class}">{metrics.get('sortino_ratio', 0)}</td>
                <td class="neutral">{metrics['beta']}</td>
                <td class="negative">{metrics['from_52w_high']}%</td>
                <td class="positive">{metrics['from_52w_low']}%</td>
                <td class="neutral">{metrics['current_allocation']}%</td>
            </tr>
            """
        
        return f"""
        <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th onclick="sortTable(this)">Symbol</th>
                    <th onclick="sortTable(this)">Current Return</th>
                    <th onclick="sortTable(this)">Volatility</th>
                    <th onclick="sortTable(this)">Max Drawdown</th>
                    <th onclick="sortTable(this)">Sharpe Ratio</th>
                    <th onclick="sortTable(this)">Sortino Ratio</th>
                    <th onclick="sortTable(this)">Beta</th>
                    <th onclick="sortTable(this)">From 52W High</th>
                    <th onclick="sortTable(this)">From 52W Low</th>
                    <th onclick="sortTable(this)">Current Allocation</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        </div>
        """
    
    def create_optimization_section(self, data: dict) -> str:
        """Create optimization results section"""
        optimization = data['optimization']
        
        if not optimization.get('success', False):
            return """
            <div class="metric-card">
                <h3>⚠️ Optimization Status</h3>
                <p>Portfolio optimization could not be completed. This may be due to insufficient historical data or numerical constraints.</p>
                <p><strong>Recommendation:</strong> Consider manual rebalancing based on risk metrics and suggestions below.</p>
            </div>
            """
        
        optimal_weights = optimization['optimal_weights']
        top_allocations = sorted(optimal_weights.items(), key=lambda x: x[1], reverse=True)[:10]
        
        allocations_html = ""
        for symbol, weight in top_allocations:
            allocations_html += f"""
            <div class="allocation-item">
                <span><strong>{symbol}</strong></span>
                <span>{weight}%</span>
            </div>
            """
        
        return f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Expected Annual Return</h3>
                <div class="metric-value positive">{optimization['expected_return']}%</div>
            </div>
            <div class="metric-card">
                <h3>Portfolio Volatility</h3>
                <div class="metric-value neutral">{optimization['volatility']}%</div>
            </div>
            <div class="metric-card">
                <h3>Sharpe Ratio</h3>
                <div class="metric-value {'positive' if optimization['sharpe_ratio'] > 1 else 'neutral'}">{optimization['sharpe_ratio']}</div>
            </div>
        </div>
        
        <div class="strategy-card">
            <h3>🎯 Optimal Allocation (Top 10)</h3>
            <div class="allocation-list">
                {allocations_html}
            </div>
        </div>
        """
    
    def create_stress_test_section(self, data: dict) -> str:
        """Create stress test section HTML"""
        stress_data = data.get('stress_test', {})
        
        if 'error' in stress_data:
            return f"<p>⚠️ Could not generate stress test: {stress_data['error']}</p>"
        
        if not stress_data or 'scenarios' not in stress_data:
            return "<p>⚠️ Stress test data not available</p>"
        
        # Portfolio Beta Summary
        beta = stress_data['portfolio_beta']
        interpretation = stress_data['interpretation']
        benchmark = stress_data['benchmark']
        
        # Beta interpretation with color
        if beta < 0.8:
            beta_class = "positive"
            beta_icon = "🛡️"
        elif beta < 1.2:
            beta_class = "neutral"
            beta_icon = "⚖️"
        elif beta < 1.5:
            beta_class = "neutral"
            beta_icon = "📈"
        else:
            beta_class = "negative"
            beta_icon = "⚠️"
        
        html = f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>{beta_icon} Portfolio Beta</h3>
                <div class="metric-value {beta_class}">{beta}</div>
                <small>{interpretation}</small>
            </div>
            <div class="metric-card">
                <h3>📊 Benchmark</h3>
                <div class="metric-value neutral">{benchmark}</div>
                <small>Reference index for beta calculation</small>
            </div>
        </div>
        
        <div id="stress-test-chart" style="min-height:400px;"></div>
        <script>
            Plotly.newPlot('stress-test-chart', {self.create_stress_test_chart(stress_data)});
        </script>
        
        <h3 style="margin-top: 20px;">📋 Detailed Scenario Analysis</h3>
        <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th onclick="sortTable(this)">Scenario</th>
                    <th onclick="sortTable(this)">Market Move</th>
                    <th onclick="sortTable(this)">Expected Portfolio Move</th>
                    <th onclick="sortTable(this)">Risk Assessment</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Add scenario rows
        for scenario_data in stress_data['scenarios'].values():
            market_move = scenario_data['market_move']
            portfolio_move = scenario_data['expected_portfolio_move']
            
            # Color coding
            if portfolio_move < -10:
                row_class = "negative"
            elif portfolio_move < 0:
                row_class = "neutral"
            else:
                row_class = "positive"
            
            html += f"""
                <tr>
                    <td><strong>{scenario_data['name']}</strong></td>
                    <td style="text-align: center;">{market_move:+.1f}%</td>
                    <td class="{row_class}" style="text-align: center; font-weight: bold;">{portfolio_move:+.1f}%</td>
                    <td>{scenario_data['risk_level']}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        </div>
        
        <div class="methodology" style="margin-top: 20px;">
            <strong>💡 Key Takeaway:</strong> 
            Use this stress test to set appropriate position sizes and stop-losses. 
            If your portfolio has high beta (>1.5), consider reducing leverage or adding defensive positions to balance risk.
        </div>
        """
        
        return html
    
    def create_allocation_strategies(self, data: dict) -> str:
        """Create allocation strategies comparison"""
        strategies = data['allocation_strategies']
        
        strategy_names = {
            'equal_weight': '⚖️ Equal Weight',
            'risk_parity': '🛡️ Risk Parity',
            'momentum_based': '🚀 Momentum Based',
            'value_based': '💎 Value Based',
            'low_volatility': '🔒 Low Volatility'
        }
        
        strategies_html = ""
        for strategy_key, strategy_data in strategies.items():
            if strategy_data:
                strategy_name = strategy_names.get(strategy_key, strategy_key)
                top_allocations = sorted(strategy_data.items(), key=lambda x: x[1], reverse=True)[:8]
                
                allocations_html = ""
                for symbol, weight in top_allocations:
                    allocations_html += f"""
                    <div class="allocation-item">
                        <span>{symbol}</span>
                        <span>{weight}%</span>
                    </div>
                    """
                
                strategies_html += f"""
                <div class="strategy-card">
                    <h3>{strategy_name}</h3>
                    <div class="allocation-list">
                        {allocations_html}
                    </div>
                </div>
                """
        
        return f'<div class="strategy-comparison">{strategies_html}</div>'
    
    def create_rebalancing_suggestions(self, data: dict) -> str:
        """Create rebalancing suggestions section"""
        rebalancing = data.get('rebalancing', {})
        
        suggestions_html = ""
        
        # Reduce positions
        if rebalancing.get('reduce_positions', []):
            suggestions_html += """<button class="collapsible">🔻 Positions to Reduce</button>
            <div class="collapsible-content"><div class='suggestions-list'>"""
            for suggestion in rebalancing['reduce_positions']:
                suggestions_html += f"""
                <div class="suggestion-item suggestion-reduce">
                    <strong>{suggestion['symbol']}</strong><br>
                    Current: {suggestion['current_allocation']}% → Suggested: {suggestion['suggested_allocation']}%<br>
                    <small>{suggestion['reason']}</small>
                </div>
                """
            suggestions_html += "</div></div>"
        
        # Increase positions
        if rebalancing.get('increase_positions', []):
            suggestions_html += """<button class="collapsible">🔺 Positions to Increase</button>
            <div class="collapsible-content"><div class='suggestions-list'>"""
            for suggestion in rebalancing['increase_positions']:
                suggestions_html += f"""
                <div class="suggestion-item suggestion-increase">
                    <strong>{suggestion['symbol']}</strong><br>
                    Current: {suggestion['current_allocation']}% → Suggested: {suggestion['suggested_allocation']}%<br>
                    <small>{suggestion['reason']}</small>
                </div>
                """
            suggestions_html += "</div></div>"
        
        # Diversification opportunities
        if rebalancing.get('diversification_opportunities', []):
            suggestions_html += """<button class="collapsible">🎯 Diversification Alerts</button>
            <div class="collapsible-content"><div class='suggestions-list'>"""
            for corr in rebalancing['diversification_opportunities']:
                suggestions_html += f"""
                <div class="suggestion-item">
                    <strong>High Correlation Alert:</strong> {corr['stock1']} & {corr['stock2']}<br>
                    Correlation: {corr['correlation']}<br>
                    <small>Consider reducing exposure to one of these highly correlated positions</small>
                </div>
                """
            suggestions_html += "</div></div>"
        
        return suggestions_html if suggestions_html else "<p>No specific rebalancing suggestions at this time.</p>"
    
    def create_correlation_heatmap(self) -> str:
        """Create correlation heatmap visualization"""
        corr_matrix = self.correlation_matrix.copy()
        
        if corr_matrix.empty:
            return "<p>No correlation data available.</p>"
        
        # Handle large portfolios - limit to top holdings for better visualization
        num_stocks = len(corr_matrix)
        title_suffix = ""
        
        if num_stocks > 50:
            # Show top 50 stocks (just use first 50 from the correlation matrix)
            # Since correlation_matrix is already computed, we can't easily filter by allocation here
            # So we'll just take first 50 stocks
            top_stocks = corr_matrix.columns[:50].tolist()
            corr_matrix = corr_matrix.loc[top_stocks, top_stocks]
            num_stocks = len(corr_matrix)
            title_suffix = f" (Showing {num_stocks} of {len(self.correlation_matrix)} Holdings)"
        
        # Calculate appropriate size with a hard cap at 1200px
        # This ensures the heatmap fits on standard screens
        size = min(600 + (num_stocks * 10), 1200)
        
        # Adjust text visibility based on portfolio size
        show_text = num_stocks <= 30
        font_size = max(6, min(10, 280 // num_stocks))
        
        # Convert numpy arrays to lists to avoid binary encoding in JSON
        z_values = corr_matrix.values.tolist()
        x_labels = corr_matrix.columns.tolist()
        y_labels = corr_matrix.index.tolist()
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            colorscale=[
                [0, '#d32f2f'],      # Strong negative correlation (red)
                [0.25, '#ff9800'],   # Weak negative correlation (orange)
                [0.5, '#fafafa'],    # No correlation (white/gray)
                [0.75, '#81c784'],   # Weak positive correlation (light green)
                [1, '#2e7d32']       # Strong positive correlation (dark green)
            ],
            zmid=0,
            zmin=-1,
            zmax=1,
            colorbar=dict(
                title="Correlation",
                tickvals=[-1, -0.5, 0, 0.5, 1],
                ticktext=['-1.0<br>Perfect<br>Negative', '-0.5<br>Weak<br>Negative', 
                         '0<br>No<br>Correlation', '0.5<br>Weak<br>Positive', 
                         '1.0<br>Perfect<br>Positive']
            ),
            text=z_values if show_text else None,
            texttemplate='%{text:.2f}' if show_text else None,
            textfont={"size": font_size} if show_text else None,
            hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"📊 Portfolio Correlation Heatmap - Diversification Analysis{title_suffix}",
            xaxis_title="",
            yaxis_title="",
            height=size,
            width=size,
            xaxis={'side': 'bottom'},
            yaxis={'side': 'left'},
            paper_bgcolor='#161b22',
            plot_bgcolor='#0d1117',
            font=dict(color='#c9d1d9')
        )
        
        # Convert to dict and then JSON to avoid binary encoding issues
        # This ensures browser compatibility and proper rendering
        fig_dict = fig.to_dict()
        return json.dumps(fig_dict)
    
    def create_stress_test_chart(self, stress_data: dict) -> str:
        """Create stress test visualization"""
        if 'error' in stress_data or 'scenarios' not in stress_data:
            return ""
        
        scenarios = stress_data['scenarios']
        scenario_names = [s['name'] for s in scenarios.values()]
        market_moves = [s['market_move'] for s in scenarios.values()]
        portfolio_moves = [s['expected_portfolio_move'] for s in scenarios.values()]
        
        fig = go.Figure()
        
        # Market benchmark line
        fig.add_trace(go.Scatter(
            x=scenario_names,
            y=market_moves,
            mode='lines+markers',
            name=f'{stress_data["benchmark"]} (Market)',
            line=dict(color='#2196F3', width=3, dash='dash'),
            marker=dict(size=10, symbol='diamond')
        ))
        
        # Portfolio line
        fig.add_trace(go.Scatter(
            x=scenario_names,
            y=portfolio_moves,
            mode='lines+markers',
            name='Your Portfolio',
            line=dict(color='#FF5722', width=3),
            marker=dict(size=12, symbol='circle'),
            fill='tonexty',
            fillcolor='rgba(255, 87, 34, 0.1)'
        ))
        
        fig.update_layout(
            title=f"🎯 Portfolio Stress Test (Portfolio Beta: {stress_data['portfolio_beta']})",
            xaxis_title="Market Scenario",
            yaxis_title="Expected Change (%)",
            height=500,
            hovermode='closest',
            paper_bgcolor='#161b22',
            plot_bgcolor='#0d1117',
            font=dict(color='#c9d1d9'),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(22,27,34,0.8)",
                font=dict(color='#c9d1d9')
            ),
            xaxis=dict(
                gridcolor='#21262d',
                showspikes=True,
                spikemode='across',
                spikesnap='cursor',
                spikethickness=1,
                spikedash='dot',
                spikecolor='#8b949e'
            ),
            yaxis=dict(
                gridcolor='#21262d',
                showspikes=True,
                spikemode='across',
                spikesnap='cursor',
                spikethickness=1,
                spikedash='dot',
                spikecolor='#8b949e'
            ),
            shapes=[
                dict(
                    type='line',
                    xref='paper',
                    x0=0,
                    x1=1,
                    y0=0,
                    y1=0,
                    line=dict(color='gray', width=1, dash='dot')
                )
            ]
        )
        
        return fig.to_json()
    
    def create_optimization_charts(self, data: dict) -> str:
        """Create optimization visualization charts"""
        charts_html = ""
        
        # Risk-Return Scatter Plot
        risk_metrics = data['risk_metrics']
        if risk_metrics:
            symbols = list(risk_metrics.keys())
            returns = [risk_metrics[s]['current_return'] for s in symbols]
            volatilities = [risk_metrics[s]['volatility'] for s in symbols]
            allocations = [risk_metrics[s]['current_allocation'] for s in symbols]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=volatilities,
                y=returns,
                mode='markers+text',
                text=symbols,
                textposition="top center",
                marker=dict(
                    size=[max(10, alloc) for alloc in allocations],
                    color=returns,
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="Current Return %"),
                    line=dict(width=1, color='black')
                ),
                name="Stocks",
                hovertemplate="<b>%{text}</b><br>" +
                            "Volatility: %{x:.1f}%<br>" +
                            "Return: %{y:.1f}%<br>" +
                            "Allocation: %{marker.size:.1f}%<extra></extra>"
            ))
            
            fig.update_layout(
                title="Risk-Return Analysis (Bubble Size = Current Allocation)",
                xaxis_title="Volatility (%)",
                yaxis_title="Current Return (%)",
                height=500,
                showlegend=False,
                paper_bgcolor='#161b22',
                plot_bgcolor='#0d1117',
                font=dict(color='#c9d1d9'),
                xaxis=dict(gridcolor='#21262d'),
                yaxis=dict(gridcolor='#21262d')
            )
            
            charts_html += f"""
            <div id="risk-return-chart" style="min-height:500px;"></div>
            <script>
                Plotly.newPlot('risk-return-chart', {fig.to_json()});
            </script>
            """
            
            # Sortino Ratio Bar Chart
            sortino_ratios = [risk_metrics[s].get('sortino_ratio', 0) for s in symbols]
            
            # Sort by sortino ratio
            sorted_data = sorted(zip(symbols, sortino_ratios), key=lambda x: x[1], reverse=True)
            sorted_symbols, sorted_sortino = zip(*sorted_data) if sorted_data else ([], [])
            
            colors = ['#4CAF50' if s > 1 else '#f44336' if s < 0 else '#FFA726' for s in sorted_sortino]
            
            fig_sortino = go.Figure(data=[go.Bar(
                x=list(sorted_symbols),
                y=list(sorted_sortino),
                marker_color=colors,
                text=[f"{s:.2f}" for s in sorted_sortino],
                textposition='outside',
                hovertemplate="<b>%{x}</b><br>Sortino Ratio: %{y:.2f}<extra></extra>"
            )])
            
            fig_sortino.update_layout(
                title="Sortino Ratio by Stock (Higher = Better Risk-Adjusted Returns)",
                xaxis_title="Stock Symbol",
                yaxis_title="Sortino Ratio",
                height=400,
                showlegend=False,
                xaxis={'tickangle': -45, 'gridcolor': '#21262d'},
                yaxis={'gridcolor': '#21262d'},
                paper_bgcolor='#161b22',
                plot_bgcolor='#0d1117',
                font=dict(color='#c9d1d9')
            )
            
            # Add reference lines
            fig_sortino.add_hline(y=1.0, line_dash="dash", line_color="gray", 
                                 annotation_text="Good (>1.0)", annotation_position="right")
            fig_sortino.add_hline(y=0, line_dash="dot", line_color="red", 
                                 annotation_text="Negative", annotation_position="right")
            
            charts_html += f"""
            <div id="sortino-chart" style="min-height:400px;"></div>
            <script>
                Plotly.newPlot('sortino-chart', {fig_sortino.to_json()});
            </script>
            """
        
        return charts_html


if __name__ == "__main__":
    print("Portfolio Optimizer module loaded successfully!")
