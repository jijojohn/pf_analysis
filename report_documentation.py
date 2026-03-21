#!/usr/bin/env python3
"""
Report Documentation Generator
=============================
Creates comprehensive documentation explaining all reports, their logic, calculations, and analysis benefits.
"""

import pandas as pd
import os
from datetime import datetime
from config_manager import get_config
from report_style import get_base_css, get_sortable_table_js, get_nav_bar, get_how_it_works

class ReportDocumentationGenerator:
    """Generate comprehensive documentation for all portfolio reports"""
    
    def __init__(self):
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")
        
    def generate_documentation(self) -> str:
        """Generate complete documentation page
        
        Returns:
            str: Path to the saved documentation HTML file
        """
        print("📚 Generating Report Documentation & Analysis Guide...")
        
        html_content = self.create_html_documentation()
        
        # Save documentation
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{self.reports_dir}/reports_documentation_{date_str}.html"
        
        os.makedirs(self.reports_dir, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Report Documentation saved: {filename}")
        return filename
    
    def create_html_documentation(self) -> str:
        """Create comprehensive HTML documentation"""
        
        nav = get_nav_bar('Report Documentation')
        how_it_works = get_how_it_works('How This Guide Works', [
            ('Main Reports', 'Detailed explanations of each portfolio report — purpose, data sources, and analysis logic'),
            ('Filtered Reports', 'All 57+ filter criteria explained with thresholds and interpretation guidelines'),
            ('Minervini & Swing Filters', '10 new filters: 6 Minervini stage + 4 HH/HL swing pattern filters'),
            ('Performance Bar Chart', 'Period return bar charts (1W/1M/3M/6M/1Y) with gainers/losers summary'),
            ('Technical Indicators', 'RSI, Moving Averages, Sharpe, Sortino, Beta, Volatility formulas and meaning'),
            ('Calculations', 'Step-by-step methodology for every metric calculation used across reports'),
        ])

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Reports Documentation & Analysis Guide</title>
    <style>{get_base_css()}
        .report-card {{ background:#161b22; border-radius:10px; padding:25px; margin:20px 0; border-left:5px solid #58a6ff; }}
        .report-card.special {{ border-left-color:#f85149; }}
        .report-card.optimization {{ border-left-color:#3fb950; }}
        .report-title {{ font-size:1.3em; font-weight:bold; color:#58a6ff; margin-bottom:10px; }}
        .report-purpose {{ color:#8b949e; font-style:italic; margin-bottom:15px; }}
        .logic-section {{ background:#21262d; padding:15px; border-radius:8px; margin:15px 0; }}
        .formula {{ background:#0d1117; color:#79c0ff; padding:10px; border-radius:5px; font-family:'Courier New',monospace; margin:10px 0; overflow-x:auto; border:1px solid #30363d; }}
        .benefits-list {{ background:rgba(63,185,80,0.08); padding:15px; border-radius:8px; margin:15px 0; border-left:3px solid #3fb950; }}
        .benefits-list ul {{ margin:10px 0; padding-left:20px; }}
        .benefits-list li {{ margin:5px 0; color:#3fb950; }}
        .calculation-table {{ width:100%; border-collapse:collapse; margin:15px 0; background:#161b22; border-radius:8px; overflow:hidden; }}
        .calculation-table th {{ background:#21262d; color:#c9d1d9; padding:12px; text-align:left; }}
        .calculation-table td {{ padding:12px; border-bottom:1px solid #21262d; color:#c9d1d9; }}
        .calculation-table tr:hover {{ background:#1c2128; }}
        .toc {{ background:#161b22; border:2px solid #58a6ff; border-radius:10px; padding:20px; margin:20px 0; }}
        .toc h3 {{ color:#58a6ff; margin-bottom:15px; }}
        .toc ul {{ list-style:none; padding:0; }}
        .toc li {{ margin:8px 0; }}
        .toc a {{ color:#c9d1d9; text-decoration:none; padding:5px 10px; border-radius:5px; transition:background 0.3s; }}
        .toc a:hover {{ background:#21262d; }}
        .highlight {{ background:rgba(88,166,255,0.08); padding:15px; border-radius:8px; border-left:4px solid #58a6ff; margin:15px 0; color:#c9d1d9; }}
        .section h3 {{ color:#c9d1d9; margin:30px 0 15px 0; font-size:1.4em; }}
        .section h4 {{ color:#8b949e; margin:20px 0 10px 0; font-size:1.1em; }}
    </style>
    <script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
    <h1>📚 Portfolio Reports Documentation</h1>
    <p class="subtitle">Complete Analysis Guide &bull; Logic & Calculations &bull; Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

{how_it_works}
            <!-- Table of Contents -->
            <div class="toc">
                <h3>📑 Table of Contents</h3>
                <ul>
                    <li><a href="#overview">🎯 System Overview</a></li>
                    <li><a href="#main-reports">📊 Main Portfolio Reports</a></li>
                    <li><a href="#filtered-reports">🔍 Filtered Analysis Reports</a></li>
                    <li><a href="#technical-indicators">📈 Technical Indicators Explained</a></li>
                    <li><a href="#calculations">🧮 Calculation Methodologies</a></li>
                    <li><a href="#usage-guide">💡 Usage Guide & Best Practices</a></li>
                </ul>
            </div>
            
            <!-- System Overview -->
            <div id="overview" class="section">
                <h2>🎯 Portfolio Analysis System Overview</h2>
                
                <div class="highlight">
                    <strong>Purpose:</strong> This comprehensive portfolio analysis system provides multi-dimensional insights into your investment portfolio using advanced technical analysis, risk management principles, and modern portfolio theory.
                </div>
                
                <h3>System Architecture</h3>
                <p>The system is built on four core pillars:</p>
                <ul>
                    <li><strong>Data Processing:</strong> Real-time market data integration with historical analysis</li>
                    <li><strong>Technical Analysis:</strong> 20+ technical indicators with configurable parameters</li>
                    <li><strong>Risk Management:</strong> Comprehensive risk metrics and drawdown analysis</li>
                    <li><strong>Portfolio Optimization:</strong> Modern Portfolio Theory implementation with multiple strategies</li>
                </ul>
                
                <h3>Key Features</h3>
                <div class="benefits-list">
                    <ul>
                        <li>Interactive filtering system with 57+ criteria (including 6 Minervini stage, 4 HH/HL swing, 5 Sortino ratio filters)</li>
                        <li>Real-time portfolio performance tracking with Key Takeaways banner</li>
                        <li>Advanced risk metrics including Sharpe & Sortino ratios</li>
                        <li>Portfolio optimization using Modern Portfolio Theory</li>
                        <li>Drag analysis for identifying underperforming stocks</li>
                        <li>Multiple allocation strategies comparison</li>
                        <li>Comprehensive rebalancing suggestions</li>
                        <li>Master report dashboard with quick navigation</li>
                    </ul>
                </div>
                
                <h3>📊 Key Takeaways Banner</h3>
                <div class="report-card">
                    <div class="report-title">Understanding the Key Takeaways Section</div>
                    <p>Every filtered report displays a <strong>Key Takeaways</strong> banner at the top with critical portfolio metrics:</p>
                    
                    <h4>Metrics Displayed:</h4>
                    <ul>
                        <li><strong>Total Stocks:</strong> Number of stocks in the filtered report</li>
                        <li><strong>Profitable Stocks:</strong> Count and percentage of stocks with Profit/Loss > 0</li>
                        <li><strong>Average P&L%:</strong> Mean profit/loss percentage across all filtered stocks</li>
                        <li><strong>Average RSI:</strong> Mean RSI value (helps identify if group is overbought/oversold)</li>
                        <li><strong>Average Sharpe Ratio:</strong> Mean risk-adjusted return (total volatility basis)</li>
                        <li><strong>Average Sortino Ratio:</strong> Mean downside risk-adjusted return</li>
                    </ul>
                    
                    <h4>💡 How to Use Key Takeaways:</h4>
                    <ul>
                        <li><strong>Quick Assessment:</strong> Instantly see if filtered group is performing well</li>
                        <li><strong>Compare Filters:</strong> Check Key Takeaways across different reports to find best performers</li>
                        <li><strong>Risk Assessment:</strong> High average Sortino/Sharpe = better risk-adjusted group performance</li>
                        <li><strong>Momentum Check:</strong> Average RSI > 50 = bullish momentum, < 50 = bearish momentum</li>
                        <li><strong>Profitability:</strong> % Profitable helps understand success rate of the filter criteria</li>
                    </ul>
                    
                    <div class="highlight">
                        <strong>Example:</strong> A "Sortino > 2" filter showing 23 stocks, 78% profitable, Avg Sortino 2.8 indicates a high-quality group with excellent downside risk management.
                    </div>
                </div>
            </div>
            
            <!-- Main Reports -->
            <div id="main-reports" class="section">
                <h2>📊 Main Portfolio Reports</h2>
                
                {self.create_main_reports_documentation()}
            </div>
            
            <!-- Filtered Reports -->
            <div id="filtered-reports" class="section">
                <h2>🔍 Filtered Analysis Reports</h2>
                
                {self.create_filtered_reports_documentation()}
            </div>
            
            <!-- Technical Indicators -->
            <div id="technical-indicators" class="section">
                <h2>📈 Technical Indicators Explained</h2>
                
                {self.create_technical_indicators_documentation()}
            </div>
            
            <!-- Calculations -->
            <div id="calculations" class="section">
                <h2>🧮 Calculation Methodologies</h2>
                
                {self.create_calculations_documentation()}
            </div>
            
            <!-- Usage Guide -->
            <div id="usage-guide" class="section">
                <h2>💡 Usage Guide & Best Practices</h2>
                
                {self.create_usage_guide()}
            </div>
        
        <div class="footer">
            Portfolio Analysis Documentation &bull; Generated by Portfolio Analysis System
        </div>
</div>
</body>
</html>
        """
    
    def create_main_reports_documentation(self) -> str:
        """Create documentation for main portfolio reports"""
        return """
        <div class="report-card special">
            <div class="report-title">🎯 Portfolio Drag Analysis (Interactive)</div>
            <div class="report-purpose">Identify which stocks are negatively impacting your portfolio performance</div>
            
            <h4>📋 Purpose & Benefits</h4>
            <div class="benefits-list">
                <ul>
                    <li>Identify underperforming stocks that drag down overall returns</li>
                    <li>Interactive deselection to see real-time portfolio improvement</li>
                    <li>Comprehensive drawdown analysis for each stock</li>
                    <li>Visual comparison of individual vs portfolio impact</li>
                    <li>Data-driven decision making for portfolio cleanup</li>
                </ul>
            </div>
            
            <h4>🧮 Calculation Logic</h4>
            <div class="logic-section">
                <strong>Helper vs Dragger Classification:</strong>
                <div class="formula">
                    Portfolio_Average_Return = Mean(All_Stock_Returns)
                    
                    If Stock_Return >= Portfolio_Average → 🟢 HELPER
                       Outperformance = Stock_Return - Portfolio_Average
                    
                    If Stock_Return < Portfolio_Average → 🔴 DRAGGER
                       Underperformance = Portfolio_Average - Stock_Return
                </div>
                
                <p><strong>🟢 HELPER:</strong> Stock outperforming portfolio average - pulling portfolio UP</p>
                <p><strong>🔴 DRAGGER:</strong> Stock underperforming portfolio average - pulling portfolio DOWN</p>
                
                <p><em>Note: Classification is relative to portfolio average. A profitable stock can still be a DRAGGER if it underperforms the average.</em></p>
                
                <strong>Return Calculation:</strong>
                <div class="formula">
                    Stock_Return_% = ((Current_Price - Hold_Price) / Hold_Price) × 100
                </div>
                
                <strong>Portfolio Impact Calculation:</strong>
                <div class="formula">
                    Impact = Portfolio_Return_Without_Stock - Portfolio_Return_With_Stock
                </div>
                <p><strong>Positive Impact:</strong> Removing this stock would improve portfolio performance (DRAGGER)</p>
                <p><strong>Negative Impact:</strong> Removing this stock would hurt portfolio performance (HELPER)</p>
                
                <strong>Drawdown Metrics:</strong>
                <div class="formula">
                    Max_Drawdown = Min((Price_t - Rolling_Max_Price_t) / Rolling_Max_Price_t) × 100
                    Current_Drawdown = ((Current_Price - Recent_Peak_Price) / Recent_Peak_Price) × 100
                    From_52W_High = ((Current_Price - 52W_High) / 52W_High) × 100 (negative = below high)
                    From_52W_Low = ((Current_Price - 52W_Low) / 52W_Low) × 100 (positive = above low)
                </div>
            </div>
            
            <h4>📊 How to Use</h4>
            <p>1. <strong>Review Classification:</strong> Identify Helpers (outperformers) vs Draggers (underperformers)</p>
            <p>2. <strong>Analyze Performance Gap:</strong> Check outperformance/underperformance scores</p>
            <p>3. <strong>Interactive Deselection:</strong> Click stock legends to see real-time portfolio recalculation</p>
            <p>4. <strong>Action on Draggers:</strong> Focus on stocks underperforming by >5% (action required)</p>
            <p>5. <strong>Monitor Helpers:</strong> Consider increasing allocation to strong helpers (>10% outperformance)</p>
            <p>6. <strong>Drawdown Assessment:</strong> Review drawdown metrics for additional risk context</p>
            
            <h4>🎯 Recommendation Thresholds</h4>
            <ul>
                <li><strong>Action Required:</strong> Underperformance > 5% - Consider reducing/exiting</li>
                <li><strong>Watch List:</strong> Underperformance 2-5% - Monitor closely</li>
                <li><strong>Strong Helper:</strong> Outperformance > 10% - Consider increasing allocation</li>
            </ul>
        </div>
        
        <div class="report-card optimization">
            <div class="report-title">🚀 Portfolio Optimization & Risk Management</div>
            <div class="report-purpose">Maximize returns while minimizing risks using Modern Portfolio Theory</div>
            
            <h4>📋 Purpose & Benefits</h4>
            <div class="benefits-list">
                <ul>
                    <li>Optimal weight allocation using Sharpe ratio maximization</li>
                    <li>Multiple allocation strategies comparison</li>
                    <li>Comprehensive risk metrics analysis</li>
                    <li>Intelligent rebalancing suggestions</li>
                    <li><strong>🔗 NEW: Correlation Heatmap</strong> - Visual identification of false diversification</li>
                    <li><strong>⚡ NEW: Portfolio Beta & Stress Test</strong> - Market crash scenario analysis</li>
                    <li>Risk-adjusted performance evaluation</li>
                </ul>
            </div>
            
            <h4>🔗 Correlation Heatmap Analysis</h4>
            <div class="benefits-list">
                <strong>What It Shows:</strong> Visual correlation matrix showing how stocks move together
                <ul>
                    <li>🟢 <strong>Green (High Positive >0.7):</strong> Stocks move together - Risk! False diversification</li>
                    <li>⚪ <strong>White/Gray (~0):</strong> Stocks move independently - True diversification</li>
                    <li>🔴 <strong>Red (Negative <-0.3):</strong> Stocks move opposite - Good hedge</li>
                </ul>
                <strong>Use Case:</strong> If TCS, Infosys, HCL Tech all show >0.9 correlation, they act as ONE position. Reduce correlated holdings.
            </div>
            
            <h4>⚡ Portfolio Beta & Stress Test</h4>
            <div class="benefits-list">
                <strong>Portfolio Beta:</strong> Weighted average of stock betas vs market benchmark
                <ul>
                    <li>🛡️ <strong>Beta < 0.8:</strong> Defensive - Less volatile than market</li>
                    <li>⚖️ <strong>Beta = 1.0:</strong> Neutral - Moves with market</li>
                    <li>📈 <strong>Beta 1.0-1.5:</strong> Aggressive - More volatile than market</li>
                    <li>⚠️ <strong>Beta > 1.5:</strong> Very Aggressive - Significantly more volatile</li>
                </ul>
                <strong>Stress Test Scenarios:</strong> Shows expected portfolio moves for 6 market scenarios (-20% to +20%)
                <br><strong>Use Case:</strong> If market falls 10% and portfolio expected to fall 15%, Beta = 1.5. Use for position sizing & stop-losses.
            </div>
            
            <h4>🧮 Calculation Logic</h4>
            <div class="logic-section">
                <strong>Modern Portfolio Theory Optimization:</strong>
                <div class="formula">
                    Maximize: Sharpe_Ratio = (Portfolio_Return - Risk_Free_Rate) / Portfolio_Volatility
                    Subject to: Sum(Weights) = 1, Weights >= 0, Max_Weight <= 30%
                </div>
                
                <strong>Risk Metrics:</strong>
                <div class="formula">
                    Volatility = Std_Dev(Daily_Returns) * sqrt(252)
                    Beta = Covariance(Stock, Portfolio) / Variance(Portfolio)
                    VaR_95 = 5th_Percentile(Daily_Returns)
                    Sharpe_Ratio = (Mean_Return - Risk_Free_Rate) / Volatility
                </div>
                
                <strong>Alternative Allocation Strategies:</strong>
                <ul>
                    <li><strong>Equal Weight:</strong> 1/N allocation for each stock</li>
                    <li><strong>Risk Parity:</strong> Inverse volatility weighting</li>
                    <li><strong>Momentum:</strong> Based on recent performance</li>
                    <li><strong>Value:</strong> Based on distance from 52-week high</li>
                    <li><strong>Low Volatility:</strong> Favor lower volatility stocks</li>
                </ul>
            </div>
            
            <h4>📊 How to Use</h4>
            <p>1. Review the optimized allocation suggestions</p>
            <p>2. Compare different allocation strategies</p>
            <p>3. Analyze risk metrics table for individual stock assessment</p>
            <p>4. Follow rebalancing suggestions for risk reduction</p>
            <p>5. Monitor correlation matrix for diversification opportunities</p>
        </div>
        
        <div class="report-card">
            <div class="report-title">📋 Comprehensive Portfolio Report</div>
            <div class="report-purpose">Complete portfolio overview with performance metrics and technical analysis</div>
            
            <h4>📋 Purpose & Benefits</h4>
            <div class="benefits-list">
                <ul>
                    <li>Complete portfolio performance overview</li>
                    <li>Individual stock analysis with technical indicators</li>
                    <li>Risk metrics and allocation breakdown</li>
                    <li>Historical performance visualization</li>
                    <li>Profit/Loss analysis with projections</li>
                </ul>
            </div>
            
            <h4>🧮 Key Components</h4>
            <ul>
                <li><strong>Performance Summary:</strong> Total returns, volatility, Sharpe ratio</li>
                <li><strong>Holdings Analysis:</strong> Individual stock breakdown with metrics</li>
                <li><strong>Risk Assessment:</strong> Portfolio-level risk analysis</li>
                <li><strong>Technical Analysis:</strong> Charts and indicator analysis</li>
                <li><strong>Allocation Review:</strong> Current vs optimal allocation</li>
            </ul>
        </div>
        
        <!-- NEW Analytics Reports -->
        <div class="report-card" style="border-left-color:#FF9800">
            <div class="report-title">🎯 Composite Stock Scorer & Signal Engine</div>
            <div class="report-purpose">Scores every stock 0-100 and generates Buy/Hold/Sell signals with confidence stars</div>
            
            <h4>📋 Scoring Categories (20 pts each, total 100)</h4>
            <div class="benefits-list">
                <ul>
                    <li><strong>Relative Strength (20 pts):</strong> RS value vs benchmark + rank within portfolio</li>
                    <li><strong>Trend (20 pts):</strong> CMP position relative to WEMA21, WEMA30, DSMA50, DSMA200</li>
                    <li><strong>Momentum (20 pts):</strong> Minervini Stage classification + Trend Template score + daily change</li>
                    <li><strong>Risk (20 pts):</strong> Sharpe Ratio, Sortino Ratio, low volatility</li>
                    <li><strong>Value/Volume (20 pts):</strong> 52-week position, DMA extension, relative volume</li>
                </ul>
            </div>
            
            <h4>📊 Signal Logic</h4>
            <div class="logic-section">
                <div class="formula">
                    Strong Buy: Score ≥ 75 AND RS > 0 AND above WEMA21 AND Sharpe > 0.5<br>
                    Buy: Score ≥ 60 AND Stage 1 or 2 AND (RS > 0 OR TT ≥ 4)<br>
                    Sell: Score < 40<br>
                    Strong Sell: Score < 25 AND Sharpe < 0 AND below all MAs<br>
                    Hold: Everything else
                </div>
                <p>Confidence (★ to ★★★★★) reflects how many categories agree with the signal direction.</p>
            </div>
        </div>
        
        <div class="report-card" style="border-left-color:#58a6ff">
            <div class="report-title">📊 Minervini Stage Analysis</div>
            <div class="report-purpose">Classifies stocks into 4-stage cycle (Mark Minervini) and evaluates 8-point Trend Template</div>
            
            <h4>📍 4 Stages of a Stock Cycle</h4>
            <div class="benefits-list">
                <ul>
                    <li><strong>Stage 1 — Basing:</strong> Price consolidating near SMA200, MAs flattening. Watch for breakout. Score contribution: Low</li>
                    <li><strong>Stage 2 — Advancing:</strong> Bullish MA stack (SMA50 > SMA150 > SMA200), strong trend. <em>BUY ZONE</em>. Score: High</li>
                    <li><strong>Stage 3 — Topping:</strong> MAs converging, price below SMA50, momentum fading. Take profits. Score: Minimal</li>
                    <li><strong>Stage 4 — Declining:</strong> Bearish MA stack, price below all MAs. <em>EXIT/AVOID</em>. Score: Zero</li>
                </ul>
            </div>
            
            <h4>📋 8-Point Trend Template (TT Score 0–8)</h4>
            <div class="logic-section">
                <div class="formula">
                    1. Price > SMA150 AND Price > SMA200<br>
                    2. SMA150 > SMA200<br>
                    3. SMA200 trending up ≥1 month (slope > 0%)<br>
                    4. SMA50 > SMA150 AND SMA50 > SMA200<br>
                    5. Price > SMA50<br>
                    6. Price ≥25% above 52-week Low<br>
                    7. Price within 25% of 52-week High<br>
                    8. RS > 0 (outperforming NIFTY 50)
                </div>
                <p>TT Score 7+/8 = strongest setups. TT Score 6+/8 = strong Stage 2. Score drives Momentum category in Composite Scorer.</p>
            </div>
            
            <h4>📈 Stage → Momentum Score Mapping</h4>
            <ul>
                <li><strong>Stage 2, TT ≥7:</strong> +10 pts (full trend template — top momentum)</li>
                <li><strong>Stage 2, TT ≥6:</strong> +8 pts (strong stage 2)</li>
                <li><strong>Stage 2, TT <6:</strong> +6 pts (early stage 2)</li>
                <li><strong>Stage 1, TT ≥5:</strong> +4 pts (potential breakout)</li>
                <li><strong>Stage 1, TT <5:</strong> +2 pts (deep basing)</li>
                <li><strong>Stage 3:</strong> +1 pt (topping — losing momentum)</li>
                <li><strong>Stage 4:</strong> +0 pts (declining — no momentum credit)</li>
            </ul>
        </div>
        
        <div class="report-card" style="border-left-color:#4CAF50">
            <div class="report-title">🏥 Portfolio Health Dashboard</div>
            <div class="report-purpose">Traffic-light health diagnostics with concentration risk and momentum health</div>
            
            <h4>📋 How Health Score Works</h4>
            <div class="benefits-list">
                <ul>
                    <li><strong>Green (≥ 65):</strong> Healthy portfolio — majority outperforming, good risk-adjusted returns</li>
                    <li><strong>Yellow (40-64):</strong> Mixed health — some concerns need monitoring</li>
                    <li><strong>Red (< 40):</strong> Needs attention — multiple risk factors present</li>
                </ul>
            </div>
            
            <h4>📊 Metrics Tracked</h4>
            <ul>
                <li><strong>Concentration Risk:</strong> Herfindahl-Hirschman Index (HHI), top-3 allocation %</li>
                <li><strong>Momentum Health:</strong> % above WEMA21, % above DSMA200, % with positive RS</li>
                <li><strong>Risk Alerts:</strong> Stocks with negative Sharpe, high drawdown, average Sortino</li>
            </ul>
        </div>
        
        <div class="report-card" style="border-left-color:#f44336">
            <div class="report-title">🚨 Alert Conditions Report</div>
            <div class="report-purpose">Scans portfolio for critical threshold breaches requiring immediate attention</div>
            
            <h4>📋 Alert Types (7 categories)</h4>
            <div class="benefits-list">
                <ul>
                    <li><strong>Stage 4 — Declining (Critical):</strong> Bearish MA stack, downtrend confirmed. Exit immediately</li>
                    <li><strong>Stage 3 — Topping (Warning):</strong> Distribution phase, MAs converging. Take profits</li>
                    <li><strong>Stage 2 — Prime Uptrend (Info):</strong> Full Trend Template (7+/8). Strong buy setup</li>
                    <li><strong>MA Crossovers:</strong> CMP within 2% of WEMA21 or DSMA200</li>
                    <li><strong>High Drawdown:</strong> 52wHCh% < -30%</li>
                    <li><strong>Volume Spikes:</strong> Relative Volume ≥ 3x average</li>
                    <li><strong>Risk Deterioration:</strong> Both Sharpe and Sortino negative</li>
                </ul>
            </div>
            
            <h4>⚡ Severity Levels</h4>
            <ul>
                <li><strong>🔴 Critical:</strong> Immediate action required (RSI extremes, high drawdown)</li>
                <li><strong>🟡 Warning:</strong> Monitor closely (MA crossovers, risk deterioration)</li>
                <li><strong>🔵 Info:</strong> Awareness items (contrarian opportunities)</li>
            </ul>
        </div>
        
        <div class="report-card" style="border-left-color:#FF5722">
            <div class="report-title">📊 Performance Bar Chart Report</div>
            <div class="report-purpose">Visual comparison of stock returns across 5 time periods with gainers/losers breakdown</div>
            
            <h4>📋 Purpose & Benefits</h4>
            <div class="benefits-list">
                <ul>
                    <li>Horizontal green/red bars for 1W%, 1M%, 3M%, 6M%, 1Y% returns per stock</li>
                    <li>Summary cards: gainers/losers count, best/worst performer per period</li>
                    <li>Average returns table across all periods</li>
                    <li>Quick-sort buttons to rank by any period</li>
                    <li>Includes Minervini Stage, Signal, and Swing_Trend columns for context</li>
                </ul>
            </div>
            
            <h4>📊 How to Use</h4>
            <p>1. <strong>Identify momentum:</strong> Stocks green across all periods = strong sustained trend</p>
            <p>2. <strong>Spot reversals:</strong> Green in 1W/1M but red in 6M/1Y = potential turnaround</p>
            <p>3. <strong>Find laggards:</strong> Red across all periods = consider exit</p>
            <p>4. <strong>Sort by period:</strong> Click period buttons to find best performers per timeframe</p>
        </div>
        
        <div class="report-card" style="border-left-color:#2196F3">
            <div class="report-title">📈 Performance Trend Tracker</div>
            <div class="report-purpose">Tracks portfolio metrics across runs to show improvement or deterioration trends</div>
            
            <h4>📋 What Gets Tracked Each Run</h4>
            <div class="benefits-list">
                <ul>
                    <li>Total P&L and portfolio return %</li>
                    <li>Average Composite Score, RSI, Sharpe Ratio</li>
                    <li>Signal distribution (buy/sell/hold counts)</li>
                    <li>Stock count</li>
                </ul>
            </div>
            
            <h4>📊 Trend Charts</h4>
            <ul>
                <li><strong>P&L Trajectory:</strong> Line chart of P&L and return % over time</li>
                <li><strong>Score Evolution:</strong> Composite score trend with fill area</li>
                <li><strong>RSI & Sharpe Trends:</strong> Dual-axis chart showing momentum and risk-adjusted return trends</li>
            </ul>
            <p>Data is stored in <code>performance_history.json</code> and accumulates over up to 365 runs.</p>
        </div>
        """
    
    def create_filtered_reports_documentation(self) -> str:
        """Create documentation for filtered reports"""
        return """
        <p>The filtered reports system provides 57+ pre-configured filters to analyze your portfolio from different perspectives. Each filter applies specific criteria to identify stocks matching particular technical or fundamental conditions. The master index shows stock count badges next to each filter link.</p>
        
        <h3>📊 Columns Displayed in All Filtered Reports</h3>
        
        <div class="report-card">
            <div class="report-title">Standard Columns Reference</div>
            <p>All filtered reports display the following columns (when available in data):</p>
            
            <div class="calculation-table">
                <thead>
                    <tr>
                        <th>Column</th>
                        <th>Description</th>
                        <th>Format</th>
                        <th>Interpretation</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Symbol</strong></td>
                        <td>Stock ticker symbol</td>
                        <td>Text (e.g., RELIANCE.NS)</td>
                        <td>Unique stock identifier</td>
                    </tr>
                    <tr>
                        <td><strong>CMP</strong></td>
                        <td>Current Market Price</td>
                        <td>₹123.45</td>
                        <td>Latest trading price</td>
                    </tr>
                    <tr>
                        <td><strong>Daily_Change_%</strong></td>
                        <td>Today's price change percentage</td>
                        <td>2.50% (green), -1.20% (red)</td>
                        <td>Intraday momentum indicator</td>
                    </tr>
                    <tr>
                        <td><strong>WEMA21</strong></td>
                        <td>21-period Weighted EMA</td>
                        <td>₹120.00</td>
                        <td>Short-term trend level</td>
                    </tr>
                    <tr>
                        <td><strong>WEMA30</strong></td>
                        <td>30-period Weighted EMA</td>
                        <td>₹118.50</td>
                        <td>Medium-term trend level</td>
                    </tr>
                    <tr>
                        <td><strong>52wH / 52wL</strong></td>
                        <td>52-week High and Low prices</td>
                        <td>₹150.00 / ₹80.00</td>
                        <td>Trading range boundaries</td>
                    </tr>
                    <tr>
                        <td><strong>52wHCh%</strong></td>
                        <td>% from 52-week high</td>
                        <td>-15.50% (typically negative)</td>
                        <td>Negative = below high, -5% = near high</td>
                    </tr>
                    <tr>
                        <td><strong>52wLCh%</strong></td>
                        <td>% from 52-week low</td>
                        <td>45.20% (typically positive)</td>
                        <td>Positive = above low, 5% = near low</td>
                    </tr>
                    <tr>
                        <td><strong>DSMA50</strong></td>
                        <td>50-day Displaced SMA</td>
                        <td>₹122.00</td>
                        <td>Intermediate support/resistance</td>
                    </tr>
                    <tr>
                        <td><strong>DSMA200</strong></td>
                        <td>200-day Displaced SMA</td>
                        <td>₹110.00</td>
                        <td>Long-term trend baseline</td>
                    </tr>
                    <tr>
                        <td><strong>RSI</strong></td>
                        <td>Relative Strength Index (14)</td>
                        <td>65.40 (red if >70, green if <30)</td>
                        <td>>70 overbought, <30 oversold</td>
                    </tr>
                    <tr>
                        <td><strong>RS</strong></td>
                        <td>Relative Strength vs benchmark (NIFTY 50)</td>
                        <td>7.23 (green if >0, red if <0)</td>
                        <td>>0 outperforming by N percentage points, <0 underperforming. Typical range: -20 to +30</td>
                    </tr>
                    <tr>
                        <td><strong>Standard_Deviation</strong></td>
                        <td>Daily volatility percentage</td>
                        <td>2.50%</td>
                        <td>>3% high volatility, <1% low volatility</td>
                    </tr>
                    <tr>
                        <td><strong>Sharpe_Ratio</strong></td>
                        <td>Risk-adjusted returns (total volatility)</td>
                        <td>1.25</td>
                        <td>>1 good, >2 excellent, <0 poor</td>
                    </tr>
                    <tr>
                        <td><strong>Sortino_Ratio</strong></td>
                        <td>Risk-adjusted returns (downside risk only)</td>
                        <td>1.85</td>
                        <td>>1 good, >2 excellent, <0 poor, typically higher than Sharpe</td>
                    </tr>
                    <tr>
                        <td><strong>Profit/Loss</strong></td>
                        <td>Current position P/L in rupees</td>
                        <td>₹15,234 (green if profit)</td>
                        <td>Actual gain/loss on position</td>
                    </tr>
                    <tr>
                        <td><strong>Percentage_Allocation</strong></td>
                        <td>Portfolio weight percentage</td>
                        <td>8.50%</td>
                        <td>>20% concentration risk, <5% minimal impact</td>
                    </tr>
                    <tr>
                        <td><strong>Relative_Volume</strong></td>
                        <td>Today's volume / 20-day avg</td>
                        <td>2.50 (orange if ≥2.0, red if ≥3.0)</td>
                        <td>≥2.0 high spike, ≥3.0 extreme spike</td>
                    </tr>
                    <tr>
                        <td><strong>Week_Avg_Volume</strong></td>
                        <td>Last 5 days average volume</td>
                        <td>1,234,567 (comma-formatted)</td>
                        <td>Current week trading activity level</td>
                    </tr>
                    <tr>
                        <td><strong>Month_Avg_Volume</strong></td>
                        <td>Last 21 days average volume</td>
                        <td>985,432 (comma-formatted)</td>
                        <td>Monthly baseline for comparison</td>
                    </tr>
                    <tr>
                        <td><strong>Volume_Threshold_2x</strong></td>
                        <td>2x monthly average volume</td>
                        <td>1,970,864 (comma-formatted)</td>
                        <td>Threshold for detecting gradual buildup</td>
                    </tr>
                    <tr>
                        <td><strong>Week_Threshold_Ratio</strong></td>
                        <td>Week avg / (2x Month avg)</td>
                        <td>0.63 or 1.15 (orange if >1.2, red if >1.5)</td>
                        <td>>1.0 buildup, >1.2 strong, >1.5 surge</td>
                    </tr>
                    <tr>
                        <td><strong>DMA200_Extension_Pct</strong></td>
                        <td>% above/below 200-day DMA</td>
                        <td>35.20% (green if positive)</td>
                        <td>>30% overextended, <-20% oversold</td>
                    </tr>
                    <tr>
                        <td><strong>Stage</strong></td>
                        <td>Minervini stage (1–4)</td>
                        <td>2 (green), 4 (red)</td>
                        <td>1=Basing, 2=Advancing (buy), 3=Topping (sell), 4=Declining (exit)</td>
                    </tr>
                    <tr>
                        <td><strong>TT_Score</strong></td>
                        <td>Trend Template score (0–8)</td>
                        <td>7/8</td>
                        <td>6+=Strong Stage 2, 7+=Elite setup</td>
                    </tr>
                    <tr>
                        <td><strong>Signal</strong></td>
                        <td>Buy/Hold/Sell recommendation</td>
                        <td>Strong Buy ★★★★★</td>
                        <td>Composite score + stage + RS driven. Stars = confidence (1–5)</td>
                    </tr>
                    <tr>
                        <td><strong>Composite_Score</strong></td>
                        <td>Overall stock score (0–100)</td>
                        <td>78</td>
                        <td>≥75 Strong Buy zone, ≥60 Buy zone, <40 Sell zone, <25 Strong Sell</td>
                    </tr>
                    <tr>
                        <td><strong>Swing_Trend</strong></td>
                        <td>HH/HL swing pattern</td>
                        <td>Bullish / Bearish / Weakening / Topping</td>
                        <td>Bullish=HH+HL, Bearish=no HH+no HL, Weakening=HL only, Topping=HH only</td>
                    </tr>
                    <tr>
                        <td><strong>1W% / 1M% / 3M% / 6M% / 1Y%</strong></td>
                        <td>Period returns (5/21/63/126/252 trading days)</td>
                        <td>3.50% (green) / -2.10% (red)</td>
                        <td>Multi-timeframe momentum. Green across all = sustained trend</td>
                    </tr>
                </tbody>
            </div>
            
            <h4>💡 Column Availability Note:</h4>
            <p>Not all columns appear in every report - only columns with data for the filtered stocks are displayed. Volume columns (Relative_Volume, Week_Avg_Volume, Month_Avg_Volume, Volume_Threshold_2x, Week_Threshold_Ratio) and DMA200_Extension_Pct provide critical insights for volume-based and trend extension analysis. The Week_Threshold_Ratio uses a 2x monthly average threshold to detect gradual volume buildup during the current week.</p>
        </div>
        
        <h3>📊 Technical Analysis Filters</h3>
        
        <div class="report-card">
            <div class="report-title">RSI-Based Filters</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>RSI Below 50:</strong> Stocks with momentum below neutral</li>
                <li><strong>RSI Above 50:</strong> Stocks with positive momentum</li>
                <li><strong>Oversold (RSI < 30):</strong> Potentially undervalued stocks</li>
                <li><strong>Overbought (RSI > 70):</strong> Potentially overvalued stocks</li>
            </ul>
            
            <div class="logic-section">
                <strong>RSI Calculation:</strong>
                <div class="formula">
                    RSI = 100 - (100 / (1 + RS))
                    RS = Average_Gain / Average_Loss (over 14 periods)
                </div>
            </div>
            
            <h4>📊 How to Use:</h4>
            <p><strong>Oversold stocks:</strong> Consider for buying opportunities</p>
            <p><strong>Overbought stocks:</strong> Consider for profit-taking</p>
            <p><strong>RSI trends:</strong> Identify momentum shifts</p>
        </div>
        
        <div class="report-card">
            <div class="report-title">52-Week High/Low Analysis</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>52wHCh% > -10%/-20%/-30%:</strong> Stocks near 52-week highs</li>
                <li><strong>52wLCh% < 10%/20%/30%:</strong> Stocks near 52-week lows</li>
                <li><strong>Near 52-Week High (within 5%/10%):</strong> Momentum leaders</li>
                <li><strong>Near 52-Week Low (within 5%/10%):</strong> Potential value plays</li>
            </ul>
            
            <div class="logic-section">
                <strong>Calculation Logic:</strong>
                <div class="formula">
                    52wHCh% = (Current_Price - 52W_High) / 52W_High * 100
                    52wLCh% = (Current_Price - 52W_Low) / 52W_Low * 100
                </div>
                <p><strong>Note:</strong> 52wHCh% is typically negative (down from high)</p>
                <p><strong>Note:</strong> 52wLCh% is typically positive (up from low)</p>
            </div>
            
            <h4>📊 Analysis Benefits:</h4>
            <p><strong>Near Highs:</strong> Identify momentum stocks and breakout candidates</p>
            <p><strong>Near Lows:</strong> Find potential value opportunities and oversold conditions</p>
            <p><strong>Range Analysis:</strong> Understand price positioning within 52-week range</p>
        </div>
        
        <h3>📈 Moving Average Filters</h3>
        
        <div class="report-card">
            <div class="report-title">WEMA (Weighted Exponential Moving Average)</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>Above/Below WEMA21:</strong> Short-term trend direction</li>
                <li><strong>Above/Below WEMA30:</strong> Medium-term trend direction</li>
                <li><strong>Bullish Trend:</strong> Above both WEMA21 & WEMA30</li>
                <li><strong>Bearish Trend:</strong> Below both WEMA21 & WEMA30</li>
            </ul>
            
            <div class="logic-section">
                <strong>WEMA Calculation:</strong>
                <div class="formula">
                    WEMA = Σ(Price_i * Weight_i) / Σ(Weight_i)
                    Weight_i = i (where i = 1, 2, 3, ..., period)
                </div>
            </div>
        </div>
        
        <div class="report-card">
            <div class="report-title">DSMA (Displaced Simple Moving Average)</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>Above/Below DSMA50:</strong> Medium-term trend with 10-day displacement</li>
                <li><strong>Above/Below DSMA200:</strong> Long-term trend with 25-day displacement</li>
            </ul>
            
            <div class="logic-section">
                <strong>DSMA Calculation:</strong>
                <div class="formula">
                    DSMA50 = SMA50 shifted forward by 10 days
                    DSMA200 = SMA200 shifted forward by 25 days
                </div>
                <p>Displacement helps reduce lag and provide earlier signals</p>
            </div>
        </div>
        
        <h3>📊 Relative Strength Filters</h3>
        
        <div class="report-card">
            <div class="report-title">RS (Relative Strength) Analysis</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>Strong RS (> 0.0):</strong> Outperforming benchmark</li>
                <li><strong>Weak RS (< 0.0):</strong> Underperforming benchmark</li>
                <li><strong>Very Strong RS (> 10.0):</strong> Significantly outperforming (top momentum)</li>
                <li><strong>Strong RS (> 3.0):</strong> Solidly outperforming</li>
                <li><strong>Weak RS (< -3.0):</strong> Solidly underperforming</li>
                <li><strong>Very Weak RS (< -10.0):</strong> Significantly underperforming</li>
            </ul>
            
            <div class="logic-section">
                <strong>RS Calculation (Period-Based with Sliding Sub-Window Smoothing):</strong>
                <div class="formula">
                    Step 1: Fetch stock and benchmark (NIFTY 50) prices for rs_calculation_period (default 90 days)
                    Step 2: stock_return = (stock_end / stock_start - 1) × 100
                             bench_return = (bench_end / bench_start - 1) × 100
                    Step 3: RS = stock_return - bench_return (percentage points)
                    
                    Smoothing (sliding sub-windows, period = rs_smoothing_period, default 14):
                    For each sub-window i of size (total_days - smoothing_period + 1):
                        RS_i = stock_return[window_i] - bench_return[window_i]
                    Smoothed_RS = Mean(RS_1, RS_2, ..., RS_N)
                </div>
                <p>Benchmark: NIFTY 50 (^NSEI) by default. RS is in percentage-point scale (typical range: -20 to +30).</p>
                <p><strong>Key:</strong> RS > 0 means stock outperformed benchmark over the period; RS = 7.0 means stock beat NIFTY by 7 percentage points.</p>
            </div>
        </div>
        
        <h3>🎯 Minervini Stage Filters</h3>
        
        <div class="report-card">
            <div class="report-title">Minervini Stage-Based Filters (6 filters)</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>Stage 1 — Basing:</strong> Stocks consolidating near SMA200, potential breakout candidates</li>
                <li><strong>Stage 2 — Advancing:</strong> Bullish MA stack, strong uptrend — BUY ZONE</li>
                <li><strong>Stage 3 — Topping:</strong> MAs converging, momentum fading — take profits</li>
                <li><strong>Stage 4 — Declining:</strong> Bearish MA stack — EXIT/AVOID</li>
                <li><strong>Trend Template 6+/8:</strong> Strong Stage 2 setups meeting 6+ of 8 Minervini criteria</li>
                <li><strong>Trend Template 7+/8:</strong> Elite setups meeting 7+ of 8 criteria (highest conviction)</li>
            </ul>
            <div class="logic-section">
                <strong>Stage Classification Logic:</strong>
                <div class="formula">
                    Stage 2 (Advancing): SMA50 > SMA150 > SMA200 AND Price > SMA50 AND SMA200 slope > 0
                    Stage 4 (Declining): SMA50 < SMA150 < SMA200 AND Price < SMA50
                    Stage 3 (Topping): Price < SMA50 AND NOT Stage 4
                    Stage 1 (Basing): Everything else (consolidation)
                </div>
            </div>
        </div>
        
        <h3>📐 Higher High / Higher Low Swing Filters</h3>
        
        <div class="report-card">
            <div class="report-title">HH/HL Swing Pattern Filters (4 filters)</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>Higher High &amp; Higher Low (Bullish Swing):</strong> Both HH and HL confirmed — strongest bullish setup</li>
                <li><strong>Higher Low Only (Accumulation):</strong> HL without HH — accumulation phase, potential breakout</li>
                <li><strong>Lower Low (Bearish — Exit Signal):</strong> No HL — bearish structure, exit signal</li>
                <li><strong>Higher High Only (Topping Risk):</strong> HH without HL — higher highs on lower lows = divergence risk</li>
            </ul>
            <div class="logic-section">
                <strong>Swing Detection (5-bar pivot, 11-bar window):</strong>
                <div class="formula">
                    Swing High: Bar whose High is the highest in ±5 bars (11-bar window)
                    Swing Low: Bar whose Low is the lowest in ±5 bars (11-bar window)
                    Scans last 63 trading days (~3 months) for swing points
                    
                    HH = last pivot high > prior pivot high
                    HL = last pivot low > prior pivot low
                    
                    Swing_Trend:
                      Bullish  = HH AND HL (higher highs + higher lows)
                      Topping  = HH AND NOT HL (new highs but lower lows)
                      Weakening = NOT HH AND HL (higher lows but no new highs)
                      Bearish  = NOT HH AND NOT HL (lower highs + lower lows)
                </div>
            </div>
        </div>
        
        <h3>📊 Period Return Filters</h3>
        
        <div class="report-card">
            <div class="report-title">Multi-Period Return Columns</div>
            <p>All filtered reports include 5 period-return columns calculated using trading-day lookback:</p>
            <ul>
                <li><strong>1W%:</strong> 5 trading days return</li>
                <li><strong>1M%:</strong> 21 trading days return</li>
                <li><strong>3M%:</strong> 63 trading days return</li>
                <li><strong>6M%:</strong> 126 trading days return</li>
                <li><strong>1Y%:</strong> 252 trading days return</li>
            </ul>
            <div class="logic-section">
                <div class="formula">
                    Period_Return% = (Current_Price / Price_N_days_ago - 1) × 100
                </div>
            </div>
        </div>
        
        <h3>💰 Performance & Risk Filters</h3>
        
        <div class="report-card">
            <div class="report-title">Performance Analysis</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>In Profit:</strong> Positive current returns</li>
                <li><strong>In Loss:</strong> Negative current returns</li>
                <li><strong>Positive/Negative Sharpe Ratio:</strong> Risk-adjusted performance (total volatility)</li>
                <li><strong>Positive/Negative Sortino Ratio:</strong> Downside risk-adjusted performance</li>
                <li><strong>Sortino > 1, > 2:</strong> Good/excellent downside risk-adjusted returns</li>
                <li><strong>Sortino < 1:</strong> Poor downside risk-adjusted returns</li>
            </ul>
        </div>
        
        <div class="report-card">
            <div class="report-title">Volatility Analysis</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>High Volatility (>3%):</strong> Higher risk/reward stocks</li>
                <li><strong>Low Volatility (<1%):</strong> Lower risk, stable stocks</li>
            </ul>
            
            <div class="logic-section">
                <strong>Volatility Calculation:</strong>
                <div class="formula">
                    Volatility = Standard_Deviation(Daily_Returns) * 100
                </div>
            </div>
        </div>
        
        <h3>📊 Volume Analysis Filters (NEW)</h3>
        
        <div class="report-card">
            <div class="report-title">Volume-Based Filters</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>High Relative Volume (>= 2.0x):</strong> Today's volume vs 20-day average - detects immediate single-day spikes</li>
                <li><strong>Week Volume > 2x Month Average:</strong> Last 5-day average vs 2x monthly (21-day) average - identifies gradual volume buildup during current week</li>
                <li><strong>Price Extended from 200 DMA (> 30%):</strong> Price significantly above long-term average</li>
            </ul>
            
            <div class="logic-section">
                <strong>Volume Spike Detection Formulas:</strong>
                <div class="formula">
                    <strong>Relative Volume:</strong>
                    = Current_Day_Volume / 20_Day_Avg_Volume
                    (Detects single-day volume spikes)
                    
                    <strong>Week vs 2x Month Threshold Ratio:</strong>
                    = Last_5_Days_Avg_Volume / (2 × 21_Day_Avg_Volume)
                    (Ratio > 1.0 means current week volume exceeds 2x monthly baseline - indicates gradual buildup)
                    
                    <strong>Price Extension:</strong>
                    = (Current_Price - DMA200) / DMA200 × 100
                </div>
            </div>
            
            <h4>📊 Use Cases:</h4>
            <p><strong>High Relative Volume:</strong> Breakouts, news events, institutional buying (single-day spikes)</p>
            <p><strong>Week > 2x Month Average (Ratio > 1.0):</strong> Gradual accumulation during current week, building market interest, early trend detection (sensitive to recent changes)</p>
            <p><strong>Price Extended from DMA:</strong> Overbought conditions, profit-taking zones, mean reversion setups</p>
            
            <h4>📊 Volume Columns in Reports:</h4>
            <ul>
                <li><strong>Relative_Volume:</strong> Current day volume / 20-day average. Values ≥2.0 indicate high single-day spikes, ≥3.0 extreme spikes</li>
                <li><strong>Week_Avg_Volume:</strong> Average daily volume over last 5 trading days (formatted with comma separators)</li>
                <li><strong>Month_Avg_Volume:</strong> Average daily volume over last 21 trading days (monthly baseline, formatted with comma separators)</li>
                <li><strong>Volume_Threshold_2x:</strong> 2x the monthly average volume - the threshold for detecting gradual buildup (formatted with comma separators)</li>
                <li><strong>Week_Threshold_Ratio:</strong> Week average / (2x Month average). >1.0 = gradual buildup, >1.2 = strong buildup, >1.5 = significant surge</li>
                <li><strong>DMA200_Extension_Pct:</strong> Percentage price is above/below 200-day DMA. >30% indicates overextension risk</li>
            </ul>
        </div>
        
        <h3>🎯 Combined Analysis Filters</h3>
        
        <div class="report-card">
            <div class="report-title">Multi-Criteria Filters</div>
            <h4>Available Filters:</h4>
            <ul>
                <li><strong>Above All Moving Averages:</strong> Strong uptrend (CMP > WEMA21, WEMA30, DSMA50, DSMA200)</li>
                <li><strong>Below All Moving Averages:</strong> Strong downtrend (CMP < all MAs)</li>
                <li><strong>Bullish Trend:</strong> Above WEMA21 & WEMA30</li>
                <li><strong>Bearish Trend:</strong> Below WEMA21 & WEMA30</li>
            </ul>
            
            <h4>📊 Strategy:</h4>
            <p><strong>Above All MAs:</strong> Strongest trend confirmation, consider holding or adding</p>
            <p><strong>Below All MAs:</strong> Weakest position, consider reducing exposure</p>
        </div>
        """
    
    def create_technical_indicators_documentation(self) -> str:
        """Create documentation for technical indicators"""
        return """
        <div class="section">
            <h2>📖 Beginner's Guide to Key Metrics</h2>
            <p>This section provides easy-to-understand explanations of important financial metrics used throughout the system.</p>
            
            <div class="report-card">
                <div class="report-title">Beta (β) - Market Sensitivity</div>
                <p><strong>What it is:</strong> Beta measures how much a stock moves compared to the overall market (NIFTY 50 index).</p>
                
                <h4>📊 What it means:</h4>
                <ul>
                    <li><strong>Beta = 1.0:</strong> Stock moves exactly like the market</li>
                    <li><strong>Beta > 1.0</strong> (e.g., 1.5): Stock is more volatile. If market goes up 10%, stock may go up 15%</li>
                    <li><strong>Beta < 1.0</strong> (e.g., 0.7): Stock is less volatile. If market goes up 10%, stock may go up 7%</li>
                    <li><strong>Negative Beta:</strong> Stock moves opposite to market (rare)</li>
                </ul>
                
                <h4>💡 How to use it:</h4>
                <ul>
                    <li>High beta stocks (>1.2) are good for aggressive growth but higher risk</li>
                    <li>Low beta stocks (<0.8) are good for conservative, defensive portfolios</li>
                    <li>Use beta to understand your portfolio's market sensitivity</li>
                </ul>
            </div>
            
            <div class="report-card">
                <div class="report-title">Sharpe & Sortino Ratio - Risk-Adjusted Returns</div>
                <p><strong>Sharpe Ratio:</strong> Measures return per unit of total volatility (both up and down movements).</p>
                <p><strong>Sortino Ratio:</strong> Measures return per unit of downside risk only (focuses on harmful volatility).</p>
                
                <h4>📊 What it means:</h4>
                <ul>
                    <li><strong>Sharpe > 2:</strong> Excellent risk-adjusted returns (considers all volatility)</li>
                    <li><strong>Sharpe 1-2:</strong> Very good returns for the risk taken</li>
                    <li><strong>Sharpe 0-1:</strong> Acceptable but could be better</li>
                    <li><strong>Sharpe < 0:</strong> Losing money or returns don't justify the risk</li>
                </ul>
                
                <h4>📊 Sortino Ratio Thresholds:</h4>
                <ul>
                    <li><strong>Sortino > 2:</strong> Excellent - minimal downside risk relative to returns</li>
                    <li><strong>Sortino > 1:</strong> Good - positive return with acceptable downside risk</li>
                    <li><strong>Sortino < 1:</strong> Poor - returns don't justify downside risk</li>
                    <li><strong>Sortino < 0:</strong> Negative - losing money with downside risk</li>
                    <li><strong>Note:</strong> Sortino is usually higher than Sharpe because it only penalizes harmful (downside) volatility</li>
                </ul>
                
                <h4>💡 How to use it:</h4>
                <ul>
                    <li><strong>Sharpe Ratio:</strong> Use when both upside and downside volatility concern you equally</li>
                    <li><strong>Sortino Ratio:</strong> Use when you only care about downside risk (prefer this for most cases)</li>
                    <li>Compare stocks: Higher Sortino = better downside-risk-adjusted performance</li>
                    <li>Target Sortino > 1 for long-term holdings (indicates positive return with manageable downside)</li>
                    <li>Sortino > 2 indicates exceptional performance with minimal downside risk</li>
                </ul>
                
                <div class="formula">
                    Sharpe Formula: (Stock Return - Risk-Free Rate) / Total Volatility
                    <br>
                    Sortino Formula: (Stock Return - Risk-Free Rate) / Downside Deviation
                    <br>
                    Risk-Free Rate: 6% (default)
                </div>
            </div>
            
            <div class="report-card">
                <div class="report-title">Volatility (Standard Deviation)</div>
                <p><strong>What it is:</strong> Volatility measures how much a stock's price jumps around.</p>
                
                <h4>📊 What it means:</h4>
                <ul>
                    <li><strong>Low (<15%):</strong> Stable, predictable price movements (large-cap stocks)</li>
                    <li><strong>Medium (15-30%):</strong> Moderate price swings (most mid-cap stocks)</li>
                    <li><strong>High (>30%):</strong> Large unpredictable price swings (small-cap, momentum stocks)</li>
                </ul>
                
                <h4>💡 How to use it:</h4>
                <ul>
                    <li>High volatility = Higher risk AND higher potential returns</li>
                    <li>Low volatility = More stable, suitable for conservative investors</li>
                    <li>Use to size positions: Smaller position size for high-volatility stocks</li>
                </ul>
            </div>
            
            <div class="report-card">
                <div class="report-title">Maximum Drawdown</div>
                <p><strong>What it is:</strong> Maximum Drawdown shows the biggest peak-to-trough decline in stock price.</p>
                
                <h4>📊 What it means:</h4>
                <ul>
                    <li><strong>-10%:</strong> Small decline, good resilience</li>
                    <li><strong>-20%:</strong> Moderate decline, acceptable for most stocks</li>
                    <li><strong>-30% to -50%:</strong> Large decline, consider if it's worth the risk</li>
                    <li><strong>>-50%:</strong> Severe decline, very risky</li>
                </ul>
                
                <h4>💡 How to use it:</h4>
                <ul>
                    <li>Shows the "worst case" loss you might have experienced</li>
                    <li>Use to assess if you can stomach potential losses</li>
                    <li>Compare to your risk tolerance before investing</li>
                </ul>
            </div>
            
            <div class="report-card">
                <div class="report-title">RSI (Relative Strength Index)</div>
                <p><strong>What it is:</strong> RSI measures if a stock is "overbought" (too expensive) or "oversold" (too cheap).</p>
                
                <h4>📊 What it means:</h4>
                <ul>
                    <li><strong>RSI > 70:</strong> Overbought - might be overpriced, potential for pullback</li>
                    <li><strong>RSI 30-70:</strong> Neutral zone - normal trading range</li>
                    <li><strong>RSI < 30:</strong> Oversold - might be underpriced, potential for bounce</li>
                    <li><strong>RSI 14:</strong> Uses 14-day calculation period (standard)</li>
                </ul>
                
                <h4>💡 How to use it:</h4>
                <ul>
                    <li><strong>Buy signals:</strong> RSI < 30 (oversold stocks may bounce back)</li>
                    <li><strong>Sell signals:</strong> RSI > 70 (overbought stocks may correct)</li>
                    <li>Don't use RSI alone - combine with other indicators</li>
                    <li>RSI works best for range-bound stocks, not strong trends</li>
                </ul>
            </div>
            
            <div class="report-card">
                <div class="report-title">Allocation & P/L Percentages</div>
                <p><strong>What they are:</strong> Key metrics for portfolio management.</p>
                
                <h4>📊 Profit/Loss Percentage:</h4>
                <ul>
                    <li><strong>Positive %:</strong> Making profit</li>
                    <li><strong>Negative %:</strong> In loss</li>
                    <li><strong>>20%:</strong> Consider taking some profits</li>
                    <li><strong><-20%:</strong> Re-evaluate if investment thesis is broken</li>
                </ul>
                
                <h4>📊 Allocation Percentage:</h4>
                <ul>
                    <li><strong>>20%:</strong> High concentration - significant risk if stock falls</li>
                    <li><strong>10-20%:</strong> Moderate allocation - balanced approach</li>
                    <li><strong>5-10%:</strong> Standard position size</li>
                    <li><strong><5%:</strong> Small position - limited impact on portfolio</li>
                </ul>
                
                <h4>💡 How to use them:</h4>
                <ul>
                    <li>Set profit targets (e.g., sell 50% at +30%)</li>
                    <li>Set stop-losses (e.g., exit at -15%)</li>
                    <li>Avoid >25% in any single stock (diversification risk)</li>
                    <li>Rebalance periodically to maintain target allocations</li>
                </ul>
            </div>
        </div>
        
        <p>The system employs 20+ technical indicators to provide comprehensive market analysis. Each indicator serves a specific purpose in understanding price action, momentum, and trend direction.</p>
        
        <div class="calculation-table">
            <thead>
                <tr>
                    <th>Indicator</th>
                    <th>Purpose</th>
                    <th>Calculation</th>
                    <th>Interpretation</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>RSI (14)</strong></td>
                    <td>Momentum oscillator</td>
                    <td>100 - (100 / (1 + RS))</td>
                    <td>< 30: Oversold, > 70: Overbought</td>
                </tr>
                <tr>
                    <td><strong>WEMA 21/30</strong></td>
                    <td>Weighted trend analysis</td>
                    <td>Σ(Price × Weight) / Σ(Weight)</td>
                    <td>Price above: Bullish, below: Bearish</td>
                </tr>
                <tr>
                    <td><strong>DSMA 50/200</strong></td>
                    <td>Displaced trend analysis</td>
                    <td>SMA shifted forward</td>
                    <td>Reduces lag, earlier signals</td>
                </tr>
                <tr>
                    <td><strong>Relative Strength</strong></td>
                    <td>Benchmark comparison</td>
                    <td>Stock_Period_Return - Bench_Period_Return (%-pts, smoothed by sliding sub-windows)</td>
                    <td>> 0: Outperforming (e.g., RS=7 means beat NIFTY by 7pp)</td>
                </tr>
                <tr>
                    <td><strong>Sharpe Ratio</strong></td>
                    <td>Risk-adjusted returns</td>
                    <td>(Return - Risk Free) / Volatility</td>
                    <td>Higher values indicate better risk-adjusted performance</td>
                </tr>
                <tr>
                    <td><strong>Beta</strong></td>
                    <td>Market sensitivity</td>
                    <td>Covariance(Stock, Market) / Variance(Market)</td>
                    <td>> 1: More volatile than market, < 1: Less volatile</td>
                </tr>
                <tr>
                    <td><strong>Maximum Drawdown</strong></td>
                    <td>Worst-case loss</td>
                    <td>Max(Peak - Trough) / Peak</td>
                    <td>Lower values indicate better downside protection</td>
                </tr>
                <tr>
                    <td><strong>Volatility</strong></td>
                    <td>Price variability</td>
                    <td>Std Dev(Returns) × √252</td>
                    <td>Annualized standard deviation of returns</td>
                </tr>
                <tr>
                    <td><strong>VaR 95%</strong></td>
                    <td>Value at Risk</td>
                    <td>5th percentile of daily returns</td>
                    <td>Expected loss in worst 5% of cases</td>
                </tr>
                <tr>
                    <td><strong>OBV</strong></td>
                    <td>Volume momentum</td>
                    <td>Cumulative volume based on price direction</td>
                    <td>Confirms price trends with volume</td>
                </tr>
                <tr>
                    <td><strong>A/D Line</strong></td>
                    <td>Accumulation/Distribution</td>
                    <td>Based on price position within range</td>
                    <td>Measures buying/selling pressure</td>
                </tr>
            </tbody>
        </div>
        
        <h3>📊 Indicator Categories</h3>
        
        <div class="report-card">
            <div class="report-title">Trend Indicators</div>
            <p><strong>Purpose:</strong> Identify direction and strength of price trends</p>
            <ul>
                <li><strong>WEMA 21/30:</strong> Short to medium-term trend direction</li>
                <li><strong>DSMA 50/200:</strong> Medium to long-term trend analysis</li>
                <li><strong>Relative Strength:</strong> Trend relative to benchmark</li>
            </ul>
        </div>
        
        <div class="report-card">
            <div class="report-title">Momentum Indicators</div>
            <p><strong>Purpose:</strong> Measure rate of price change and momentum shifts</p>
            <ul>
                <li><strong>RSI:</strong> Overbought/oversold conditions</li>
                <li><strong>OBV:</strong> Volume-based momentum</li>
                <li><strong>Price Rate of Change:</strong> Momentum measurement</li>
            </ul>
        </div>
        
        <div class="report-card">
            <div class="report-title">Risk Indicators</div>
            <p><strong>Purpose:</strong> Assess and quantify investment risk</p>
            <ul>
                <li><strong>Volatility:</strong> Price variability measurement</li>
                <li><strong>Maximum Drawdown:</strong> Worst-case scenario analysis</li>
                <li><strong>Beta:</strong> Market sensitivity measurement</li>
                <li><strong>VaR:</strong> Potential loss quantification</li>
            </ul>
        </div>
        
        <div class="report-card">
            <div class="report-title">Performance Indicators</div>
            <p><strong>Purpose:</strong> Evaluate risk-adjusted performance</p>
            <ul>
                <li><strong>Sharpe Ratio:</strong> Risk-adjusted returns</li>
                <li><strong>Alpha:</strong> Excess return vs benchmark</li>
                <li><strong>Information Ratio:</strong> Active return per unit of risk</li>
            </ul>
        </div>
        """
    
    def create_calculations_documentation(self) -> str:
        """Create detailed calculations documentation"""
        return """
        <h3>🔢 Core Calculation Methodologies</h3>
        
        <div class="report-card">
            <div class="report-title">Portfolio Return Calculations</div>
            
            <h4>Daily Portfolio Returns (Equally Weighted)</h4>
            <div class="logic-section">
                <div class="formula">
                    Portfolio_Return_t = Σ(Weight_i × Stock_Return_i_t)
                    Weight_i = 1/N (where N = number of stocks)
                    Stock_Return_i_t = (Price_i_t - Price_i_(t-1)) / Price_i_(t-1)
                </div>
            </div>
            
            <h4>Cumulative Returns</h4>
            <div class="logic-section">
                <div class="formula">
                    Cumulative_Return = Π(1 + Daily_Return_t) - 1
                    Percentage_Return = Cumulative_Return × 100
                </div>
            </div>
        </div>
        
        <div class="report-card">
            <div class="report-title">Risk Metrics Calculations</div>
            
            <h4>Volatility (Annualized)</h4>
            <div class="logic-section">
                <div class="formula">
                    Daily_Volatility = Standard_Deviation(Daily_Returns)
                    Annualized_Volatility = Daily_Volatility × √252
                    Percentage_Volatility = Annualized_Volatility × 100
                </div>
                <p><strong>Note:</strong> 252 represents typical trading days per year</p>
            </div>
            
            <h4>Maximum Drawdown</h4>
            <div class="logic-section">
                <div class="formula">
                    Running_Max_t = Max(Cumulative_Return_1, ..., Cumulative_Return_t)
                    Drawdown_t = (Cumulative_Return_t - Running_Max_t) / Running_Max_t
                    Max_Drawdown = Min(Drawdown_1, ..., Drawdown_T) × 100
                </div>
            </div>
            
            <h4>Sharpe Ratio</h4>
            <div class="logic-section">
                <div class="formula">
                    Sharpe_Ratio = (Annualized_Return - Risk_Free_Rate) / Annualized_Volatility
                    Risk_Free_Rate = 6% (configurable)
                    Annualized_Return = Mean(Daily_Returns) × 252
                </div>
            </div>
            
            <h4>Beta Calculation</h4>
            <div class="logic-section">
                <div class="formula">
                    Beta = Covariance(Stock_Returns, Benchmark_Returns) / Variance(Benchmark_Returns)
                    Covariance = E[(Stock_Return - E[Stock_Return]) × (Benchmark_Return - E[Benchmark_Return])]
                </div>
            </div>
        </div>
        
        <div class="report-card">
            <div class="report-title">52-Week Analysis Calculations</div>
            
            <h4>52-Week High/Low Percentages</h4>
            <div class="logic-section">
                <div class="formula">
                    52W_High = Max(High_Prices_Last_252_Days)
                    52W_Low = Min(Low_Prices_Last_252_Days)
                    
                    52wHCh% = (Current_Price - 52W_High) / 52W_High × 100
                    52wLCh% = (Current_Price - 52W_Low) / 52W_Low × 100
                </div>
                
                <p><strong>Interpretation:</strong></p>
                <ul>
                    <li><strong>52wHCh%:</strong> Negative values indicate how far below 52-week high</li>
                    <li><strong>52wLCh%:</strong> Positive values indicate how far above 52-week low</li>
                </ul>
            </div>
        </div>
        
        <div class="report-card">
            <div class="report-title">Modern Portfolio Theory Optimization</div>
            
            <h4>Objective Function</h4>
            <div class="logic-section">
                <div class="formula">
                    Maximize: Sharpe_Ratio = (μ_p - r_f) / σ_p
                    
                    Where:
                    μ_p = Σ(w_i × μ_i) (Portfolio Expected Return)
                    σ_p = √(w^T × Σ × w) (Portfolio Volatility)
                    r_f = Risk-free rate
                    w_i = Weight of asset i
                    Σ = Covariance matrix
                </div>
            </div>
            
            <h4>Constraints</h4>
            <div class="logic-section">
                <div class="formula">
                    Σ(w_i) = 1 (Weights sum to 100%)
                    w_i ≥ 0 (No short selling)
                    w_i ≤ 0.30 (Maximum 30% in any single asset)
                </div>
            </div>
            
            <h4>Alternative Allocation Strategies</h4>
            <div class="logic-section">
                <strong>Risk Parity:</strong>
                <div class="formula">
                    w_i = (1/σ_i) / Σ(1/σ_j) × 100%
                </div>
                
                <strong>Momentum Strategy:</strong>
                <div class="formula">
                    w_i = Max(0, Return_i) / Σ(Max(0, Return_j)) × 100%
                </div>
                
                <strong>Value Strategy:</strong>
                <div class="formula">
                    w_i = Max(0, -52wHCh%_i) / Σ(Max(0, -52wHCh%_j)) × 100%
                </div>
            </div>
        </div>
        """
    
    def create_usage_guide(self) -> str:
        """Create usage guide and best practices"""
        return """
        <h3>🎯 Getting Started</h3>
        
        <div class="highlight">
            <strong>Recommended Workflow:</strong>
            <ol>
                <li>Start with the <strong>Comprehensive Portfolio Report</strong> for overall health check</li>
                <li>Use <strong>Portfolio Drag Analysis</strong> to identify underperformers</li>
                <li>Review <strong>Portfolio Optimization</strong> for rebalancing guidance</li>
                <li>Apply <strong>Filtered Reports</strong> for specific analysis needs</li>
                <li>Monitor regularly and adjust based on market conditions</li>
            </ol>
        </div>
        
        <h3>📊 Analysis Best Practices</h3>
        
        <div class="report-card">
            <div class="report-title">Daily/Weekly Monitoring</div>
            <ul>
                <li><strong>Portfolio Drag Analysis:</strong> Check for new draggers weekly</li>
                <li><strong>RSI Filters:</strong> Monitor overbought/oversold conditions</li>
                <li><strong>52-Week Analysis:</strong> Track stocks approaching highs/lows</li>
                <li><strong>Trend Filters:</strong> Monitor WEMA/DSMA crossovers</li>
            </ul>
        </div>
        
        <div class="report-card">
            <div class="report-title">Monthly Review</div>
            <ul>
                <li><strong>Portfolio Optimization:</strong> Review and implement rebalancing suggestions</li>
                <li><strong>Risk Metrics:</strong> Assess portfolio risk profile changes</li>
                <li><strong>Performance Analysis:</strong> Compare actual vs optimized performance</li>
                <li><strong>Correlation Analysis:</strong> Review diversification effectiveness</li>
            </ul>
        </div>
        
        <div class="report-card">
            <div class="report-title">Quarterly Assessment</div>
            <ul>
                <li><strong>Strategy Comparison:</strong> Evaluate different allocation strategies</li>
                <li><strong>Risk-Return Profile:</strong> Assess if portfolio matches objectives</li>
                <li><strong>Benchmark Analysis:</strong> Compare relative strength performance</li>
                <li><strong>Position Sizing:</strong> Review individual stock weightings</li>
            </ul>
        </div>
        
        <h3>⚠️ Important Considerations</h3>
        
        <div class="report-card">
            <div class="report-title">Limitations & Disclaimers</div>
            <ul>
                <li><strong>Historical Data:</strong> Past performance doesn't guarantee future results</li>
                <li><strong>Market Conditions:</strong> Strategies may perform differently in various market environments</li>
                <li><strong>Risk Tolerance:</strong> Consider your personal risk tolerance before implementing suggestions</li>
                <li><strong>Transaction Costs:</strong> Consider trading costs when implementing changes</li>
                <li><strong>Tax Implications:</strong> Consult tax advisor for rebalancing implications</li>
                <li><strong>Diversification:</strong> Don't rely solely on quantitative analysis</li>
            </ul>
        </div>
        
        <h3>🔧 Configuration & Customization</h3>
        
        <div class="report-card">
            <div class="report-title">Adjustable Parameters</div>
            <ul>
                <li><strong>RSI Periods:</strong> Default 14, adjustable for sensitivity</li>
                <li><strong>Moving Average Periods:</strong> WEMA 21/30, DSMA 50/200</li>
                <li><strong>Risk-Free Rate:</strong> Default 6%, adjustable for market conditions</li>
                <li><strong>Correlation Threshold:</strong> Default 0.7 for diversification alerts</li>
                <li><strong>Maximum Position Size:</strong> Default 30% for optimization</li>
                <li><strong>Volatility Thresholds:</strong> High >3%, Low <1%</li>
            </ul>
            
            <p><strong>To modify settings:</strong> Use <code>python config_util.py set &lt;setting&gt; &lt;value&gt;</code></p>
        </div>
        
        <h3>📱 Interactive Features</h3>
        
        <div class="report-card">
            <div class="report-title">Chart Interactions</div>
            <ul>
                <li><strong>Legend Clicking:</strong> Toggle individual stocks on/off</li>
                <li><strong>Double-Click Legend:</strong> Isolate single stock view</li>
                <li><strong>Zoom & Pan:</strong> Detailed chart exploration</li>
                <li><strong>Hover Data:</strong> Detailed metrics on hover</li>
                <li><strong>Real-time Recalculation:</strong> Instant portfolio updates</li>
            </ul>
        </div>
        
        <h3>🔄 Report Integration</h3>
        
        <div class="report-card">
            <div class="report-title">Cross-Report Analysis</div>
            <p><strong>Integrated Workflow:</strong></p>
            <ol>
                <li><strong>Identify Issues:</strong> Use Drag Analysis to find problems</li>
                <li><strong>Understand Context:</strong> Use Filtered Reports for deeper analysis</li>
                <li><strong>Find Solutions:</strong> Use Optimization for rebalancing guidance</li>
                <li><strong>Implement Changes:</strong> Use specific filter reports for execution</li>
                <li><strong>Monitor Progress:</strong> Return to main reports for tracking</li>
            </ol>
        </div>
        """


def generate_documentation_report():
    """Generate the documentation report"""
    generator = ReportDocumentationGenerator()
    return generator.generate_documentation()


if __name__ == "__main__":
    print("Report Documentation Generator loaded successfully!")
