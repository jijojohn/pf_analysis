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
- Documentation-first: If docs are outdated or missing, update `README.md` and the generated `reports_documentation_YYYYMMDD.html` before or along with the change. All docs live in the root.
- Keep the `run.sh` workflow as the primary interface for running the system.
- Always update `copilot-instructions.md` with any new feature or change.

## Architecture & module inventory

### Pipeline flow (orchestrated by `main_pf_app.py`)

```
run.sh -> venv activation -> verify_data_freshness.py -> update_portfolio_data.py -> main_pf_app.py
  STEP 0: cleanup old reports
  STEP 1: load portfolio (config.json -> system_settings.portfolio_file via pf_manager.py)
  STEP 2: check data availability (price_cache/*.pkl via data_fetcher.py)
  STEP 3: generate comprehensive dataset (technical_indicators.py)
  STEP 4: Minervini stage analysis (minervini_analyzer.py) + composite scoring (stock_scorer.py) + signals (signal_engine.py)
  STEP 5: create Plotly visualizations
  STEP 6: main portfolio report (html_report_generator.py)
  STEP 7: ~57 filtered reports (interactive_filter.py) -- includes 6 Minervini + 4 HH/HL swing filters
  STEP 8: advanced reports
     - pf_drag_analyzer.py -> portfolio_drag_analysis_YYYYMMDD.html
     - pf_optimizer.py -> portfolio_optimization_report_YYYYMMDD.html
     - minervini_analyzer.py -> minervini_stage_analysis_YYYYMMDD.html
     - performance_bar_report.py -> performance_bar_chart_YYYYMMDD.html
     - portfolio_health.py -> portfolio_health_YYYYMMDD.html
     - alert_engine.py -> alert_conditions_YYYYMMDD.html
     - backtest_engine.py -> signal_backtest_YYYYMMDD.html
     - sector_analyzer.py -> sector_rotation_YYYYMMDD.html
     - rebalance_advisor.py -> rebalance_suggestions_YYYYMMDD.html
     - momentum_rotation.py -> momentum_rotation_YYYYMMDD.html
     - performance_tracker.py -> performance_trend_YYYYMMDD.html
     - report_documentation.py -> reports_documentation_YYYYMMDD.html
  STEP 9: master index (master_report_generator.py -> reports/index.html)
```

### Key modules

| Module                       | Purpose                                                                                                                                                         |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `main_pf_app.py`             | Main orchestrator -- 9-step pipeline                                                                                                                            |
| `technical_indicators.py`    | All technical indicator calculations; builds comprehensive dataset per stock                                                                                    |
| `html_report_generator.py`   | Main portfolio HTML report with Plotly charts                                                                                                                   |
| `interactive_filter.py`      | ~55+ filter criteria; generates per-filter HTML reports (MA, RS, volume, 52w, Minervini, HH/HL swing)                                                           |
| `stock_scorer.py`            | Composite scoring (0-100) across 5 categories: RS, Trend, Momentum (Minervini stage-based), Risk, Value/Volume                                                  |
| `signal_engine.py`           | Strong Buy / Buy / Hold / Sell / Strong Sell signals -- stage-aware (Buy requires Stage 1/2)                                                                    |
| `minervini_analyzer.py`      | 4-stage classification, 8-point Trend Template, stage analysis report                                                                                           |
| `pf_optimizer.py`            | Correlation, beta, stress-test, efficient-frontier-style optimization                                                                                           |
| `pf_drag_analyzer.py`        | Leave-one-out portfolio drag analysis, per-stock drawdown                                                                                                       |
| `portfolio_health.py`        | Traffic-light health dashboard, HHI concentration, momentum health                                                                                              |
| `alert_engine.py`            | Critical/Warning/Info alerts: MA crossovers, volume spikes, drawdowns, RSI 70/30 crossings, golden/death cross, benchmark-relative drawdown, RS momentum fading |
| `backtest_engine.py`         | Replays event-based entry setups (SMA50/200 reclaim, golden cross, RSI bounce) and reports forward-return win rate / expectancy                                 |
| `sector_analyzer.py`         | Groups holdings by `config.json` sector_map; sector leaderboard + stage distribution (Unclassified fallback)                                                    |
| `rebalance_advisor.py`       | Concrete EXIT/TRIM/ADD/HOLD deltas with target allocations; redistributes freed capital to ADD candidates by score                                              |
| `momentum_rotation.py`       | RRG-style quadrants (Leading/Weakening/Improving/Lagging) from RS + RS_Trend                                                                                    |
| `data_utils.py`              | Centralized data cleaning helpers: `clean_close_nan()`, `safe_float()`                                                                                          |
| `performance_tracker.py`     | Persists metrics per run to `performance_history.json`; trend charts                                                                                            |
| `master_report_generator.py` | Generates `reports/index.html` -- central dashboard with filter count badges                                                                                    |
| `report_documentation.py`    | Full guide to all reports, indicators, calculations                                                                                                             |
| `report_style.py`            | Shared dark-theme CSS, sortable-table JS, nav bar, "How It Works" helpers, `render_table()` + `html_escape()`                                                   |
| `config_manager.py`          | Loads/manages `config.json` -- all configurable thresholds and parameters                                                                                       |
| `data_fetcher.py`            | Yahoo Finance API with smart incremental caching, NSE/BSE fallback, NaN close cleanup                                                                           |
| `update_portfolio_data.py`   | Standalone script to update portfolio + benchmark data                                                                                                          |
| `performance_bar_report.py`  | Horizontal period-return bar chart for all stocks (1W/1M/3M/6M/1Y)                                                                                              |
| `pf_manager.py`              | Loads portfolio from config-driven Excel file, normalizes columns                                                                                               |
| `data_freshness_checker.py`  | Validates data freshness before analysis                                                                                                                        |
| `verify_data_freshness.py`   | CLI freshness check used by `run.sh`                                                                                                                            |
| `smart_data_updater.py`      | Incremental data update logic, used by `data_freshness_checker.py`                                                                                              |

