# Portfolio Analysis System

**Version:** 3.1 | **Last Updated:** February 2026

A comprehensive stock portfolio analysis system with 55+ filters, Mark Minervini stage analysis, Higher High / Higher Low swing detection, period-return bar charts, composite scoring, and interactive dark-themed HTML reports. Designed for **swing trading and long-term investment analysis**.

---

## Quick Start

```bash
./setup.sh          # First-time setup (creates venv + installs dependencies)
./run.sh            # Full pipeline — data fetch + report generation
./run.sh --serve    # Browse reports at http://localhost:8080/reports/index.html
```

## Running the System

**Always use `run.sh`** — it manages the virtual environment, data freshness, and proper execution order.

```bash
./run.sh                  # Full pipeline (default): verify → fetch → reports
./run.sh --full           # Same as above
./run.sh --reports-only   # Regenerate reports only (skip data fetch)
./run.sh --update-only    # Update data only (no reports)
./run.sh --clean          # Delete old reports + full pipeline
./run.sh --serve [PORT]   # Local web server (default: 8080)
./run.sh --help           # Show help
```

> **Never run Python files directly.** Always use `./run.sh`.

---

## Key Features

| Feature                                | Description                                                                               |
| -------------------------------------- | ----------------------------------------------------------------------------------------- |
| **Mark Minervini Stage Analysis**      | 4-stage classification (Basing → Advancing → Topping → Declining), 8-point Trend Template |
| **Higher High / Higher Low Detection** | Swing-pattern filter: Bullish (HH+HL), Weakening, Topping, Bearish                        |
| **Performance Bar Chart**              | Horizontal 1W/1M/3M/6M/1Y return bars per stock (green = gain, red = loss)                |
| **55+ Pre-configured Filters**         | MA, RS, volume, 52-week, Minervini stage, HH/HL swing filters                             |
| **Composite Scoring (0–100)**          | Across 5 categories: RS, Trend, Momentum (stage-based), Risk, Value/Volume                |
| **Buy/Sell Signals**                   | Strong Buy / Buy / Hold / Sell / Strong Sell with confidence levels                       |
| **Portfolio Optimization**             | Correlation, beta, stress-test, efficient frontier                                        |
| **Health Dashboard**                   | Traffic-light per stock, HHI concentration, momentum health                               |
| **Alert Engine**                       | Critical / Warning / Info — stage changes, MA crossovers, volume spikes                   |
| **Dark Theme**                         | Unified design via `report_style.py`, Plotly dark charts, responsive/mobile-friendly      |
| **Sortable Tables**                    | Frozen headers, context-relevant columns per report                                       |

---

## Architecture & Pipeline

```
run.sh → venv activation → verify_data_freshness.py → update_portfolio_data.py → main_pf_app.py
  STEP 0: cleanup old reports
  STEP 1: load portfolio (config.json → system_settings.portfolio_file via pf_manager.py)
  STEP 2: check data availability (price_cache/*.pkl via data_fetcher.py)
  STEP 3: generate comprehensive dataset (technical_indicators.py)
  STEP 4b: Minervini stage analysis (minervini_analyzer.py)
          + composite scoring (stock_scorer.py)
          + signals (signal_engine.py)
  STEP 5: create Plotly visualizations
  STEP 6: main portfolio report (html_report_generator.py)
  STEP 7: ~57 filtered reports (interactive_filter.py)
  STEP 8: advanced reports
     - pf_drag_analyzer.py        → portfolio_drag_analysis_YYYYMMDD.html
     - pf_optimizer.py            → portfolio_optimization_report_YYYYMMDD.html
     - minervini_analyzer.py      → minervini_stage_analysis_YYYYMMDD.html
     - performance_bar_report.py  → performance_bar_chart_YYYYMMDD.html
     - portfolio_health.py        → portfolio_health_YYYYMMDD.html
     - alert_engine.py            → alert_conditions_YYYYMMDD.html
     - performance_tracker.py     → performance_trend_YYYYMMDD.html
     - report_documentation.py    → reports_documentation_YYYYMMDD.html
  STEP 9: master index (master_report_generator.py → reports/index.html)
```

---

## Module Inventory

| Module                       | Purpose                                                                   |
| ---------------------------- | ------------------------------------------------------------------------- |
| `main_pf_app.py`             | Main orchestrator — 9-step pipeline                                       |
| `technical_indicators.py`    | All indicator calculations; builds comprehensive dataset per stock        |
| `minervini_analyzer.py`      | 4-stage classification, 8-point Trend Template, stage analysis report     |
| `stock_scorer.py`            | Composite scoring (0–100) across 5 categories                             |
| `signal_engine.py`           | Strong Buy / Buy / Hold / Sell / Strong Sell — stage-aware                |
| `html_report_generator.py`   | Main portfolio HTML report with Plotly charts                             |
| `interactive_filter.py`      | 55+ filter criteria; generates per-filter HTML reports                    |
| `performance_bar_report.py`  | Horizontal period-return bar chart for all stocks                         |
| `pf_optimizer.py`            | Correlation, beta, stress-test, efficient-frontier optimization           |
| `pf_drag_analyzer.py`        | Leave-one-out portfolio drag analysis, per-stock drawdown                 |
| `portfolio_health.py`        | Traffic-light health dashboard, HHI concentration                         |
| `alert_engine.py`            | Critical/Warning/Info alerts: stage changes, MA crossovers, volume spikes |
| `performance_tracker.py`     | Persists metrics per run to `performance_history.json`; trend charts      |
| `master_report_generator.py` | Generates `reports/index.html` — central dashboard                        |
| `report_documentation.py`    | Full guide to all reports, indicators, calculations                       |
| `report_style.py`            | Shared dark-theme CSS, sortable-table JS, nav bar, "How It Works" helpers |
| `config_manager.py`          | Loads/manages `config.json` — all configurable thresholds                 |
| `config.json`                | All configurable thresholds and parameters                                |
| `data_fetcher.py`            | Yahoo Finance API with incremental `.pkl` caching                         |
| `update_portfolio_data.py`   | Standalone script to update portfolio + benchmark data                    |
| `pf_manager.py`              | Loads portfolio from Excel, normalizes columns                            |
| `verify_data_freshness.py`   | CLI freshness check used by `run.sh`                                      |
| `smart_data_updater.py`      | Incremental data update logic                                             |

