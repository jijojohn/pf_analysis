## Working agreements (apply to all changes)

- Python: Always create and use a local venv (`./venv`).
  - Preferred: `source venv/bin/activate` (Linux/macOS) or `.\venv\Scripts\activate` (Windows).
  - **Never run Python files directly** — always use `./run.sh` which manages venv automatically.
- Testing: For every feature or bugfix, add/modify tests and run the full suite before proposing changes.
- Use `./run.sh` for all execution. Available modes:
  - `./run.sh` or `./run.sh --full` — Full pipeline (verify → fetch → generate reports)
  - `./run.sh --reports-only` — Regenerate reports with cached data (skip data fetch)
  - `./run.sh --update-only` — Only fetch/update data, no report generation
  - `./run.sh --serve [PORT]` — Start local HTTP server to browse reports (default port: 8080)
  - `./run.sh --clean` — Delete all reports and regenerate from scratch
  - `./run.sh --help` — Show usage
- Keep changes minimal and focused; avoid drive-by refactors unless explicitly requested.
- Documentation-first: If docs are outdated or missing, update `README.md` and the generated `reports_documentation_YYYYMMDD.html` before or along with the change. (There is no `docs/architecture/` folder — all docs live in the root. `SYSTEM_DOCUMENTATION.md` was merged into `README.md` in v3.1.)
- Keep the `run.sh` workflow as the primary interface for running the system.

## Architecture & module inventory

### Pipeline flow (orchestrated by `main_pf_app.py`)

```
run.sh → venv activation → verify_data_freshness.py → update_portfolio_data.py → main_pf_app.py
  STEP 0: cleanup old reports
  STEP 1: load portfolio (config.json → system_settings.portfolio_file via pf_manager.py)
  STEP 2: check data availability (price_cache/*.pkl via data_fetcher.py)
  STEP 3: generate comprehensive dataset (technical_indicators.py)
  STEP 4: Minervini stage analysis (minervini_analyzer.py) + composite scoring (stock_scorer.py) + signals (signal_engine.py)
  STEP 5: create Plotly visualizations
  STEP 6: main portfolio report (html_report_generator.py)
  STEP 7: ~57 filtered reports (interactive_filter.py) — includes 6 Minervini + 4 HH/HL swing filters
  STEP 8: advanced reports
     - pf_drag_analyzer.py → portfolio_drag_analysis_YYYYMMDD.html
     - pf_optimizer.py → portfolio_optimization_report_YYYYMMDD.html
     - minervini_analyzer.py → minervini_stage_analysis_YYYYMMDD.html
     - performance_bar_report.py → performance_bar_chart_YYYYMMDD.html
     - portfolio_health.py → portfolio_health_YYYYMMDD.html
     - alert_engine.py → alert_conditions_YYYYMMDD.html
     - performance_tracker.py → performance_trend_YYYYMMDD.html
     - report_documentation.py → reports_documentation_YYYYMMDD.html
  STEP 9: master index (master_report_generator.py → reports/index.html)
```

### Key modules