### Technical indicators in the comprehensive dataset

- **Moving averages:** WEMA21 (Weekly EMA 21), WEMA30 (Weekly EMA 30), DSMA50, DSMA200, SMA50, SMA150, SMA200
- **Internal only (not in dataset columns):** SMA20, EMA12, EMA26, EMA50, MACD, Bollinger Bands, Stochastic (Slow 14,3,3), ATR, Williams %R
- **Note:** WEMA21/WEMA30 are proper EMA (`ewm(span=period, adjust=False)`) on daily close. DSMA50/DSMA200 are displaced (shifted) SMAs kept as reference columns only. Filters and scoring use current SMA50/SMA200 (not displaced).
- **Minervini:** Stage (1-4), Stage_Name, TT_Score (0-8), Stage_Action, SMA200_Slope
- **52-week:** 52wH, 52wL, 52wHCh%, 52wLCh%
- **Momentum:** RSI (14-period Wilder's RMA, reference only -- NOT used in scoring or signals), RS (vs NIFTY 50 benchmark), RS_Prev (RS ~21 trading days ago), RS_Trend (Rising/Falling/Flat vs 1 month ago), RS_Quadrant (RRG-style: Leading/Weakening/Improving/Lagging)
- **Risk:** Sharpe Ratio, Sortino Ratio, Standard Deviation
- **Volume:** OBV, A/D Line, Relative_Volume, Week/Month avg, Volume_Threshold_2x, Week_Threshold_Ratio
- **Extension:** DMA200_Extension_Pct
- **Period Returns:** 1W%, 1M%, 3M%, 6M%, 1Y% (trading-day lookback: 5/21/63/126/252)
- **Swing Pattern:** HH (Higher High), HL (Higher Low), Swing_Trend (Bullish/Bearish/Weakening/Topping)

#### TradingView-compatible formulas

All indicators use TradingView-compatible formulas. Any future indicator additions MUST follow these conventions:

| Indicator           | Formula                                                   |
| ------------------- | --------------------------------------------------------- |
| **RSI / ATR**       | Wilder's RMA: `ewm(alpha=1/period, adjust=False).mean()`  |
| **EMA**             | `ewm(span=period, adjust=False).mean()`                   |
| **MACD**            | EMA(12) - EMA(26), signal = EMA(9) of MACD line           |
| **Stochastic**      | Slow 14,3,3: raw %K smoothed by SMA(3), %D = SMA(3) of %K |
| **Bollinger Bands** | Population std dev (`ddof=0`)                             |
| **SMA**             | `rolling(window=period).mean()`                           |

#### Display label conventions

- Internal column names: `WEMA21`, `WEMA30`, `DSMA50`, `DSMA200`
- User-facing display: "Weekly EMA 21", "Weekly EMA 30", "SMA 50", "SMA 200"
- Table column headers use `col_display_names` mapping in filtered reports

### Report styling conventions

- All reports use shared `report_style.py` (unified dark theme: body `#0d1117`, text `#c9d1d9`, accent `#58a6ff`)
- Tables: sortable via `onclick="sortTable(this)"`, sticky headers, frozen first column
- Responsive design: `@media` breakpoints at 768px and 480px (mobile-friendly)
- All reports have nav bar linking back to `reports/index.html`
- Reports include "How This Report Works" collapsible section
- Plotly charts: `template='plotly_dark'`, `paper_bgcolor='#161b22'`, `plot_bgcolor='#0d1117'`, `font(color='#c9d1d9')`, `hovermode='closest'` with crosshair spikes (`showspikes=True, spikemode='across', spikesnap='cursor', spikethickness=1, spikedash='dot', spikecolor='#8b949e'`), legend `bgcolor='rgba(22,27,34,0.9)'`
- All report `generate_report()` methods return the **filename** (not HTML content) -- `main_pf_app.py` must NEVER print return values in f-strings

## Project context

- **Stock Analysis System (SAS)** for **swing trading and long-term investment** -- not day trading or HFT.
- Do NOT use `yfinance` module. Use the implemented `data_fetcher.py` which uses Yahoo Finance API with incremental caching.
- Always update new features to documentation report (`reports_documentation_YYYYMMDD.html`). Read existing docs first.
- All reports must have sortable tables, frozen headers, back-to-index link, working hyperlinks. Minimize vertical scrolling.
- Reporting should include actionable insights: entry/exit points, hold decisions, rebalance recommendations.
- Inform user when an implementation request is not aligned with this project's swing/long-term trading focus.
- Security: Never expose API keys or sensitive data in codebase or reports.

## Data fetching & smart update architecture

### Data flow overview

- **Portfolio symbols**: sourced from `config.json -> system_settings.portfolio_file` Excel file (config-driven, not hardcoded)
- **Cache**: per-symbol pickle files in `price_cache/{BASE_SYMBOL}_data.pkl` (exchange suffix stripped) -- single source of truth
- **Analysis pipeline** (`main_pf_app.py`): reads cache only -- zero network calls during analysis
- **Data update** (`update_portfolio_data.py`): calls `get_stock_data_smart()` per symbol, writes to cache

### Smart data fetcher (`get_stock_data_smart()` in `data_fetcher.py`)

The primary entry point for all data fetching. Implements a 4-step fallback strategy:

1. **Cache lookup with exchange fallback** (`_load_from_cache_with_fallback`):
   - Loads `{base_symbol}_data.pkl` from `price_cache/` (e.g., `RELIANCE_data.pkl` for `RELIANCE.NS`)
   - Uses `_base_symbol()` to strip `.NS`/`.BO` suffix for filename lookup
   - Cleans NaN close rows from cached data

2. **Incremental (delta) fetch** -- if cache exists but is stale:
   - `_get_missing_date_range()` determines what's missing using IST (`Asia/Kolkata`)
   - Fetches only missing data from 5 days before last cached date to today
   - **NSE/BSE fallback on incremental**: if primary symbol fetch fails/returns empty, automatically tries the alternative exchange symbol before giving up
   - Combines new data with existing via `_combine_historical_data()` (deduplicates by date+symbol)
   - Saves combined data back to cache under original symbol name

3. **Full historical fetch** -- if no cache exists:
   - `_fetch_full_historical_data()` fetches 6 years of daily OHLCV data
   - If primary symbol returns no data, tries alternative exchange (Step 4)

4. **Alternative exchange fallback** (`_get_alternative_exchange_symbol`):
   - `.NS` (NSE) to `.BO` (BSE) automatic conversion and vice versa
   - Symbols without suffix -> tries `.BO`
   - Data is always saved under the **base symbol** cache filename (e.g., both `MODINSU.NS` and `MODINSU.BO` save to `MODINSU_data.pkl`)
   - `_base_symbol()` strips `.NS`/`.BO`: `RELIANCE.NS` -> `RELIANCE`, `MODINSU.BO` -> `MODINSU`
   - Example: `MODINSU.NS` not available on NSE -> dynamically switches to `MODINSU.BO` for data fetching, saves as `MODINSU_data.pkl`

### IST-aware freshness logic

- `_get_latest_expected_trading_date(now_ist)` determines the latest date for which market data should exist:
  - After 4 PM IST on weekdays -> expects today's data
  - Before 4 PM IST on weekdays -> expects previous trading day's data
  - Weekends -> expects Friday's data (but accepts Saturday/Sunday data if it exists in cache)
- Skips fetch entirely if `last_cached_date >= latest_expected` -- no unnecessary API calls

### NaN close price cleanup

NaN close rows (from incomplete market-open fetches) are dropped at every layer:

- `_yahoo_finance_fetch()`: before returning raw data
- `_combine_historical_data()`: before merging
- `get_stock_data_smart()`: after loading from cache
- `DataManager._ensure_proper_index()`: when loading for analysis
- `technical_indicators.py`: per-symbol before calculating indicators

### Yahoo Finance API details

- Uses dynamic crumb/cookie authentication (`_get_yahoo_crumb_dynamic()`)
- Falls back to hardcoded crumb if dynamic fetch fails after 2 attempts
- 1-second rate limiting between requests
- API endpoint: `query2.finance.yahoo.com/v8/finance/chart/{symbol}`
- Uses `adjclose` as the `close` column (adjusted for splits/dividends)

### Symbol handling conventions

- `update_portfolio_data.py` appends `.NS` if symbol has no exchange suffix
- Only symbols from `portfolio_file` are included in comprehensive dataset and reports
- Symbols without cached data are skipped with a warning
- Benchmark indices fetched separately (`update_portfolio_data.py --benchmarks`)
- Cache may contain non-portfolio symbols; they are ignored during analysis
- `run.sh` reads portfolio filename from `config.json`

### Multiple data manager classes

- `get_stock_data_smart()`: module-level function -- primary fetcher used by `update_portfolio_data.py`
- `StreamlinedDataManager`: freshness checking, selective/full update orchestration
- `DataManager`: used by analysis pipeline -- cache-only reads (no network), with BSE fallback for cache loading and force-update fetching

## Feature reference

### Minervini stage analysis

- 4-stage stock cycle: Basing (1) -> Advancing (2) -> Topping (3) -> Declining (4)
- 8-point Trend Template screening using SMA 50/150/200, 52wH/52wL, RS
- Stage-based scoring in momentum category of Composite Scorer (replaces RSI in scoring)
- Signal engine requires Stage 1/2 for Buy signals; Stage 3/4 generate bearish factors
- Alert engine: Stage 4 = Critical, Stage 3 = Warning, Stage 2 TT7+ = Info
- 6 Minervini filters in `interactive_filter.py` (Stage 1/2/3/4, TT 6+, TT 7+)
- Dedicated report: `minervini_stage_analysis_YYYYMMDD.html`

### Higher High / Higher Low swing detection

- `_detect_hh_hl()` in `technical_indicators.py`: **5-bar pivot detection** (11-bar window) on daily chart data
- Scans last 63 trading days (~3 months); accepts pivot if bar is **first occurrence** of max/min in +/-5 bars (`np.argmax`/`np.argmin`)
- HH = last pivot high > prior pivot high; HL = last pivot low > prior pivot low
- 4 swing filters: Bullish Swing (HH+HL), Accumulation (HL only), Bearish Exit (Lower Low), Topping Risk (HH only)
- Filter sub-page nav only links to non-empty filter reports

### RS (Relative Strength) calculation

- Period-based: `stock_period_return - benchmark_period_return` (percentage-point scale, typical range -20 to +30)
- Smoothing: sliding sub-windows (not daily-return EMA)
- Config keys: `rs_calculation_period: 90`, `rs_smoothing_period: 14`, `rs_benchmark_index: "^NSEI"`
- Scorer thresholds: 5.0/7.0/10.0 | Signal thresholds: 3.0/5.0 | Filter thresholds: very_strong 10.0, strong 3.0, weak -3.0, very_weak -10.0

### Memory optimization

- `analysis_results` passed by reference (no `.copy()`); `gc.collect()` between pipeline steps
- `interactive_filter.py`: non-mutating operations (`.rename()`, `.assign()`)
- `pf_drag_analyzer.py` / `pf_optimizer.py`: `comprehensive_dataset` read-only; parallel workers capped to max 2

## Output formatting

- For plans: Use a short checklist then the proposed diff summary.
- For tests: Show commands you ran and the result summary.
- For documentation: Show the updated sections with context.