---

## Technical Indicators

### In the Comprehensive Dataset

| Category            | Columns                                                             |
| ------------------- | ------------------------------------------------------------------- |
| **Moving Averages** | WEMA21, WEMA30, DSMA50, DSMA200, SMA50, SMA150, SMA200              |
| **Minervini**       | Stage (1–4), Stage_Name, TT_Score (0–8), Stage_Action, SMA200_Slope |
| **52-Week**         | 52wH, 52wL, 52wHCh%, 52wLCh%                                        |
| **Momentum**        | RSI (14-period, reference only), RS (vs NIFTY 50 benchmark)         |
| **Risk**            | Sharpe Ratio, Sortino Ratio, Standard Deviation                     |
| **Volume**          | OBV, A/D Line, Relative_Volume, Week/Month avg, Volume_Threshold_2x |
| **Extension**       | DMA200_Extension_Pct                                                |
| **Period Returns**  | 1W%, 1M%, 3M%, 6M%, 1Y%                                             |
| **Swing Pattern**   | HH (Higher High), HL (Higher Low), Swing_Trend                      |

### Computed Internally (not in dataset columns)

SMA20, EMA12, EMA26, EMA50, MACD, Bollinger Bands, Stochastic, ATR, Williams %R

---

## Scoring & Signals

### Composite Score (0–100)

Five 20-point categories:

- **Relative Strength (RS):** Outperformance vs NIFTY 50
- **Trend:** MA alignment and slope
- **Momentum:** Minervini stage-based (RSI is reference only, NOT scored)
- **Risk:** Sharpe/Sortino/volatility
- **Value/Volume:** allocation, drawdown, volume buildup

### Signal Engine

| Signal      | Condition                            |
| ----------- | ------------------------------------ |
| Strong Buy  | Stage 1/2, high composite, strong RS |
| Buy         | Stage 1/2, decent score              |
| Hold        | Balanced factors                     |
| Sell        | Stage 3/4, deteriorating metrics     |
| Strong Sell | Stage 4, critical alerts             |

> **Buy signals require Stage 1 or 2.** Stage 3/4 generate bearish factors.

---

## Configuration

All thresholds live in `config.json`:

- `system_settings.portfolio_file` — name of the portfolio Excel file
- `benchmark_settings` — primary benchmark, RS benchmark, calculation period
- `technical_indicators` — RSI, MACD, MA periods
- `filter_thresholds` — RS, 52-week, volume filter thresholds
- `scoring_settings` — 5 × 20 category weights
- `signal_settings` — signal generation thresholds
- `alert_settings` — alert severity thresholds

---

## Report Styling

- All reports use shared `report_style.py` (unified dark theme: body `#0d1117`, text `#c9d1d9`, accent `#58a6ff`)
- Tables: sortable via `onclick="sortTable(this)"`, sticky headers, frozen first column
- Responsive design: `@media` breakpoints at 768px and 480px (mobile-friendly)
- All reports have nav bar linking back to `reports/index.html`
- Reports include "How This Report Works" collapsible section
- Plotly charts: `paper_bgcolor='#161b22'`, `plot_bgcolor='#0d1117'`, `font(color='#c9d1d9')`

---

## File Structure

```
├── run.sh                       # Primary interface (always use this)
├── main_pf_app.py               # Main orchestrator
├── technical_indicators.py      # All indicator calculations
├── minervini_analyzer.py        # Minervini 4-stage + Trend Template
├── stock_scorer.py              # Composite scoring engine
├── signal_engine.py             # Buy/Sell signal generation
├── performance_bar_report.py    # Period-return bar chart report
├── html_report_generator.py     # Main portfolio report
├── interactive_filter.py        # 55+ filtered reports
├── pf_optimizer.py              # Portfolio optimization
├── pf_drag_analyzer.py          # Drag analysis
├── portfolio_health.py          # Health dashboard
├── alert_engine.py              # Alert conditions
├── performance_tracker.py       # Performance trend tracking
├── master_report_generator.py   # index.html generator
├── report_documentation.py      # Documentation report
├── report_style.py              # Shared dark theme CSS/JS
├── config_manager.py            # Configuration management
├── config.json                  # All configurable thresholds
├── data_fetcher.py              # Yahoo Finance data fetcher
├── update_portfolio_data.py     # Data update script
├── pf_manager.py                # Portfolio loader
├── price_cache/                 # Cached price data (.pkl)
└── reports/
    └── index.html               # Master dashboard (start here)
```

---

**Version 3.1** | Portfolio Analysis System