| Module                       | Purpose                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `main_pf_app.py`             | Main orchestrator — 9-step pipeline                                                                            |
| `technical_indicators.py`    | All technical indicator calculations; builds comprehensive dataset per stock                                   |
| `html_report_generator.py`   | Main portfolio HTML report with Plotly charts                                                                  |
| `interactive_filter.py`      | ~55+ filter criteria; generates per-filter HTML reports (MA, RS, volume, 52w, Minervini, HH/HL swing)          |
| `stock_scorer.py`            | Composite scoring (0–100) across 5 categories: RS, Trend, Momentum (Minervini stage-based), Risk, Value/Volume |
| `signal_engine.py`           | Strong Buy / Buy / Hold / Sell / Strong Sell signals — stage-aware (Buy requires Stage 1/2)                    |
| `minervini_analyzer.py`      | 4-stage classification, 8-point Trend Template, stage analysis report                                          |
| `pf_optimizer.py`            | Correlation, beta, stress-test, efficient-frontier-style optimization                                          |
| `pf_drag_analyzer.py`        | Leave-one-out portfolio drag analysis, per-stock drawdown                                                      |
| `portfolio_health.py`        | Traffic-light health dashboard, HHI concentration, momentum health                                             |
| `alert_engine.py`            | Critical/Warning/Info alerts: MA crossovers, volume spikes, drawdowns                                          |
| `performance_tracker.py`     | Persists metrics per run to `performance_history.json`; trend charts                                           |
| `master_report_generator.py` | Generates `reports/index.html` — central dashboard linking all sub-reports                                     |
| `report_documentation.py`    | Full guide to all reports, indicators, calculations                                                            |
| `report_style.py`            | Shared dark-theme CSS, sortable-table JS, nav bar, "How It Works" helpers                                      |
| `config_manager.py`          | Loads/manages `config.json` — all configurable thresholds and parameters                                       |
| `data_fetcher.py`            | Yahoo Finance API with incremental .pkl caching in `price_cache/`                                              |
| `update_portfolio_data.py`   | Standalone script to update portfolio + benchmark data                                                         |
| `performance_bar_report.py`  | Horizontal period-return bar chart for all stocks (1W/1M/3M/6M/1Y)                                             |
| `pf_manager.py`              | Loads portfolio from config-driven Excel file, normalizes columns                                              |
| `data_freshness_checker.py`  | Validates data freshness before analysis                                                                       |
| `verify_data_freshness.py`   | CLI freshness check used by `run.sh`                                                                           |
| `smart_data_updater.py`      | Incremental data update logic, used by `data_freshness_checker.py`                                             |

### Technical indicators in the comprehensive dataset

- **Moving averages:** WEMA21, WEMA30, DSMA50, DSMA200, SMA50, SMA150, SMA200
- **Internal only (not in dataset columns):** SMA20, EMA12, EMA26, EMA50, MACD, Bollinger Bands, Stochastic, ATR, Williams %R
- **Minervini:** Stage (1–4), Stage_Name, TT_Score (0–8), Stage_Action, SMA200_Slope
- **52-week:** 52wH, 52wL, 52wHCh%, 52wLCh%
- **Momentum:** RSI (14-period, reference only — NOT used in scoring), RS (vs NIFTY 50 benchmark)
- **Risk:** Sharpe Ratio, Sortino Ratio, Standard Deviation
- **Volume:** OBV, A/D Line, Relative_Volume, Week/Month avg, Volume_Threshold_2x, Week_Threshold_Ratio
- **Extension:** DMA200_Extension_Pct
- **Period Returns:** 1W%, 1M%, 3M%, 6M%, 1Y% (trading-day lookback: 5/21/63/126/252)
- **Swing Pattern:** HH (Higher High), HL (Higher Low), Swing_Trend (Bullish/Bearish/Weakening/Topping)

### Report styling conventions

- All reports use shared `report_style.py` (unified dark theme: body `#0d1117`, text `#c9d1d9`, accent `#58a6ff`)
- Tables: sortable via `onclick="sortTable(this)"`, sticky headers, frozen first column
- Responsive design: `@media` breakpoints at 768px and 480px (mobile-friendly)
- All reports have nav bar linking back to `reports/index.html`
- Reports include "How This Report Works" collapsible section
- Plotly charts use dark theme: `template='plotly_dark'`, `paper_bgcolor='#161b22'`, `plot_bgcolor='#0d1117'`, `font(color='#c9d1d9')`, `hovermode='closest'` with crosshair spikes, legend `bgcolor='rgba(22,27,34,0.9)'`

## Project context

