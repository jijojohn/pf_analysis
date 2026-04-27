#!/usr/bin/env python3
"""
Master Report Generator
Creates a comprehensive master report page with links to all sub-reports
"""

import os
import re
import html
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional
import glob
from config_manager import get_config
from report_style import get_base_css, get_how_it_works

class MasterReportGenerator:
    """Generate master report page with all sub-reports"""
    
    def __init__(self):
        self.config = get_config()
        self.reports_dir = self.config.get_setting("system_settings.reports_directory", "reports")
        self.today = datetime.now().strftime("%Y%m%d")
        
    def get_report_files(self) -> Dict[str, List[str]]:
        """Get all report files organized by type"""
        report_files = {
            "comprehensive_datasets": [],
            "filtered_reports": [],
            "portfolio_reports": [],
            "analytics_reports": [],
            "other_reports": []
        }
        
        if not os.path.exists(self.reports_dir):
            return report_files
            
        # Get all HTML, CSV, and Excel files from reports directory (not just today's)
        html_files = glob.glob(f"{self.reports_dir}/*.html")
        csv_files = glob.glob(f"{self.reports_dir}/*.csv")
        xlsx_files = glob.glob(f"{self.reports_dir}/*.xlsx")
        
        for file_path in html_files:
            filename = os.path.basename(file_path)
            # Skip zero-size files
            if os.path.getsize(file_path) == 0:
                continue
            
            # New analytics reports
            if any(tag in filename for tag in ("portfolio_health", "alert_conditions", "performance_trend", "minervini_stage_analysis", "performance_bar_chart")):
                report_files["analytics_reports"].append(filename)
            elif "filtered_report" in filename:
                report_files["filtered_reports"].append(filename)
            elif ("portfolio_report" in filename or "portfolio_drag_analysis" in filename or 
                  "portfolio_optimization" in filename or "reports_documentation" in filename):
                report_files["portfolio_reports"].append(filename)
            else:
                report_files["other_reports"].append(filename)
                
        for file_path in csv_files + xlsx_files:
            filename = os.path.basename(file_path)
            # Skip zero-size files
            if os.path.getsize(file_path) == 0:
                continue
                
            if "comprehensive_dataset" in filename:
                report_files["comprehensive_datasets"].append(filename)
            else:
                report_files["other_reports"].append(filename)
                
        # Sort all lists (most recent first)
        for key in report_files:
            report_files[key].sort(reverse=True)
            
        return report_files
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary from comprehensive dataset"""
        try:
            # Look for the most recent comprehensive dataset CSV file
            csv_files = glob.glob(f"{self.reports_dir}/comprehensive_dataset_*.csv")
            if csv_files:
                # Sort by date (most recent first)
                csv_files.sort(reverse=True)
                csv_file = csv_files[0]  # Use the most recent file
                
                df = pd.read_csv(csv_file)
                
                total_stocks = len(df)
                strong_rs_count = len(df[df['RS'] > 0]) if 'RS' in df.columns else 0
                weak_rs_count = len(df[df['RS'] < 0]) if 'RS' in df.columns else 0
                
                # Check for RSI column - could be 'RSI' or 'RSI_14'
                rsi_col = 'RSI' if 'RSI' in df.columns else 'RSI_14' if 'RSI_14' in df.columns else None
                high_rsi_count = len(df[df[rsi_col] > 70]) if rsi_col else 0
                low_rsi_count = len(df[df[rsi_col] < 30]) if rsi_col else 0
                
                # Check for Profit/Loss column
                pl_col = 'Profit/Loss' if 'Profit/Loss' in df.columns else 'P&L' if 'P&L' in df.columns else None
                profitable_count = len(df[df[pl_col] > 0]) if pl_col else 0
                
                avg_rs = df['RS'].mean() if 'RS' in df.columns else 0
                avg_rsi = df[rsi_col].mean() if rsi_col else 0
                total_profit_loss = df[pl_col].sum() if pl_col else 0
                
                return {
                    "total_stocks": total_stocks,
                    "strong_rs_count": strong_rs_count,
                    "weak_rs_count": weak_rs_count,
                    "high_rsi_count": high_rsi_count,
                    "low_rsi_count": low_rsi_count,
                    "profitable_count": profitable_count,
                    "avg_rs": avg_rs,
                    "avg_rsi": avg_rsi,
                    "total_profit_loss": total_profit_loss
                }
        except Exception as e:
            print(f"Error getting portfolio summary: {e}")
            import traceback
            traceback.print_exc()
            
        return {}
    
    def _read_report_head(self, filename: str) -> str:
        """Read first 20KB of a report HTML file (cached)."""
        if not hasattr(self, '_head_cache'):
            self._head_cache = {}
        if filename not in self._head_cache:
            try:
                filepath = os.path.join(self.reports_dir, filename)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    self._head_cache[filename] = f.read(20480)
            except Exception:
                self._head_cache[filename] = ""
        return self._head_cache[filename]

    def _get_filtered_count(self, filename: str) -> Optional[int]:
        """Extract stock count from a filtered report HTML file."""
        head = self._read_report_head(filename)
        m = re.search(r'Showing (\d+) stocks?\b', head)
        if m:
            return int(m.group(1))
        return None

    def format_filter_name(self, filename: str) -> str:
        """Extract readable filter name from HTML <title> tag, with filename fallback."""
        head = self._read_report_head(filename)
        m = re.search(r'<title>Filtered Portfolio Report - (.+?)</title>', head)
        if m:
            return m.group(1)
        # Fallback: reverse the _safe_filename() transformation
        name = filename.replace("filtered_report_", "").replace(f"_{self.today}.html", "")
        name = (name
                .replace("__greater_than__", " > ")
                .replace("__less_than__", " < ")
                .replace("__equals__", " = ")
                .replace("__and__", " & ")
                .replace("__or__", "/")
                .replace("pct", "%")
                .replace("_", " "))
        # Restore decimals: "3 0" → "3.0"
        name = re.sub(r'(\d+) (\d+)', r'\1.\2', name)
        return name.strip()
    
    def generate_master_report(self) -> str:
        """Generate master report HTML"""
        config = self.config
        benchmark_config = config.get_benchmark_config()
        tech_config = config.get_technical_config()
        
        report_files = self.get_report_files()
        portfolio_summary = self.get_portfolio_summary()
        
        css = get_base_css()
        how_it_works = get_how_it_works("How This Report Works", [
            ("Dashboard Home", "This is your central hub — every report generated by the system is linked here"),
            ("Portfolio Summary", "Key metrics (total stocks, RS strength, RSI, P&amp;L) from the latest comprehensive dataset"),
            ("Report Categories", "Reports are grouped into Datasets, Portfolio Analysis, Analytics &amp; Insights, and Filtered Views"),
            ("Quick Actions", "Download CSV/Excel data or jump to configuration"),
            ("Navigation", "Click any report link to open it; every sub-report links back here"),
        ])
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Analysis Dashboard - {datetime.now().strftime('%B %d, %Y')}</title>
    <style>
    {css}
    .summary-card {{ transition: transform 0.2s ease; }}
    .summary-card:hover {{ transform: translateY(-3px); }}
    .config-info .config-row {{ margin:5px 0; }}
    .drag-analysis-highlight {{ border-color:#f0883e !important; animation:pulse 2.5s infinite; }}
    .optimization-highlight {{ border-color:#3fb950 !important; animation:pulse 2.5s infinite; }}
    .documentation-highlight {{ border-color:#a371f7 !important; animation:pulse 2.5s infinite; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>&#128202; Portfolio Analysis Dashboard</h1>
        <p class="subtitle">Comprehensive Analysis Hub &mdash; {datetime.now().strftime('%B %d, %Y')}</p>

        {how_it_works}
        
        <div class="section">
            <div class="config-info">
                <strong><span class="config-label">&#127919; Analysis Configuration</span></strong><br>
                <div class="config-row"><span class="config-label">Primary Benchmark:</span> {benchmark_config.benchmark_name} ({benchmark_config.primary_benchmark})</div>
                <div class="config-row"><span class="config-label">RS Benchmark:</span> {benchmark_config.rs_benchmark_name} ({benchmark_config.rs_benchmark_index})</div>
                <div class="config-row"><span class="config-label">RS Period:</span> {benchmark_config.rs_calculation_period} days ({benchmark_config.rs_calculation_period//21} months) | <span class="config-label">Smoothing:</span> {benchmark_config.rs_smoothing_period} days</div>
                <div class="config-row"><span class="config-label">Data Retention:</span> {config.get_setting('system_settings.data_retention_years')} years | <span class="config-label">RSI:</span> {tech_config.rsi_period} period (Oversold: {tech_config.rsi_oversold} / Overbought: {tech_config.rsi_overbought})</div>
            </div>
            
            <div class="quick-actions">
                <a href="comprehensive_dataset_{self.today}.csv" class="action-btn">&#128202; Download CSV Data</a>
                <a href="comprehensive_dataset_{self.today}.xlsx" class="action-btn">&#128200; Download Excel Data</a>
                <a href="../config.json" class="action-btn">&#9881; View Configuration</a>
            </div>
        </div>
"""

        # Portfolio Summary Section
        if portfolio_summary:
            html_content += f"""
        <div class="section">
            <h2>&#128200; Portfolio Summary</h2>
            <div class="summary-grid">
                <div class="card">
                    <div class="label">Total Stocks</div>
                    <div class="value">{portfolio_summary.get('total_stocks', 'N/A')}</div>
                </div>
                <div class="card">
                    <div class="label">Strong RS (Outperforming)</div>
                    <div class="value {'positive' if portfolio_summary.get('strong_rs_count', 0) > portfolio_summary.get('weak_rs_count', 0) else 'negative'}">{portfolio_summary.get('strong_rs_count', 'N/A')}</div>
                </div>
                <div class="card">
                    <div class="label">Weak RS (Underperforming)</div>
                    <div class="value {'negative' if portfolio_summary.get('weak_rs_count', 0) > 0 else 'neutral'}">{portfolio_summary.get('weak_rs_count', 0)}</div>
                </div>
                <div class="card">
                    <div class="label">Average RS</div>
                    <div class="value {'positive' if portfolio_summary.get('avg_rs', 0) > 0 else 'negative'}">{portfolio_summary.get('avg_rs', 0):.2f}</div>
                </div>
                <div class="card">
                    <div class="label">Average RSI</div>
                    <div class="value {'positive' if portfolio_summary.get('avg_rsi', 50) > 50 else 'negative'}">{portfolio_summary.get('avg_rsi', 0):.1f}</div>
                </div>
                <div class="card">
                    <div class="label">Total P&amp;L</div>
                    <div class="value {'positive' if portfolio_summary.get('total_profit_loss', 0) > 0 else 'negative'}">&#8377;{portfolio_summary.get('total_profit_loss', 0):,.0f}</div>
                </div>
                <div class="card">
                    <div class="label">Profitable Stocks</div>
                    <div class="value {'positive' if portfolio_summary.get('profitable_count', 0) > portfolio_summary.get('total_stocks', 1) / 2 else 'negative'}">{portfolio_summary.get('profitable_count', 'N/A')}</div>
                </div>
            </div>
        </div>
"""

        # Comprehensive Datasets Section
        if report_files["comprehensive_datasets"]:
            html_content += """
        <div class="section">
            <h2>📊 Comprehensive Datasets</h2>
            <div class="reports-grid">
"""
            for dataset in report_files["comprehensive_datasets"]:
                file_type = "📈 Excel" if dataset.endswith('.xlsx') else "📊 CSV"
                html_content += f"""
                <a href="{dataset}" class="report-link dataset-link">
                    {file_type} Dataset - {dataset.replace('comprehensive_dataset_', '').replace(f'_{self.today}', '').replace('.csv', '').replace('.xlsx', '')}
                </a>
"""
            html_content += """
            </div>
        </div>
"""

        # Portfolio Reports Section
        if report_files["portfolio_reports"]:
            html_content += """
        <div class="section">
            <h2>📋 Portfolio Reports</h2>
            <div class="reports-grid">
"""
            # Sort portfolio reports to prioritize special reports
            sorted_reports = sorted(report_files["portfolio_reports"], 
                                  key=lambda x: (0 if "documentation" in x else 1 if "drag_analysis" in x else 2 if "optimization" in x else 3, x))
            
            for report in sorted_reports:
                if "reports_documentation" in report:
                    report_name = "📚 Complete Documentation & Analysis Guide"
                    extra_class = " documentation-highlight"
                    description = " - Comprehensive guide explaining all reports and methodologies"
                elif "portfolio_drag_analysis" in report:
                    report_name = "🎯 Portfolio Drag Analysis (Interactive)"
                    extra_class = " drag-analysis-highlight"
                    description = " - Identify which stocks are dragging down your portfolio"
                elif "portfolio_optimization" in report:
                    report_name = "🚀 Portfolio Optimization & Risk Management"
                    extra_class = " optimization-highlight"
                    description = " - Maximize returns while minimizing drawdowns"
                else:
                    report_name = self.format_filter_name(report.replace("portfolio_report_", "Portfolio Report "))
                    extra_class = ""
                    description = ""
                
                html_content += f"""
                <a href="{report}" class="report-link portfolio-link{extra_class}">
                    📋 {report_name}{description}
                </a>
"""
            html_content += """
            </div>
        </div>
"""

        # Analytics Reports Section (NEW - Health, Alerts, Performance Trend)
        if report_files.get("analytics_reports"):
            html_content += """
        <div class="section">
            <h2>🧠 Analytics & Insights</h2>
            <p style="color:#8b949e;margin-bottom:15px;">Advanced portfolio scoring, alerts, health diagnostics and performance tracking.</p>
            <div class="reports-grid">
"""
            for report in report_files["analytics_reports"]:
                if "portfolio_health" in report:
                    icon = "🏥"
                    name = "Portfolio Health Dashboard"
                    desc = " — Traffic-light diagnostics, concentration risk, momentum health"
                elif "alert_conditions" in report:
                    icon = "🚨"
                    name = "Alert Conditions Report"
                    desc = " — RSI extremes, MA crossovers, volume spikes, risk deterioration"
                elif "performance_trend" in report:
                    icon = "📈"
                    name = "Performance Trend Tracker"
                    desc = " — P&L trajectory, composite score evolution, signal history"
                elif "minervini_stage_analysis" in report:
                    icon = "📊"
                    name = "Minervini Stage Analysis"
                    desc = " — 4-stage classification, 8-point Trend Template, buy/sell zones"
                elif "performance_bar_chart" in report:
                    icon = "📊"
                    name = "Performance Bar Chart"
                    desc = " — Horizontal period returns (1W, 1M, 3M, 6M, 1Y) for every stock"
                else:
                    icon = "📊"
                    name = report.replace(f"_{self.today}", "").replace(".html", "").replace("_", " ").title()
                    desc = ""
                html_content += f"""
                <a href="{report}" class="report-link portfolio-link" style="border-left:4px solid #ff9800;">
                    {icon} {name}{desc}
                </a>
"""
            html_content += """
            </div>
        </div>
"""

        # Filtered Reports Section
        if report_files["filtered_reports"]:
            html_content += """
        <div class="section">
            <h2>🔍 Interactive Filter Reports</h2>
            <div class="reports-grid">
"""
            for report in report_files["filtered_reports"]:
                filter_name = self.format_filter_name(report)
                icon = "📈" if "Strong" in filter_name else "📉" if "Weak" in filter_name else "🔍"
                count = self._get_filtered_count(report)
                badge = f' <span style="background:#30363d;color:#58a6ff;padding:2px 8px;border-radius:10px;font-size:0.8em;margin-left:6px;">{count}</span>' if count is not None else ''
                safe_name = html.escape(filter_name)
                html_content += f"""
                <a href="{report}" class="report-link">
                    {icon} {safe_name}{badge}
                </a>
"""
            html_content += """
            </div>
        </div>
"""

        # Other Reports Section
        if report_files["other_reports"]:
            html_content += """
        <div class="section">
            <h2>📄 Additional Reports</h2>
            <div class="reports-grid">
"""
            for report in report_files["other_reports"]:
                report_name = report.replace(f"_{self.today}", "").replace(".html", "").replace("_", " ").title()
                html_content += f"""
                <a href="{report}" class="report-link">
                    📄 {report_name}
                </a>
"""
            html_content += """
            </div>
        </div>
"""

        # Footer
        html_content += f"""
        <div class="footer">
            Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} &bull; Portfolio Analysis System v2.0
        </div>
    </div>
</body>
</html>
"""

        return html_content
    
    def save_master_report(self) -> str:
        """Save master report to file"""
        html_content = self.generate_master_report()
        master_report_path = f"{self.reports_dir}/index.html"
        
        with open(master_report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return master_report_path

if __name__ == "__main__":
    generator = MasterReportGenerator()
    report_path = generator.save_master_report()
    print(f"✅ Master report generated: {report_path}")
