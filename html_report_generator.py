#!/usr/bin/env python3
"""
HTML Report Generator Module
Creates comprehensive HTML reports with interactive plotly charts
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from datetime import datetime, date
from typing import Dict, List, Optional
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works

# Set plotly template
pio.templates.default = "plotly_dark"

class HTMLReportGenerator:
    """Generate comprehensive HTML reports with embedded charts"""
    
    def __init__(self):
        self.charts = {}
        self.insights = {}
    
    def create_portfolio_charts(self, analysis_df: pd.DataFrame, portfolio_manager) -> Dict:
        """Create all portfolio charts"""
        charts = {}
        
        if analysis_df.empty:
            return charts
        
        try:
            # Portfolio allocation pie chart
            charts['allocation'] = self._create_allocation_chart(analysis_df)
            
            # Returns distribution bar chart
            charts['returns'] = self._create_returns_chart(analysis_df)
            
            # Risk-return scatter plot
            charts['risk_return'] = self._create_risk_return_chart(analysis_df)
            
            # Cumulative returns line chart
            charts['cumulative'] = self._create_cumulative_returns_chart(analysis_df, portfolio_manager)
            
            # Technical indicators summary
            charts['technical_summary'] = self._create_technical_summary_chart(analysis_df)
            
            print("✅ All portfolio charts created successfully")
            
        except Exception as e:
            print(f"⚠️  Error creating charts: {e}")
        
        return charts
    
    def _create_allocation_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create portfolio allocation pie chart"""
        if 'Allocation_Pct' not in df.columns:
            return None
        
        fig = go.Figure(data=[go.Pie(
            labels=df['Symbol'],
            values=df['Allocation_Pct'],
            hole=0.4,
            textinfo='label+percent',
            textposition='outside',
            marker=dict(
                colors=px.colors.qualitative.Set3,
                line=dict(color='#000000', width=2)
            )
        )])
        
        fig.update_layout(
            title={
                'text': 'Portfolio Allocation by Stock',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            template='plotly_dark',
            showlegend=True,
            height=500,
            margin=dict(t=100, b=50, l=50, r=50)
        )
        
        return fig
    
    def _create_returns_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create returns distribution bar chart"""
        if 'Profit_Loss_Pct' not in df.columns:
            return None
        
        # Sort by returns for better visualization
        df_sorted = df.sort_values('Profit_Loss_Pct', ascending=True)
        
        colors = ['#f44336' if x < 0 else '#4CAF50' for x in df_sorted['Profit_Loss_Pct']]
        
        fig = go.Figure(data=[go.Bar(
            x=df_sorted['Symbol'],
            y=df_sorted['Profit_Loss_Pct'],
            marker_color=colors,
            text=[f"{x:.1f}%" for x in df_sorted['Profit_Loss_Pct']],
            textposition='outside',
            name='Returns'
        )])
        
        fig.update_layout(
            title={
                'text': 'Individual Stock Returns Distribution',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            xaxis_title='Stock Symbol',
            yaxis_title='Return (%)',
            template='plotly_dark',
            height=500,
            showlegend=False,
            margin=dict(t=100, b=100, l=50, r=50)
        )
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.7)
        
        # Rotate x-axis labels for better readability
        fig.update_xaxes(tickangle=45)
        
        return fig
    
    def _create_risk_return_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create risk vs return scatter plot"""
        if 'Profit_Loss_Pct' not in df.columns or 'volatility' not in df.columns:
            return None
        
        fig = go.Figure()
        
        # Calculate bubble sizes based on allocation
        sizes = df.get('Allocation_Pct', pd.Series([10]*len(df))).fillna(10)
        normalized_sizes = ((sizes - sizes.min()) / (sizes.max() - sizes.min()) * 30 + 10) if sizes.max() > sizes.min() else [20] * len(df)
        # Ensure no NaN in sizes
        if hasattr(normalized_sizes, 'fillna'):
            normalized_sizes = normalized_sizes.fillna(15).tolist()
        
        fig.add_trace(go.Scatter(
            x=df['volatility'],
            y=df['Profit_Loss_Pct'],
            mode='markers+text',
            text=df['Symbol'],
            textposition='top center',
            marker=dict(
                size=normalized_sizes,
                color=df['Profit_Loss_Pct'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Return %"),
                line=dict(width=2, color='white')
            ),
            name='Stocks',
            hovertemplate='<b>%{text}</b><br>' +
                         'Volatility: %{x:.2%}<br>' +
                         'Return: %{y:.2f}%<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title={
                'text': 'Risk vs Return Analysis',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            xaxis_title='Volatility (Risk)',
            yaxis_title='Return (%)',
            template='plotly_dark',
            height=600,
            margin=dict(t=100, b=50, l=50, r=50)
        )
        
        # Add quadrant lines if we have data
        if len(df) > 1:
            mean_vol = df['volatility'].mean()
            mean_ret = df['Profit_Loss_Pct'].mean()
            
            fig.add_vline(x=mean_vol, line_dash="dash", line_color="white", opacity=0.5)
            fig.add_hline(y=mean_ret, line_dash="dash", line_color="white", opacity=0.5)
        
        return fig
    
    def _create_cumulative_returns_chart(self, df: pd.DataFrame, portfolio_manager) -> go.Figure:
        """Create cumulative returns chart"""
        fig = go.Figure()
        
        try:
            symbols = df['Symbol'].tolist()[:5]  # Limit to top 5 for readability
            
            for symbol in symbols:
                stock_data = portfolio_manager.get_stock_data(symbol)
                
                if not stock_data.empty and 'close' in stock_data.columns:
                    # Calculate daily returns and cumulative returns
                    daily_returns = stock_data['close'].pct_change(fill_method=None)
                    daily_returns = daily_returns.fillna(0.0)
                    cumulative_returns = (1 + daily_returns).cumprod() - 1
                    
                    fig.add_trace(go.Scatter(
                        x=stock_data.index,
                        y=cumulative_returns * 100,
                        mode='lines',
                        name=symbol.replace('.NS', '').replace('.BO', ''),
                        line=dict(width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     'Date: %{x}<br>' +
                                     'Cumulative Return: %{y:.2f}%<br>' +
                                     '<extra></extra>'
                    ))
            
            fig.update_layout(
                title={
                    'text': 'Cumulative Returns Over Time (Top 5 Holdings)',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 20}
                },
                xaxis_title='Date',
                yaxis_title='Cumulative Return (%)',
                template='plotly_dark',
                height=800,
                width=1400,
                hovermode='closest',
                margin=dict(
                    l=60,
                    r=200,
                    t=80,
                    b=80
                ),
                showlegend=True,
                legend=dict(
                    orientation="v",
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
            )
            
            # Add range selector and crosshair spikes
            fig.update_layout(
                xaxis=dict(
                    showspikes=True,
                    spikemode='across',
                    spikesnap='cursor',
                    spikethickness=1,
                    spikedash='dot',
                    spikecolor='#8b949e',
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1M", step="month", stepmode="backward"),
                            dict(count=3, label="3M", step="month", stepmode="backward"),
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(step="all")
                        ])
                    ),
                    rangeslider=dict(visible=True),
                    type="date"
                ),
                yaxis=dict(
                    showspikes=True,
                    spikemode='across',
                    spikesnap='cursor',
                    spikethickness=1,
                    spikedash='dot',
                    spikecolor='#8b949e'
                )
            )
            
        except Exception as e:
            print(f"⚠️  Error creating cumulative returns chart: {e}")
        
        return fig
    
    def _create_technical_summary_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create technical indicators summary chart"""
        if 'rsi' not in df.columns:
            return None
        
        # Create subplots for different technical indicators
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('RSI Distribution', 'MACD Signals', 'Bollinger Band Positions', 'Volume Ratios'),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        try:
            # RSI Distribution
            rsi_data = df['rsi'].dropna()
            if not rsi_data.empty:
                rsi_colors = ['red' if x > 70 else 'orange' if x < 30 else 'green' for x in rsi_data]
                fig.add_trace(go.Bar(
                    x=df['Symbol'],
                    y=rsi_data,
                    marker_color=rsi_colors,
                    name='RSI',
                    showlegend=False
                ), row=1, col=1)
                
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=1, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=1, col=1)
            
            # MACD Signals
            if 'macd' in df.columns:
                macd_data = df['macd'].dropna()
                if not macd_data.empty:
                    macd_colors = ['green' if x > 0 else 'red' for x in macd_data]
                    fig.add_trace(go.Bar(
                        x=df['Symbol'],
                        y=macd_data,
                        marker_color=macd_colors,
                        name='MACD',
                        showlegend=False
                    ), row=1, col=2)
                    
                    fig.add_hline(y=0, line_dash="dash", line_color="white", row=1, col=2)
            
            # Bollinger Band Positions
            if 'bb_position' in df.columns:
                bb_data = df['bb_position'].dropna()
                if not bb_data.empty:
                    bb_colors = ['red' if x > 0.8 else 'orange' if x < 0.2 else 'green' for x in bb_data]
                    fig.add_trace(go.Bar(
                        x=df['Symbol'],
                        y=bb_data,
                        marker_color=bb_colors,
                        name='BB Position',
                        showlegend=False
                    ), row=2, col=1)
                    
                    fig.add_hline(y=0.8, line_dash="dash", line_color="red", row=2, col=1)
                    fig.add_hline(y=0.2, line_dash="dash", line_color="green", row=2, col=1)
            
            # Volume Ratios
            if 'volume_ratio' in df.columns:
                vol_data = df['volume_ratio'].dropna()
                if not vol_data.empty:
                    vol_colors = ['green' if x > 1.5 else 'orange' if x > 1 else 'gray' for x in vol_data]
                    fig.add_trace(go.Bar(
                        x=df['Symbol'],
                        y=vol_data,
                        marker_color=vol_colors,
                        name='Volume Ratio',
                        showlegend=False
                    ), row=2, col=2)
                    
                    fig.add_hline(y=1, line_dash="dash", line_color="white", row=2, col=2)
            
            fig.update_layout(
                title={
                    'text': 'Technical Indicators Summary',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 20}
                },
                template='plotly_dark',
                height=600,
                margin=dict(t=100, b=50, l=50, r=50)
            )
            
            # Update all x-axes to rotate labels
            fig.update_xaxes(tickangle=45)
            
        except Exception as e:
            print(f"⚠️  Error creating technical summary chart: {e}")
        
        return fig
    
    def generate_html_report(self, portfolio_data, insights, charts, output_filename=None):
        """Generate comprehensive HTML report with interactive charts"""
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d")
            output_filename = f"reports/portfolio_report_{timestamp}.html"
        elif not output_filename.startswith('reports/'):
            output_filename = f"reports/{output_filename}"
        
        # Ensure reports directory exists
        import os
        os.makedirs('reports', exist_ok=True)
        
        # Build complete HTML
        html_parts = []
        html_parts.append(self._get_html_header())
        
        # How This Report Works
        html_parts.append(get_how_it_works('How This Report Works', [
            ('Summary Cards', 'Show portfolio totals — investment, current value, P&L, return %, and stock count at a glance'),
            ('Performance Highlights', 'Identify best and worst performing stocks in your portfolio'),
            ('Portfolio Verdict', 'Composite Score (0-100) across Relative Strength, Trend, Momentum, Risk & Volume — drives Buy/Hold/Sell signals'),
            ('Interactive Charts', 'Allocation pie, returns bar, risk-return scatter, cumulative line & technical heatmap — click legends to toggle'),
            ('Analysis Table', 'Sortable table with price, return, RSI, volatility and allocation — click any header to sort'),
        ]))
        
        # Summary cards
        html_parts.append(self._generate_summary_cards(insights))
        
        # Performance highlights
        html_parts.append(self._generate_performance_highlights(insights))
        
        # Portfolio Verdict & Top Actions (new)
        html_parts.append(self._generate_portfolio_verdict(portfolio_data, insights))
        
        # Charts section
        html_parts.append(self._generate_charts_section(charts))
        
        # Analysis table
        html_parts.append(self._generate_analysis_table(portfolio_data))
        
        # Footer
        html_parts.append(self._get_html_footer())
        
        # Combine all parts
        html_content = ''.join(html_parts)
        
        # Write to file
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML report saved: {output_filename}")
        return output_filename
    
    def _get_html_header(self) -> str:
        """Get HTML header with shared dark-theme CSS"""
        nav = get_nav_bar('Portfolio Report')
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Analysis Report</title>
<style>{get_base_css()}
    .chart-container {{ background:#161b22; border:1px solid #30363d; border-radius:10px; padding:20px; margin:20px 0; }}
    .chart-title {{ font-size:1.3em; color:#58a6ff; margin-bottom:15px; padding-bottom:8px; border-bottom:1px solid #30363d; font-weight:600; }}
</style>
<script>{get_sortable_table_js()}</script>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
{nav}
<div class="container">
    <h1>Portfolio Analysis Report</h1>
    <p class="subtitle">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
"""
    
    def _generate_summary_cards(self, insights: Dict) -> str:
        """Generate summary cards HTML"""
        if 'portfolio_summary' not in insights:
            return ""
        
        ps = insights['portfolio_summary']
        total_return_color = 'positive' if ps.get('portfolio_return_pct', 0) >= 0 else 'negative'
        
        return f"""
    <div class="cards">
        <div class="card">
            <div class="label">💰 Total Investment</div>
            <div class="value">₹{ps.get('total_investment', 0):,.0f}</div>
        </div>
        <div class="card">
            <div class="label">📈 Current Value</div>
            <div class="value">₹{ps.get('current_value', 0):,.0f}</div>
        </div>
        <div class="card">
            <div class="label">📊 Total P&L</div>
            <div class="value {total_return_color}">₹{ps.get('total_pnl', 0):,.0f}</div>
        </div>
        <div class="card">
            <div class="label">📈 Portfolio Return</div>
            <div class="value {total_return_color}">{ps.get('portfolio_return_pct', 0):.2f}%</div>
        </div>
        <div class="card">
            <div class="label">🏢 Total Stocks</div>
            <div class="value">{ps.get('total_stocks', 0)}</div>
        </div>
    </div>
"""
    
    def _generate_performance_highlights(self, insights: Dict) -> str:
        """Generate performance highlights HTML"""
        if 'performance' not in insights:
            return ""
        
        perf = insights['performance']
        best_color = 'positive' if perf['best_performer']['return_pct'] >= 0 else 'negative'
        worst_color = 'positive' if perf['worst_performer']['return_pct'] >= 0 else 'negative'
        
        return f"""
    <div class="cards">
        <div class="card">
            <div class="label">🏆 Best Performer</div>
            <div class="value {best_color}">{perf['best_performer']['symbol']}</div>
            <div class="sub {best_color}">{perf['best_performer']['return_pct']:.2f}% return</div>
        </div>
        <div class="card">
            <div class="label">📉 Worst Performer</div>
            <div class="value {worst_color}">{perf['worst_performer']['symbol']}</div>
            <div class="sub {worst_color}">{perf['worst_performer']['return_pct']:.2f}% return</div>
        </div>
    </div>
"""
    
    def _generate_portfolio_verdict(self, analysis_df: pd.DataFrame, insights: Dict) -> str:
        """Generate Portfolio Verdict card with top-actions and scoring summary."""
        if analysis_df.empty:
            return ""

        parts = []

        # --- Scoring summary if Composite_Score present ---
        if 'Composite_Score' in analysis_df.columns:
            avg_score = analysis_df['Composite_Score'].mean()
            buy_count = len(analysis_df[analysis_df.get('Signal', pd.Series()).isin(['Strong Buy', 'Buy'])]) if 'Signal' in analysis_df.columns else 0
            sell_count = len(analysis_df[analysis_df.get('Signal', pd.Series()).isin(['Strong Sell', 'Sell'])]) if 'Signal' in analysis_df.columns else 0
            hold_count = len(analysis_df[analysis_df.get('Signal', pd.Series()) == 'Hold']) if 'Signal' in analysis_df.columns else 0

            # Top recommendations
            top_buys = analysis_df.nlargest(3, 'Composite_Score')[['Symbol', 'Composite_Score']].values.tolist() if len(analysis_df) > 0 else []
            top_sells = analysis_df.nsmallest(3, 'Composite_Score')[['Symbol', 'Composite_Score']].values.tolist() if len(analysis_df) > 0 else []

            buy_chips = ' '.join(f'<span style="background:#4CAF50;color:#fff;padding:3px 10px;border-radius:12px;font-size:0.85em">{s} ({sc:.0f})</span>' for s, sc in top_buys)
            sell_chips = ' '.join(f'<span style="background:#f44336;color:#fff;padding:3px 10px;border-radius:12px;font-size:0.85em">{s} ({sc:.0f})</span>' for s, sc in top_sells)

            score_color = '#4CAF50' if avg_score >= 65 else '#FF9800' if avg_score >= 40 else '#f44336'
            verdict_text = 'Portfolio is in strong shape — keep riding winners' if avg_score >= 65 else \
                           'Portfolio is mixed — prune weak positions and monitor closely' if avg_score >= 40 else \
                           'Portfolio needs urgent attention — several positions are deteriorating'

            parts.append(f"""
    <div class="chart-container" style="border-left:5px solid {score_color}">
        <div class="chart-title">🎯 Portfolio Verdict</div>
        <div style="display:flex;gap:30px;align-items:center;flex-wrap:wrap">
            <div style="text-align:center;min-width:120px">
                <div style="font-size:3em;font-weight:bold;color:{score_color}">{avg_score:.0f}</div>
                <div style="opacity:0.7;font-size:0.9em">Avg Composite Score</div>
            </div>
            <div style="flex:1;min-width:250px">
                <p style="font-size:1.1em;margin:0 0 8px 0"><strong>{verdict_text}</strong></p>
                <p style="margin:0;opacity:0.8">
                    Signals: <span class="positive">{buy_count} Buy</span> |
                    <span style="color:#FF9800">{hold_count} Hold</span> |
                    <span class="negative">{sell_count} Sell</span>
                </p>
            </div>
        </div>
        <div style="margin-top:18px">
            <div style="margin-bottom:8px"><strong>Top Scoring (consider adding):</strong> {buy_chips}</div>
            <div><strong>Bottom Scoring (review/exit):</strong> {sell_chips}</div>
        </div>
        <div style="margin-top:12px;padding:10px;background:rgba(255,255,255,0.05);border-radius:8px;font-size:0.85em;opacity:0.8">
            <strong>How we arrived here:</strong> Each stock is scored 0-100 across five categories —
            Relative Strength (benchmark comparison), Trend (moving average position), Momentum (RSI &amp; daily change),
            Risk (Sharpe &amp; Sortino ratios), and Value/Volume (52-week position &amp; relative volume).
            The signal (Buy/Hold/Sell) is derived from the composite score combined with trend and risk confirmations.
        </div>
    </div>
""")
        return ''.join(parts)

    def _generate_charts_section(self, charts: Dict) -> str:
        """Generate charts section HTML"""
        html_parts = []
        
        chart_titles = {
            'allocation': 'Portfolio Allocation',
            'returns': 'Returns Distribution',
            'risk_return': 'Risk vs Return Analysis',
            'cumulative': 'Cumulative Returns Over Time',
            'technical_summary': 'Technical Indicators Summary'
        }
        
        for chart_key, chart_title in chart_titles.items():
            if chart_key in charts and charts[chart_key] is not None:
                html_parts.append('<div class="chart-container">')
                html_parts.append(f'<div class="chart-title">{chart_title}</div>')
                html_parts.append(charts[chart_key].to_html(include_plotlyjs=False, div_id=f"{chart_key}-chart"))
                html_parts.append('</div>')
        
        return ''.join(html_parts)
    
    def _generate_analysis_table(self, analysis_df: pd.DataFrame) -> str:
        """Generate detailed analysis table HTML"""
        if analysis_df.empty:
            return ""
        
        # Select key columns for display
        display_columns = ['Symbol', 'current_price', 'Profit_Loss_Pct', 'rsi', 'volatility', 'Allocation_Pct']
        display_df = analysis_df[display_columns].copy()
        
        # Format values
        display_df['current_price'] = display_df['current_price'].apply(lambda x: f"₹{x:.2f}")
        display_df['Profit_Loss_Pct'] = display_df['Profit_Loss_Pct'].apply(lambda x: f"{x:.2f}%")
        display_df['rsi'] = display_df['rsi'].apply(lambda x: f"{x:.1f}")
        display_df['volatility'] = display_df['volatility'].apply(lambda x: f"{x:.2%}")
        display_df['Allocation_Pct'] = display_df['Allocation_Pct'].apply(lambda x: f"{x:.2f}%")
        
        # Column headers
        headers = {
            'Symbol': 'Stock Symbol',
            'current_price': 'Current Price',
            'Profit_Loss_Pct': 'Return (%)',
            'rsi': 'RSI',
            'volatility': 'Volatility',
            'Allocation_Pct': 'Allocation (%)'
        }
        
        html = ['<div class="section">']
        html.append('<h2>Detailed Stock Analysis</h2>')
        html.append('<p class="sort-hint">Click any column header to sort</p>')
        html.append('<div class="table-wrapper">')
        html.append('<table>')
        
        # Table header
        html.append('<thead><tr>')
        for col in display_columns:
            html.append(f'<th onclick="sortTable(this)">{headers[col]}</th>')
        html.append('</tr></thead>')
        
        # Table body
        html.append('<tbody>')
        for _, row in display_df.iterrows():
            html.append('<tr>')
            for col in display_columns:
                value = row[col]
                css_class = 'neutral'
                
                if col == 'Profit_Loss_Pct' and '%' in str(value):
                    pct_value = float(str(value).replace('%', ''))
                    css_class = 'positive' if pct_value >= 0 else 'negative'
                
                html.append(f'<td class="{css_class}">{value}</td>')
            html.append('</tr>')
        html.append('</tbody>')
        
        html.append('</table>')
        html.append('</div>')  # close table-wrapper
        html.append('</div>')  # close section
        
        return ''.join(html)
    
    def _get_html_footer(self) -> str:
        """Get HTML footer"""
        return """
    <div class="footer">
        Generated by Portfolio Analysis System &bull; Not investment advice
    </div>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    # Test the HTML report generator
    print("🧪 Testing HTML Report Generator...")
    
    # Create sample data
    sample_data = pd.DataFrame({
        'Symbol': ['AEROFLEX.NS', 'WIPRO.NS', 'WONDERLA.NS'],
        'current_price': [175.50, 240.30, 820.75],
        'Profit_Loss_Pct': [15.5, -8.2, 22.1],
        'rsi': [65.2, 45.8, 72.3],
        'volatility': [0.25, 0.18, 0.35],
        'Allocation_Pct': [35.0, 40.0, 25.0]
    })
    
    sample_insights = {
        'portfolio_summary': {
            'total_stocks': 3,
            'total_investment': 100000,
            'current_value': 112000,
            'total_pnl': 12000,
            'portfolio_return_pct': 12.0
        },
        'performance': {
            'best_performer': {'symbol': 'WONDERLA.NS', 'return_pct': 22.1},
            'worst_performer': {'symbol': 'WIPRO.NS', 'return_pct': -8.2}
        }
    }
    
    generator = HTMLReportGenerator()
    
    # Create a simple chart for testing
    test_chart = go.Figure(data=[go.Bar(x=['A', 'B', 'C'], y=[1, 3, 2])])
    test_charts = {'allocation': test_chart}
    
    html_report = generator.generate_html_report(sample_data, sample_insights, test_charts)
    
    print("✅ Test HTML report generated in reports folder")