- This is Stock Analysis System (SAS) for analyzing and reporting on stock data.
- Do not use yfinance module for data fetching. Use the currently implemented data fetching module which uses Yahoo Finance API with incremental caching in `price_cache/` to ensure data freshness and minimize redundant API calls.
- The system consists of data fetching, processing, and report generation components.
- The main entry point is `main_pf_app.py` which orchestrates the workflow.
- The system uses a Python virtual environment (`venv`) for dependency management.
- The `run.sh` script is the primary interface for running the system, managing the venv, and ensuring proper execution order.
- The system generates reports in the `reports/` directory, served locally via `./run.sh --serve`.
- The master report entry point is `reports/index.html`, which links to all sub-reports.
- The system is designed for extensibility, allowing for new data sources, processing steps, and report types to be added with minimal disruption to existing functionality.
- The system emphasizes modularity, testability, and maintainability, with a focus on clear documentation and adherence to best practices.
- The system is designed to handle large volumes of stock data efficiently, with optimizations for performance and scalability as needed.
- The system includes comprehensive error handling and logging to facilitate debugging and ensure reliability.
- The system provides actionable insights into stock performance, trends, and opportunities for investors and analysts, leveraging data-driven approaches and advanced analytics techniques.
- This should provide early indication to exit a position if the stock is starting underperforming, or to take profits if the stock is overperforming, hold decisions. It can also help identify potential entry points (addition) based on technical indicators and market trends. Also rebalance the portfolio based on the performance of individual stocks and overall market conditions.
- This should work mobile friendly, with responsive HTML reports that can be viewed on various devices.
- This should be designed with security in mind, ensuring that any sensitive data (e.g. API keys, user information) is handled securely and not exposed in the codebase or reports.
- This is primarily based on momentum indicators, technical analysis, and other relevant metrics to identify stocks that are performing well and have the potential for further growth.
- Reporting should include actionable insights, key takeaways, such as potential entry and exit points for stocks. The system should provide clear recommendations for investors to take advantage of opportunities in the market while managing risk effectively.
- Always update any new feature to documentation report html (`reports_documentation_YYYYMMDD.html`). Make sure to read that report first to understand existing header meanings, current calculations etc. Ensure it is up to date and clear for users.
- Make sure all reports including filtered reports and hyperlinks are working from `index.html` to the report details page, and all the links in the report details page are working as well.
- All reports tables must be sortable and headers frozen when scrolling, and the report details page should have a back-to-index link at the top. Try to avoid vertical scrolling — remove irrelevant columns per report context.
- Inform user when the implementation ask and intention of this project is not aligned.
- This is intended for **swing trading and long-term investment analysis**, not for day trading or high-frequency trading. The system focuses on analyzing stock performance over days, weeks, and months to identify trends and opportunities. It is not designed for real-time analysis or rapid decision-making required for day trading or high-frequency trading.
- Always update `copilot-instructions.md` with any new feature or change, to ensure that the working agreements and project context are up to date.

## Implemented: Mark Minervini stage analysis

- 4-stage stock cycle classification (Basing → Advancing → Topping → Declining)
- 8-point Trend Template screening using SMA 50/150/200, 52wH/52wL, RS
- Stage-based scoring REPLACES RSI in momentum category of Composite Scorer
- RSI remains as a reference column but is NOT used in scoring or signal generation
- Signal engine requires Stage 1/2 for Buy signals; Stage 3/4 generate bearish factors
- Alert engine: Stage 4 = Critical, Stage 3 = Warning, Stage 2 TT7+ = Info
- 6 new Minervini filters in interactive_filter.py (Stage 1/2/3/4, TT 6+, TT 7+)
- Dedicated report: `minervini_stage_analysis_YYYYMMDD.html` with pie chart, stage tables

## Implemented: Higher High / Higher Low swing detection

- `_detect_hh_hl()` in technical_indicators.py using **5-bar pivot detection** (11-bar window)
- Scans last 63 trading days (~3 months) for swing points
- A swing high: bar whose high is the highest in ±5 bars; swing low: bar whose low is the lowest in ±5 bars
- HH = last pivot high > prior pivot high; HL = last pivot low > prior pivot low
- 3 new dataset columns: HH (bool), HL (bool), Swing_Trend (Bullish/Bearish/Weakening/Topping)
- 4 new swing filters in interactive_filter.py:
  - Higher High & Higher Low (Bullish Swing)
  - Higher Low Only (Accumulation)
  - Lower Low (Bearish — Exit Signal)
  - Higher High Only (Topping Risk)
