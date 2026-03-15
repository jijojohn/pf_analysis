#!/usr/bin/env python3
"""
Portfolio Drag Analyzer - Interactive Stock Impact Analysis
===========================================================
Creates an interactive report to identify which stocks are dragging down portfolio returns.
User can deselect stocks via legend and see real-time portfolio recalculation.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import plotly.offline as pyo
from datetime import datetime
import json
from config_manager import get_config
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works

class PortfolioDragAnalyzer:
    """Analyze which stocks are dragging down portfolio performance through interactive deselection"""
    
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
        elif hasattr(self.historical_data, 'index') and isinstance(self.historical_data.index, pd.RangeIndex):
            # If no date column and index is range, we have a problem - cannot proceed
            raise ValueError("Historical data must have a 'date' column or DatetimeIndex")
        
        # Ensure index is datetime type  
        if not isinstance(self.historical_data.index, pd.DatetimeIndex):
            try:
                self.historical_data.index = pd.to_datetime(self.historical_data.index)
            except:
                # If conversion fails, the index might already be datetime but not recognized
                pass
        
        # Get last 1 year of data
        end_date = self.historical_data.index.max()
        start_date = end_date - pd.Timedelta(days=365)
        self.historical_data = self.historical_data[self.historical_data.index >= start_date]
        self.historical_data.sort_index(inplace=True)
    
    def calculate_stock_performance_impact(self) -> dict:
        """Calculate individual stock performance and impact on portfolio"""
        symbols = self.dataset['Symbol'].tolist()
        stock_impacts = {}
        
        # Calculate portfolio with all stocks
        all_portfolio_return = self.calculate_portfolio_returns(symbols)
        
        # Calculate portfolio without each stock to see impact
        for symbol in symbols:
            remaining_symbols = [s for s in symbols if s != symbol]
            if len(remaining_symbols) > 0:
                without_stock_return = self.calculate_portfolio_returns(remaining_symbols)
                
                # Calculate impact (positive means stock was dragging down)
                if all_portfolio_return['current_return'] is not None and without_stock_return['current_return'] is not None:
                    impact = without_stock_return['current_return'] - all_portfolio_return['current_return']
                else:
                    impact = 0
                
                # Calculate drawdown metrics for individual stock
                drawdown_metrics = self.calculate_stock_drawdown(symbol)
                
                # Get stock return percentage from dataset (using corrected Profit_Loss_Pct)
                stock_info = self.dataset[self.dataset['Symbol'] == symbol]
                if not stock_info.empty:
                    stock_return_pct = stock_info.iloc[0].get('Profit_Loss_Pct', 0)
                else:
                    stock_return_pct = self.get_individual_stock_return(symbol)
                
                stock_impacts[symbol] = {
                    'impact': round(impact, 2),
                    'is_dragger': bool(impact > 0.1),  # Convert to JSON-serializable bool
                    'individual_return': round(stock_return_pct, 2),
                    'max_drawdown': drawdown_metrics['max_drawdown'],
                    'current_drawdown': drawdown_metrics['current_drawdown'],
                    'from_52w_high': drawdown_metrics['from_52w_high'],
                    'from_52w_low': drawdown_metrics['from_52w_low'],
                    'drawdown_duration': drawdown_metrics['drawdown_duration']
                }
        
        return stock_impacts
    
    def calculate_stock_drawdown(self, symbol: str) -> dict:
        """Calculate comprehensive drawdown metrics for individual stock"""
        stock_data = self.historical_data[self.historical_data['Symbol'] == symbol].copy()
        
        if stock_data.empty:
            return {
                'max_drawdown': 0,
                'current_drawdown': 0,
                'from_52w_high': 0,
                'from_52w_low': 0,
                'drawdown_duration': 0
            }
        
        stock_data = stock_data.sort_index()
        prices = stock_data['close']
        
        # Calculate rolling maximum (peak prices)
        rolling_max = prices.expanding().max()
        
        # Calculate drawdown from peaks
        drawdown = (prices - rolling_max) / rolling_max * 100
        max_drawdown = round(drawdown.min(), 2)
        current_drawdown = round(drawdown.iloc[-1], 2)
        
        # Calculate 52-week high/low percentages (matching existing logic)
        if len(prices) >= 252:  # At least 1 year of data
            high_52w = prices.tail(252).max()
            low_52w = prices.tail(252).min()
        else:
            high_52w = prices.max()
            low_52w = prices.min()
        
        current_price = prices.iloc[-1]
        from_52w_high = round(((current_price - high_52w) / high_52w) * 100, 2)  # 52wHCh% logic
        from_52w_low = round(((current_price - low_52w) / low_52w) * 100, 2)    # 52wLCh% logic
        
        # Calculate drawdown duration (days since last peak)
        drawdown_duration = 0
        if current_drawdown < -0.1:  # If currently in drawdown
            last_peak_idx = rolling_max[rolling_max == rolling_max.iloc[-1]].index[-1]
            current_idx = prices.index[-1]
            drawdown_duration = (current_idx - last_peak_idx).days
        
        return {
            'max_drawdown': max_drawdown,
            'current_drawdown': current_drawdown,
            'from_52w_high': from_52w_high,
            'from_52w_low': from_52w_low,
            'drawdown_duration': drawdown_duration
        }

    def get_individual_stock_return(self, symbol: str) -> float:
        """Get individual stock's cumulative return"""
        stock_data = self.historical_data[self.historical_data['Symbol'] == symbol].copy()
        
        if stock_data.empty:
            return 0
        
        stock_data = stock_data.sort_index()
        daily_returns = stock_data['close'].pct_change(fill_method=None).dropna()
        
        if len(daily_returns) == 0:
            return 0
            
        cumulative_return = (1 + daily_returns).cumprod().iloc[-1] - 1
        return round(cumulative_return * 100, 2)
    
    def calculate_portfolio_returns(self, selected_symbols: list) -> dict:
        """Calculate equally weighted portfolio returns for selected symbols"""
        if not selected_symbols:
            return {
                'portfolio_dates': [],
                'portfolio_returns': [],
                'current_return': None,
                'max_return': None,
                'min_return': None,
                'volatility': None
            }
        
        portfolio_returns_list = []
        
        # Calculate daily returns for each selected stock
        for symbol in selected_symbols:
            # Use .query() method to avoid comparison issues
            try:
                stock_data = self.historical_data.query(f"Symbol == '{symbol}'").copy()
            except:
                # Fallback method if query fails
                stock_data = self.historical_data[self.historical_data['Symbol'].str.equals(symbol)].copy()
            
            if not stock_data.empty:
                stock_data['Daily_Return'] = stock_data['close'].pct_change(fill_method=None)
                portfolio_returns_list.append(stock_data[['Daily_Return']])
        
        if not portfolio_returns_list:
            return {
                'portfolio_dates': [],
                'portfolio_returns': [],
                'current_return': None,
                'max_return': None,
                'min_return': None,
                'volatility': None
            }
        
        # Calculate equally weighted portfolio returns
        all_daily_returns = pd.concat(portfolio_returns_list)
        daily_portfolio_return = all_daily_returns.groupby(all_daily_returns.index)['Daily_Return'].mean().dropna()
        
        if len(daily_portfolio_return) == 0:
            return {
                'portfolio_dates': [],
                'portfolio_returns': [],
                'current_return': None,
                'max_return': None,
                'min_return': None,
                'volatility': None
            }
        
        cumulative_portfolio_return = (1 + daily_portfolio_return).cumprod() - 1
        cumulative_portfolio_return_pct = cumulative_portfolio_return * 100
        
        # Calculate portfolio drawdown
        portfolio_peaks = cumulative_portfolio_return_pct.expanding().max()
        portfolio_drawdown = (cumulative_portfolio_return_pct - portfolio_peaks)
        max_portfolio_drawdown = round(portfolio_drawdown.min(), 2) if len(portfolio_drawdown) > 0 else 0
        current_portfolio_drawdown = round(portfolio_drawdown.iloc[-1], 2) if len(portfolio_drawdown) > 0 else 0
        
        return {
            'portfolio_dates': cumulative_portfolio_return.index.strftime('%Y-%m-%d').tolist(),
            'portfolio_returns': cumulative_portfolio_return_pct.tolist(),
            'current_return': round(cumulative_portfolio_return_pct.iloc[-1], 2) if len(cumulative_portfolio_return_pct) > 0 else None,
            'max_return': round(cumulative_portfolio_return_pct.max(), 2) if len(cumulative_portfolio_return_pct) > 0 else None,
            'min_return': round(cumulative_portfolio_return_pct.min(), 2) if len(cumulative_portfolio_return_pct) > 0 else None,
            'volatility': round(daily_portfolio_return.std() * 100, 2) if len(daily_portfolio_return) > 0 else None,
            'max_drawdown': max_portfolio_drawdown,
            'current_drawdown': current_portfolio_drawdown
        }
    
    def generate_interactive_chart_data(self) -> dict:
        """Generate all data needed for the interactive chart"""
        symbols = self.dataset['Symbol'].tolist()
        
        # Calculate portfolio returns with all stocks
        portfolio_data = self.calculate_portfolio_returns(symbols)
        
        # Calculate individual stock data (optimized for large datasets)
        individual_stocks = {}
        colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#aec7e8',
                 '#ffbb78', '#98df8a', '#ff9999', '#c5b0d5', '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5', '#ad494a']
        
        # Limit to manageable number for visualization (first 50 stocks for individual display)
        display_symbols = symbols[:50] if len(symbols) > 50 else symbols
        
        for i, symbol in enumerate(display_symbols):
            stock_data = self.historical_data[self.historical_data['Symbol'] == symbol].copy()
            
            if not stock_data.empty:
                stock_data = stock_data.sort_index()
                first_price = stock_data['close'].iloc[0]
                stock_cumulative_return = ((stock_data['close'] / first_price) - 1) * 100
                
                individual_stocks[symbol] = {
                    'dates': stock_data.index.strftime('%Y-%m-%d').tolist(),
                    'returns': stock_cumulative_return.tolist(),
                    'color': colors[i % len(colors)],
                    'individual_return': self.get_individual_stock_return(symbol)
                }
        
        # Calculate stock impacts
        stock_impacts = self.calculate_stock_performance_impact()
        
        return {
            'portfolio_data': portfolio_data,
            'individual_stocks': individual_stocks,
            'stock_impacts': stock_impacts,
            'all_symbols': symbols
        }
    
    def generate_report(self) -> str:
        """Generate the complete interactive HTML report and save to file"""
        
        try:
            chart_data = self.generate_interactive_chart_data()
            
            # Ensure all data is JSON serializable
            def make_json_safe(obj):
                if isinstance(obj, dict):
                    return {k: make_json_safe(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_json_safe(v) for v in obj]
                elif isinstance(obj, np.bool_):
                    return bool(obj)
                elif isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif pd.isna(obj):
                    return None
                else:
                    return obj
            
            chart_data = make_json_safe(chart_data)
        
        except Exception as e:
            return f"""
            <html>
            <head><title>Portfolio Drag Analysis - Error</title></head>
            <body>
                <h1>Portfolio Drag Analysis - Error</h1>
                <p>Error generating chart data: {str(e)}</p>
            </body>
            </html>
            """
        
        # Generate current timestamp
        current_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        
        nav = get_nav_bar('Drag Analysis')
        how_it_works = get_how_it_works('How This Report Works', [
            ('What It Shows', 'Interactive analysis identifying which stocks are dragging down your portfolio performance'),
            ('Interactive Chart', 'Click legend items to remove/add stocks and see real-time portfolio recalculation'),
            ('Drag Table', 'Red highlighted rows indicate stocks hurting portfolio returns; sorted by drag impact'),
            ('Impact Analysis', '"Return Without" shows what your portfolio would return without that stock'),
            ('Recommended Actions', 'High drag impact stocks: consider reducing position, re-evaluate thesis, or use Optimization report for rebalancing'),
        ])

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Drag Analysis - Interactive Stock Impact</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>{get_base_css()}
        .metric-card {{ background:#161b22; border:1px solid #30363d; padding:15px; border-radius:8px; text-align:center; }}
        .metric-label {{ font-size:0.85em; color:#8b949e; margin-bottom:5px; }}
        .metric-value {{ font-size:1.6em; font-weight:bold; }}
        .performance-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:20px 0; }}
        .dragger-row {{ background:rgba(248,81,73,0.1); }}
        .chart-container {{ margin:20px 0; border-radius:8px; overflow-x:auto; }}
    </style>
    <script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
    <h1>🎯 Portfolio Drag Analysis</h1>
    <p class="subtitle">Interactive Stock Impact Analysis — Generated on {current_time}</p>

{how_it_works}
            <div class="section">
                <h3>🔍 How to Use This Large Portfolio Analysis</h3>
                <ul>
                    <li><strong>Chart displays first 50 stocks</strong> individually (all {len(chart_data['all_symbols'])} stocks included in portfolio calculation)</li>
                    <li><strong>Click legend items</strong> to hide/show stocks and see real-time portfolio recalculation</li>
                    <li><strong>Table below shows all stocks</strong> with impact analysis and drag identification</li>
                    <li><strong>Red highlighted rows</strong> are potential draggers that hurt portfolio performance</li>
                </ul>
            </div>
            
            <div id="performance-summary">
                <h3>📊 Current Portfolio Performance</h3>
                <div class="performance-grid">
                    <div class="metric-card">
                        <div class="metric-label">Current Return</div>
                        <div class="metric-value" id="current-return">{chart_data['portfolio_data']['current_return']}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Return</div>
                        <div class="metric-value positive" id="max-return">{chart_data['portfolio_data']['max_return']}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Min Return</div>
                        <div class="metric-value negative" id="min-return">{chart_data['portfolio_data']['min_return']}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Volatility</div>
                        <div class="metric-value neutral" id="volatility">{chart_data['portfolio_data']['volatility']}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Drawdown</div>
                        <div class="metric-value negative" id="max-drawdown">{chart_data['portfolio_data']['max_drawdown']}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Current Drawdown</div>
                        <div class="metric-value negative" id="current-drawdown">{chart_data['portfolio_data']['current_drawdown']}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Active Stocks</div>
                        <div class="metric-value neutral" id="active-stocks">{len(chart_data['all_symbols'])}</div>
                    </div>
                </div>
            </div>
            
            <div class="chart-container">
                <div id="portfolio-chart"></div>
            </div>
            
            <div class="section">
                <h3>🚫 Stock Impact Analysis - All {len(chart_data['all_symbols'])} Stocks</h3>
                <div class="methodology">
                    <strong>📊 Portfolio Overview:</strong> 
                    {len([s for s in chart_data['stock_impacts'].values() if s.get('is_dragger', False)])} potential draggers identified out of {len(chart_data['all_symbols'])} stocks.
                    Chart shows first 50 stocks for visualization clarity.
                </div>
                <p class="sort-hint">Click any column header to sort</p>
                <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th onclick="sortTable(this)">Stock Symbol</th>
                            <th onclick="sortTable(this)">Individual Return</th>
                            <th onclick="sortTable(this)">Portfolio Impact</th>
                            <th onclick="sortTable(this)">Max Drawdown</th>
                            <th onclick="sortTable(this)">Current Drawdown</th>
                            <th onclick="sortTable(this)">From 52W High</th>
                            <th onclick="sortTable(this)">From 52W Low</th>
                            <th onclick="sortTable(this)">Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        # Add stock impact table rows
        for symbol in chart_data['all_symbols']:
            if symbol in chart_data['stock_impacts']:
                impact_data = chart_data['stock_impacts'][symbol]
                individual_return = impact_data['individual_return']
                impact = impact_data['impact']
                is_dragger = impact_data['is_dragger']
                
                # Drawdown metrics
                max_drawdown = impact_data.get('max_drawdown', 0)
                current_drawdown = impact_data.get('current_drawdown', 0)
                from_52w_high = impact_data.get('from_52w_high', 0)
                from_52w_low = impact_data.get('from_52w_low', 0)
                
                row_class = 'dragger-row' if is_dragger else ''
                status = '🚫 Dragger' if is_dragger else '✅ Helper'
                impact_color = 'positive' if impact > 0 else 'negative'
                individual_color = 'positive' if individual_return > 0 else 'negative'
                
                # Color coding for drawdown metrics
                max_dd_color = 'negative' if max_drawdown < -10 else 'neutral'
                current_dd_color = 'negative' if current_drawdown < -5 else 'neutral'
                high_52w_color = 'negative' if from_52w_high < -20 else 'neutral'
                low_52w_color = 'positive' if from_52w_low > 20 else 'neutral'
                
                html_content += f"""
                        <tr class="{row_class}">
                            <td><strong>{symbol}</strong></td>
                            <td class="{individual_color}">{individual_return}%</td>
                            <td class="{impact_color}">{"+" if impact > 0 else ""}{impact}%</td>
                            <td class="{max_dd_color}">{max_drawdown}%</td>
                            <td class="{current_dd_color}">{current_drawdown}%</td>
                            <td class="{high_52w_color}">{from_52w_high}%</td>
                            <td class="{low_52w_color}">{from_52w_low}%</td>
                            <td>{status}</td>
                        </tr>
"""
        
        html_content += f"""
                    </tbody>
                </table>
                </div>
                <div class="methodology">
                    <p><strong>📊 Column Explanations:</strong></p>
                    <ul>
                        <li><strong>Portfolio Impact:</strong> Positive values mean removing the stock improves portfolio performance (potential dragger)</li>
                        <li><strong>Max Drawdown:</strong> Maximum percentage decline from peak during the period</li>
                        <li><strong>Current Drawdown:</strong> Current percentage decline from the most recent peak</li>
                        <li><strong>From 52W High:</strong> Percentage down from 52-week high (negative = below high)</li>
                        <li><strong>From 52W Low:</strong> Percentage up from 52-week low (positive = above low)</li>
                    </ul>
                </div>
            </div>

    <script>
        // Chart data
        const chartData = {json.dumps(chart_data)};
        let currentVisibleStocks = [...chartData.all_symbols];
        
        // Initialize chart
        function initializeChart() {{
            const traces = [];
            
            // Add main portfolio line
            traces.push({{
                x: chartData.portfolio_data.portfolio_dates,
                y: chartData.portfolio_data.portfolio_returns,
                mode: 'lines',
                name: 'Portfolio Returns',
                line: {{ color: '#1f77b4', width: 4 }},
                hovertemplate: '<b>Portfolio Return</b><br>Date: %{{x}}<br>Return: %{{y:.2f}}%<extra></extra>',
                legendgroup: 'portfolio'
            }});
            
            // Add individual stock traces
            Object.keys(chartData.individual_stocks).forEach(symbol => {{
                const stockData = chartData.individual_stocks[symbol];
                traces.push({{
                    x: stockData.dates,
                    y: stockData.returns,
                    mode: 'lines',
                    name: symbol,
                    line: {{ color: stockData.color, width: 2, dash: 'dot' }},
                    hovertemplate: `<b>${{symbol}}</b><br>Date: %{{x}}<br>Return: %{{y:.2f}}%<extra></extra>`,
                    visible: true,
                    legendgroup: symbol
                }});
            }});
            
            const layout = {{
                title: {{text:'📈 Interactive Portfolio Returns - Click Legend to Remove/Add Stocks', font:{{color:'#c9d1d9'}}}},
                xaxis: {{ title: 'Date', gridcolor:'#21262d', color:'#8b949e', showspikes: true, spikemode: 'across', spikesnap: 'cursor', spikethickness: 1, spikedash: 'dot', spikecolor: '#8b949e' }},
                yaxis: {{ title: 'Cumulative Return (%)', gridcolor:'#21262d', color:'#8b949e', showspikes: true, spikemode: 'across', spikesnap: 'cursor', spikethickness: 1, spikedash: 'dot', spikecolor: '#8b949e' }},
                hovermode: 'closest',
                paper_bgcolor: '#161b22',
                plot_bgcolor: '#0d1117',
                font: {{color: '#c9d1d9'}},
                height: 800,
                width: 1400,
                showlegend: true,
                legend: {{
                    orientation: 'v',
                    yanchor: 'top',
                    y: 1,
                    xanchor: 'left',
                    x: 1.02,
                    bgcolor: 'rgba(22,27,34,0.9)',
                    bordercolor: '#30363d',
                    borderwidth: 1,
                    font: {{size: 10, color:'#c9d1d9'}},
                    itemsizing: 'constant',
                    itemwidth: 30
                }},
                margin: {{
                    l: 60,
                    r: 200,  // More space for vertical legend
                    t: 80,
                    b: 80
                }},
                shapes: [{{
                    type: 'line',
                    x0: chartData.portfolio_data.portfolio_dates[0],
                    x1: chartData.portfolio_data.portfolio_dates[chartData.portfolio_data.portfolio_dates.length - 1],
                    y0: 0,
                    y1: 0,
                    line: {{ color: 'gray', width: 1, dash: 'dash' }}
                }}]
            }};
            
            Plotly.newPlot('portfolio-chart', traces, layout);
            
            // Add legend click handler for dynamic recalculation
            document.getElementById('portfolio-chart').on('plotly_legendclick', function(data) {{
                setTimeout(() => {{
                    recalculatePortfolio();
                }}, 100);
                return true; // Allow normal legend behavior
            }});
        }}
        
        // Recalculate portfolio based on visible traces (optimized for large datasets)
        function recalculatePortfolio() {{
            const chart = document.getElementById('portfolio-chart');
            const data = chart.data;
            
            // Get currently visible individual stocks
            const visibleStocks = [];
            data.forEach(trace => {{
                if (trace.name !== 'Portfolio Returns' && 
                    trace.visible !== false && 
                    trace.visible !== 'legendonly') {{
                    visibleStocks.push(trace.name);
                }}
            }});
            
            currentVisibleStocks = visibleStocks;
            
            // For large portfolios, show loading indicator
            if (chartData.all_symbols.length > 100) {{
                document.getElementById('current-return').textContent = 'Calculating...';
            }}
            
            // Calculate new portfolio returns with visible stocks only
            if (visibleStocks.length === 0) {{
                // If no stocks visible, hide portfolio line
                Plotly.restyle('portfolio-chart', {{ visible: 'legendonly' }}, [0]);
                updateMetrics({{ 
                    current_return: 0, 
                    max_return: 0, 
                    min_return: 0, 
                    volatility: 0, 
                    total_stocks: 0,
                    portfolio_returns: [0]
                }});
                return;
            }}
            
            // Use setTimeout for non-blocking calculation with large datasets
            setTimeout(() => {{
                calculatePortfolioMetrics(visibleStocks);
            }}, 10);
        }}
        
        // Separate function for portfolio metrics calculation
        function calculatePortfolioMetrics(visibleStocks) {{
            // Calculate equally weighted portfolio with visible stocks
            const portfolioDates = [];
            const portfolioReturns = [];
            
            // Get common dates (optimized for large datasets)
            const allDates = new Set();
            const stockDataCache = {{}};
            
            // Cache stock data for performance
            visibleStocks.forEach(symbol => {{
                if (chartData.individual_stocks[symbol]) {{
                    stockDataCache[symbol] = chartData.individual_stocks[symbol];
                    chartData.individual_stocks[symbol].dates.forEach(date => allDates.add(date));
                }}
            }});
            
            const sortedDates = Array.from(allDates).sort();
            
            // Calculate daily returns for visible stocks (batch processing)
            const dailyReturns = {{}};
            Object.keys(stockDataCache).forEach(symbol => {{
                const stockData = stockDataCache[symbol];
                const dates = stockData.dates;
                const returns = stockData.returns;
                
                for (let i = 1; i < dates.length; i++) {{
                    const date = dates[i];
                    const prevReturn = returns[i-1];
                    const currReturn = returns[i];
                    const dailyReturn = currReturn - prevReturn;
                    
                    if (!dailyReturns[date]) dailyReturns[date] = [];
                    dailyReturns[date].push(dailyReturn);
                }}
            }});
            
            // Calculate portfolio cumulative returns
            let cumulativeReturn = 0;
            sortedDates.forEach(date => {{
                if (dailyReturns[date] && dailyReturns[date].length > 0) {{
                    const avgDailyReturn = dailyReturns[date].reduce((a, b) => a + b, 0) / dailyReturns[date].length;
                    cumulativeReturn += avgDailyReturn;
                    portfolioDates.push(date);
                    portfolioReturns.push(cumulativeReturn);
                }}
            }});
            
            // Update portfolio trace
            if (portfolioDates.length > 0) {{
                const newName = `Portfolio (${{visibleStocks.length}}/${{chartData.all_symbols.length}} stocks)`;
                Plotly.restyle('portfolio-chart', {{
                    x: [portfolioDates],
                    y: [portfolioReturns],
                    name: [newName],
                    visible: [true]
                }}, [0]);
                
                // Update metrics
                const currentReturn = portfolioReturns[portfolioReturns.length - 1] || 0;
                const maxReturn = Math.max(...portfolioReturns);
                const minReturn = Math.min(...portfolioReturns);
                const volatility = calculateVolatility(portfolioReturns);
                
                updateMetrics({{
                    current_return: currentReturn.toFixed(2),
                    max_return: maxReturn.toFixed(2),
                    min_return: minReturn.toFixed(2),
                    volatility: volatility.toFixed(2),
                    total_stocks: visibleStocks.length,
                    portfolio_returns: portfolioReturns
                }});
            }}
        }}
        
        function calculateVolatility(returns) {{
            if (returns.length < 2) return 0;
            const dailyChanges = [];
            for (let i = 1; i < returns.length; i++) {{
                dailyChanges.push(returns[i] - returns[i-1]);
            }}
            const mean = dailyChanges.reduce((a, b) => a + b, 0) / dailyChanges.length;
            const variance = dailyChanges.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / dailyChanges.length;
            return Math.sqrt(variance);
        }}
        
        // Update performance metrics display
        function updateMetrics(metrics) {{
            document.getElementById('current-return').textContent = `${{metrics.current_return}}%`;
            document.getElementById('current-return').className = 
                'metric-value ' + (parseFloat(metrics.current_return) >= 0 ? 'positive' : 'negative');
            
            document.getElementById('max-return').textContent = `${{metrics.max_return}}%`;
            document.getElementById('min-return').textContent = `${{metrics.min_return}}%`;
            document.getElementById('volatility').textContent = `${{metrics.volatility}}%`;
            document.getElementById('active-stocks').textContent = metrics.total_stocks;
            
            // Calculate and update drawdown metrics
            const cumulativeReturns = metrics.portfolio_returns;
            let maxDrawdown = 0;
            let currentDrawdown = 0;
            
            if (cumulativeReturns && cumulativeReturns.length > 0) {{
                let runningMax = cumulativeReturns[0];
                
                for (let i = 0; i < cumulativeReturns.length; i++) {{
                    if (cumulativeReturns[i] > runningMax) {{
                        runningMax = cumulativeReturns[i];
                    }}
                    
                    const drawdown = cumulativeReturns[i] - runningMax;
                    if (drawdown < maxDrawdown) {{
                        maxDrawdown = drawdown;
                    }}
                }}
                
                // Current drawdown is from the latest running max
                runningMax = Math.max(...cumulativeReturns);
                currentDrawdown = cumulativeReturns[cumulativeReturns.length - 1] - runningMax;
            }}
            
            document.getElementById('max-drawdown').textContent = `${{maxDrawdown.toFixed(2)}}%`;
            document.getElementById('max-drawdown').className = 
                'metric-value ' + (maxDrawdown >= 0 ? 'positive' : 'negative');
                
            document.getElementById('current-drawdown').textContent = `${{currentDrawdown.toFixed(2)}}%`;
            document.getElementById('current-drawdown').className = 
                'metric-value ' + (currentDrawdown >= 0 ? 'positive' : 'negative');
        }}
        
        // Initialize the chart when page loads
        document.addEventListener('DOMContentLoaded', initializeChart);
    </script>

    <div class="footer">
        Portfolio Drag Analysis &bull; Generated by Portfolio Analysis System
    </div>
</div>
</body>
</html>
        """
        
        # Save report to file
        # Ensure reports directory exists
        os.makedirs('reports', exist_ok=True)
        
        # Generate filename with timestamp
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"reports/portfolio_drag_analysis_{date_str}.html"
        
        # Save HTML content to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Portfolio Drag Analysis Report saved: {filename}")
        return html_content

def generate_portfolio_drag_report(comprehensive_dataset: pd.DataFrame, historical_data: pd.DataFrame) -> str:
    """Generate the portfolio drag analysis report"""
    try:
        analyzer = PortfolioDragAnalyzer(comprehensive_dataset, historical_data)
        return analyzer.generate_report()
    except Exception as e:
        return f"""
        <html>
        <head><title>Portfolio Drag Analysis - Error</title></head>
        <body>
            <h1>Portfolio Drag Analysis - Error</h1>
            <p>Error generating portfolio drag analysis: {str(e)}</p>
            <p>Details: {str(e)}</p>
        </body>
        </html>
        """

if __name__ == "__main__":
    print("Portfolio Drag Analyzer module loaded successfully!")