- Filter sub-page nav only links to non-empty filter reports (avoids broken links)

## Implemented: Performance Bar Chart report

- `performance_bar_report.py` — horizontal green/red bars for 1W%, 1M%, 3M%, 6M%, 1Y% returns
- Summary cards (gainers/losers/best/worst per period), average returns table
- Quick-sort buttons per period, Stage/Signal/Swing_Trend columns
- Wired into pipeline Step 8 and master_report_generator.py Analytics section

## Implemented: Period return columns

- `_calculate_period_returns()` in technical_indicators.py
- 5 new columns: 1W%, 1M%, 3M%, 6M%, 1Y% (trading-day lookback)
- Displayed in filtered reports, Minervini stage tables, performance bar chart

## Implemented: Config-driven portfolio filename

- Removed all 14 hardcoded `dpsr_report.xls.xlsx` references across 5 files
- All modules now read from `config.json → system_settings.portfolio_file`
- `_default_portfolio_file()` helper pattern in pf_manager, data_fetcher, update_portfolio_data, verify_data_freshness, main_pf_app

## Implemented: Consolidated documentation

- README.md is the single comprehensive document with architecture, modules, indicators, config

## Implemented: Corrected RS (Relative Strength) calculation

- RS is period-based: `stock_period_return - benchmark_period_return` (percentage-point scale, typical range -20 to +30)
- Smoothing uses sliding sub-windows (not daily-return EMA which was 77× too small)
- Config keys: `rs_calculation_period: 90`, `rs_smoothing_period: 14`, `rs_benchmark_index: "^NSEI"`
- RS filter thresholds rescaled: `very_strong: 10.0`, `strong: 3.0`, `weak: -3.0`, `very_weak: -10.0`
- Scorer thresholds rescaled in `stock_scorer.py`: 5.0/7.0/10.0 (was 0.5/0.7/1.0)
- Signal engine thresholds rescaled in `signal_engine.py`: 3.0/5.0 (was 0.3/0.5)
- RSI remains reference-only column — NOT used in scoring or signals

## Implemented: Plotly chart improvements

- All charts use `hovermode='closest'` with crosshair spike lines (not `'x unified'` which showed all legend values)
- Spike lines: `showspikes=True, spikemode='across', spikesnap='cursor', spikethickness=1, spikedash='dot', spikecolor='#8b949e'`
- All charts use `plotly_dark` template (not `plotly_white`)
- Legend: dark background `rgba(22,27,34,0.9)`, text `#c9d1d9` (was invisible white-on-white)
- Applied across: `html_report_generator.py`, `interactive_filter.py`, `pf_drag_analyzer.py`, `pf_optimizer.py`

## Implemented: Filter count badges in index.html

- `master_report_generator.py` extracts stock count from each filtered report HTML (first 20KB, regex)
- Displays pill-style badge (e.g., "12 stocks") next to each filter link in the Interactive Filter Reports section
- Empty filters show "0 stocks" with muted styling

## Implemented: Memory optimization for 1GB machines

- `main_pf_app.py`: `analysis_results` is a reference (not `.copy()`); `gc.collect()` between pipeline steps; `del` + `gc.collect()` after drag_analyzer and optimizer; charts released after Step 6; parallel workers capped to max 2
- `interactive_filter.py`: Removed duplicate `filtered_dataset` copy at init; `hist_data` uses non-mutating operations (`.rename()` returns new df, `.assign()` instead of column overwrite)
- `pf_drag_analyzer.py` / `pf_optimizer.py`: `comprehensive_dataset` passed by reference (read-only); `historical_data.copy()` retained only where date columns are mutated

## Output formatting

- For plans: Use a short checklist then the proposed diff summary.
- For tests: Show commands you ran and the result summary.
- For documentation: Show the updated sections with context.
