#!/usr/bin/env python3
"""
Data Freshness Verification Script
Displays the last date and close price for all cached stock data
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# IST timezone for Indian stock market
IST = ZoneInfo('Asia/Kolkata')

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False
    
    def tabulate(data, headers=None, tablefmt="grid"):
        """Simple fallback table formatter"""
        if not data:
            return ""
        
        # Calculate column widths
        col_widths = []
        if headers:
            col_widths = [len(str(h)) for h in headers]
        else:
            headers = [f"Col{i}" for i in range(len(data[0]))]
            col_widths = [len(h) for h in headers]
        
        for row in data:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Build table
        lines = []
        sep = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"
        
        lines.append(sep)
        # Header
        header_row = "| " + " | ".join([str(h).ljust(w) for h, w in zip(headers, col_widths)]) + " |"
        lines.append(header_row)
        lines.append(sep)
        
        # Data rows
        for row in data:
            data_row = "| " + " | ".join([str(cell).ljust(w) for cell, w in zip(row, col_widths)]) + " |"
            lines.append(data_row)
        
        lines.append(sep)
        return "\n".join(lines)

def verify_data_freshness(cache_dir='price_cache'):
    """Verify and display the freshness of all cached stock data"""
    
    if not os.path.exists(cache_dir):
        print(f"❌ Cache directory '{cache_dir}' not found!")
        return
    
    # Get all pickle files
    cache_files = sorted([f for f in os.listdir(cache_dir) if f.endswith('_data.pkl')])
    
    if not cache_files:
        print(f"❌ No cached data files found in '{cache_dir}'")
        return
    
    # Use IST timezone
    current_time = datetime.now(IST)
    
    print("="*80)
    print("📊 STOCK DATA FRESHNESS VERIFICATION")
    print("="*80)
    print(f"📁 Cache directory: {cache_dir}")
    print(f"📈 Total files: {len(cache_files)}")
    print(f"🕐 Current time (IST): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("="*80)
    print()
    
    results = []
    
    for cache_file in cache_files:
        try:
            # Extract symbol from filename
            symbol = cache_file.replace('_data.pkl', '')
            file_path = os.path.join(cache_dir, cache_file)
            
            # Load the data
            data = pd.read_pickle(file_path)
            
            if data.empty:
                results.append([symbol, "EMPTY", "N/A", "N/A", "❌ NO DATA"])
                continue
            
            # Get last date and close price
            last_date = None
            if isinstance(data.index, pd.DatetimeIndex):
                last_date = data.index[-1]
            elif hasattr(data.index, 'max'):
                last_date = data.index.max()
            elif 'Date' in data.columns:
                last_date = pd.to_datetime(data['Date'].iloc[-1])
            elif 'date' in data.columns:
                last_date = pd.to_datetime(data['date'].iloc[-1])
            
            if last_date is None or pd.isna(last_date):
                results.append([symbol, "ERROR", "N/A", "N/A", "❌ NO DATE"])
                continue
            
            # Get close price
            if 'close' in data.columns:
                close_price = data['close'].iloc[-1]
            elif 'Close' in data.columns:
                close_price = data['Close'].iloc[-1]
            else:
                close_price = "N/A"
            
            # Calculate age
            if hasattr(last_date, 'to_pydatetime'):
                last_date_dt = last_date.to_pydatetime()
            elif isinstance(last_date, pd.Timestamp):
                last_date_dt = last_date.to_pydatetime()
            else:
                last_date_dt = pd.to_datetime(last_date).to_pydatetime()
            
            # Make last_date_dt timezone-aware (assume IST for Indian stocks)
            if last_date_dt.tzinfo is None:
                last_date_dt = last_date_dt.replace(tzinfo=IST)
            
            age = current_time - last_date_dt
            days_old = age.days
            hours_old = age.seconds // 3600
            
            # Format age string
            if days_old == 0:
                age_str = f"{hours_old}h"
                status = "✅ TODAY"
            elif days_old == 1:
                age_str = "1 day"
                status = "✅ RECENT"
            elif days_old <= 3:
                age_str = f"{days_old} days"
                status = "✅ FRESH"
            elif days_old <= 7:
                age_str = f"{days_old} days"
                status = "⚠️  STALE"
            else:
                age_str = f"{days_old} days"
                status = "❌ OLD"
            
            # Get record count
            record_count = len(data)
            
            results.append([
                symbol,
                last_date_dt.strftime('%Y-%m-%d'),
                f"₹{close_price:.2f}" if isinstance(close_price, (int, float)) else close_price,
                age_str,
                status,
                record_count
            ])
            
        except Exception as e:
            results.append([symbol, "ERROR", "N/A", "N/A", f"❌ {str(e)[:20]}", "N/A"])
    
    # Display results in a table
    headers = ["Symbol", "Last Date", "Close Price", "Age", "Status", "Records"]
    print(tabulate(results, headers=headers, tablefmt="grid"))
    print()
    
    # Summary statistics
    print("="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    today_count = sum(1 for r in results if "TODAY" in r[4])
    fresh_count = sum(1 for r in results if "FRESH" in r[4] or "RECENT" in r[4])
    stale_count = sum(1 for r in results if "STALE" in r[4])
    old_count = sum(1 for r in results if "OLD" in r[4])
    error_count = sum(1 for r in results if "ERROR" in r[4] or "NO DATA" in r[4])
    
    print(f"✅ Up-to-date (today):     {today_count:3d}")
    print(f"✅ Recent (1-3 days):      {fresh_count:3d}")
    print(f"⚠️  Stale (4-7 days):      {stale_count:3d}")
    print(f"❌ Old (>7 days):          {old_count:3d}")
    print(f"❌ Errors/Empty:           {error_count:3d}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📊 Total:                  {len(results):3d}")
    print("="*80)
    
    # Recommendations
    print()
    if old_count > 0 or stale_count > 0:
        print("💡 RECOMMENDATION: Run data update to refresh stale/old data")
        print(f"   Command: python3 main_pf_app.py --update")
    elif today_count == len(results):
        print("🎉 EXCELLENT: All data is up-to-date!")
    else:
        print("👍 GOOD: Data is reasonably current")

def verify_portfolio_symbols(portfolio_file=None, cache_dir='price_cache'):
    """Verify data freshness for symbols in portfolio file"""
    if portfolio_file is None:
        from config_manager import get_config
        portfolio_file = get_config().get_setting('system_settings.portfolio_file', 'dpsr_report.xls.xlsx')
    
    if not os.path.exists(portfolio_file):
        print(f"❌ Portfolio file '{portfolio_file}' not found!")
        return
    
    try:
        # Load portfolio
        df = pd.read_excel(portfolio_file)
        
        # Try to find symbol column
        symbol_col = None
        for col in ['Symbol', 'ScripCode', 'Scrip Code', 'symbol', 'scrip_code']:
            if col in df.columns:
                symbol_col = col
                break
        
        if symbol_col is None:
            print("❌ Could not find symbol column in portfolio file")
            return
        
        symbols = df[symbol_col].dropna().tolist()
        
        # Use IST timezone
        current_time = datetime.now(IST)
        
        print("="*80)
        print("📊 PORTFOLIO SYMBOLS DATA VERIFICATION")
        print("="*80)
        print(f"📁 Portfolio file: {portfolio_file}")
        print(f"📈 Total symbols: {len(symbols)}")
        print(f"🕐 Current time (IST): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("="*80)
        print()
        
        results = []
        
        for symbol in symbols:
            # Add .NS if not present
            if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
                symbol = f"{symbol}.NS"
            
            # Cache files use base symbol (no .NS/.BO suffix)
            base_sym = symbol.split('.')[0] if '.' in str(symbol) else str(symbol)
            cache_file = os.path.join(cache_dir, f"{base_sym}_data.pkl")
            
            if not os.path.exists(cache_file):
                results.append([symbol, "NOT FOUND", "N/A", "N/A", "❌ MISSING", 0])
                continue
            
            try:
                data = pd.read_pickle(cache_file)
                
                if data.empty:
                    results.append([symbol, "EMPTY", "N/A", "N/A", "❌ NO DATA", 0])
                    continue
                
                # Get last date and close price
                last_date = None
                if isinstance(data.index, pd.DatetimeIndex):
                    last_date = data.index[-1]
                elif hasattr(data.index, 'max'):
                    last_date = data.index.max()
                elif 'Date' in data.columns:
                    last_date = pd.to_datetime(data['Date'].iloc[-1])
                elif 'date' in data.columns:
                    last_date = pd.to_datetime(data['date'].iloc[-1])
                
                if last_date is None or pd.isna(last_date):
                    results.append([symbol, "ERROR", "N/A", "N/A", "❌ NO DATE", len(data)])
                    continue
                
                # Get close price
                if 'close' in data.columns:
                    close_price = data['close'].iloc[-1]
                elif 'Close' in data.columns:
                    close_price = data['Close'].iloc[-1]
                else:
                    close_price = "N/A"
                
                # Calculate age
                if hasattr(last_date, 'to_pydatetime'):
                    last_date_dt = last_date.to_pydatetime()
                else:
                    last_date_dt = pd.to_datetime(last_date).to_pydatetime()
                
                # Make last_date_dt timezone-aware (assume IST for Indian stocks)
                if last_date_dt.tzinfo is None:
                    last_date_dt = last_date_dt.replace(tzinfo=IST)
                
                age = current_time - last_date_dt
                days_old = age.days
                
                # Format age string
                if days_old == 0:
                    age_str = f"{age.seconds // 3600}h"
                    status = "✅ TODAY"
                elif days_old == 1:
                    age_str = "1 day"
                    status = "✅ RECENT"
                elif days_old <= 3:
                    age_str = f"{days_old} days"
                    status = "✅ FRESH"
                elif days_old <= 7:
                    age_str = f"{days_old} days"
                    status = "⚠️  STALE"
                else:
                    age_str = f"{days_old} days"
                    status = "❌ OLD"
                
                results.append([
                    symbol,
                    last_date_dt.strftime('%Y-%m-%d'),
                    f"₹{close_price:.2f}" if isinstance(close_price, (int, float)) else close_price,
                    age_str,
                    status,
                    len(data)
                ])
                
            except Exception as e:
                results.append([symbol, "ERROR", "N/A", "N/A", f"❌ {str(e)[:20]}", 0])
        
        # Display results
        headers = ["Symbol", "Last Date", "Close Price", "Age", "Status", "Records"]
        print(tabulate(results, headers=headers, tablefmt="grid"))
        print()
        
        # Summary
        print("="*80)
        print("📊 SUMMARY")
        print("="*80)
        
        today_count = sum(1 for r in results if "TODAY" in r[4])
        fresh_count = sum(1 for r in results if "FRESH" in r[4] or "RECENT" in r[4])
        stale_count = sum(1 for r in results if "STALE" in r[4])
        old_count = sum(1 for r in results if "OLD" in r[4])
        missing_count = sum(1 for r in results if "MISSING" in r[4])
        error_count = sum(1 for r in results if "ERROR" in r[4] or "NO DATA" in r[4])
        
        print(f"✅ Up-to-date (today):     {today_count:3d}")
        print(f"✅ Recent (1-3 days):      {fresh_count:3d}")
        print(f"⚠️  Stale (4-7 days):      {stale_count:3d}")
        print(f"❌ Old (>7 days):          {old_count:3d}")
        print(f"❌ Missing:                {missing_count:3d}")
        print(f"❌ Errors/Empty:           {error_count:3d}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📊 Total:                  {len(results):3d}")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error loading portfolio: {e}")

if __name__ == "__main__":
    import sys
    
    print("\n")
    
    # Return code: 0 = fresh data, 1 = needs update
    needs_update = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--portfolio" or sys.argv[1] == "-p":
            # Verify portfolio symbols only and determine if update needed
            portfolio_file = sys.argv[2] if len(sys.argv) > 2 else None
            if portfolio_file is None:
                from config_manager import get_config
                portfolio_file = get_config().get_setting('system_settings.portfolio_file', 'dpsr_report.xls.xlsx')
            
            if not os.path.exists(portfolio_file):
                print(f"❌ Portfolio file '{portfolio_file}' not found!")
                sys.exit(1)
            
            # Check portfolio data freshness
            try:
                df = pd.read_excel(portfolio_file)
                symbol_col = None
                for col in ['Symbol', 'ScripCode', 'Scrip Code', 'symbol', 'scrip_code']:
                    if col in df.columns:
                        symbol_col = col
                        break
                
                if symbol_col is None:
                    print("❌ Could not find symbol column in portfolio file")
                    sys.exit(1)
                
                symbols = df[symbol_col].dropna().tolist()
                current_time = datetime.now(IST)
                cache_dir = 'price_cache'
                
                # Quick check: sample a few symbols to determine freshness
                sample_size = min(10, len(symbols))
                stale_count = 0
                missing_count = 0
                
                for symbol in symbols[:sample_size]:
                    if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
                        symbol = f"{symbol}.NS"
                    
                    base_sym = symbol.split('.')[0] if '.' in str(symbol) else str(symbol)
                    cache_file = os.path.join(cache_dir, f"{base_sym}_data.pkl")
                    
                    if not os.path.exists(cache_file):
                        missing_count += 1
                        continue
                    
                    try:
                        data = pd.read_pickle(cache_file)
                        if data.empty:
                            stale_count += 1
                            continue
                        
                        # Get last date
                        last_date = None
                        if isinstance(data.index, pd.DatetimeIndex):
                            last_date = data.index[-1]
                        elif hasattr(data.index, 'max'):
                            last_date = data.index.max()
                        elif 'Date' in data.columns:
                            last_date = pd.to_datetime(data['Date'].iloc[-1])
                        elif 'date' in data.columns:
                            last_date = pd.to_datetime(data['date'].iloc[-1])
                        
                        if last_date is None or pd.isna(last_date):
                            stale_count += 1
                            continue
                        
                        # Calculate age
                        if hasattr(last_date, 'to_pydatetime'):
                            last_date_dt = last_date.to_pydatetime()
                        else:
                            last_date_dt = pd.to_datetime(last_date).to_pydatetime()
                        
                        # Make timezone-aware for accurate comparison
                        if last_date_dt.tzinfo is None:
                            last_date_dt = last_date_dt.replace(tzinfo=IST)
                        
                        age = current_time - last_date_dt
                        days_old = age.days
                        
                        # Market-aware freshness check
                        # Market closes at 3:30 PM IST, data usually available by 4:00 PM
                        # We want fresh data if we're past market close on a trading day
                        is_stale = False
                        
                        weekday = current_time.weekday()  # 0=Monday, 6=Sunday
                        current_hour = current_time.hour
                        
                        if weekday <= 4:  # Monday to Friday (trading days)
                            # After 4 PM, we expect today's data
                            if current_hour >= 16:  
                                if days_old > 0:
                                    is_stale = True
                            # Before 4 PM, yesterday's data is still acceptable
                            # But not if it's more than 1 day old
                            elif days_old > 1:
                                is_stale = True
                        elif weekday == 5:  # Saturday
                            # Friday's data (1 day old) is acceptable
                            if days_old > 1:
                                is_stale = True
                        elif weekday == 6:  # Sunday
                            # Friday's data (2 days old) is acceptable
                            if days_old > 2:
                                is_stale = True
                        
                        if is_stale or missing_count > 0:
                            stale_count += 1
                    
                    except Exception:
                        stale_count += 1
                
                # Determine if update is needed
                # Also check ALL symbols for missing cache (not just sample)
                all_missing = 0
                for sym in symbols:
                    s = sym if (str(sym).endswith('.NS') or str(sym).endswith('.BO')) else f"{sym}.NS"
                    base_s = s.split('.')[0] if '.' in str(s) else str(s)
                    if not os.path.exists(os.path.join(cache_dir, f"{base_s}_data.pkl")):
                        all_missing += 1

                if all_missing > 0:
                    needs_update = True
                    print(f"\n⚠️  {all_missing} stock(s) in xlsx have no cached price data — update needed")
                elif missing_count > 0 or stale_count > sample_size * 0.3:  # More than 30% stale
                    needs_update = True
                    print(f"\n⚠️  Data needs update (missing: {missing_count}, stale: {stale_count} out of {sample_size} sampled)")
                else:
                    print(f"\n✅ Data is fresh (checked {sample_size} symbols, all {len(symbols)} have cache)")
                
                # Show full verification
                verify_portfolio_symbols(portfolio_file)
                
            except Exception as e:
                print(f"❌ Error checking portfolio data: {e}")
                needs_update = True
        
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage:")
            print("  python3 verify_data_freshness.py           # Check all cached data")
            print("  python3 verify_data_freshness.py -p        # Check portfolio symbols only")
            print("  python3 verify_data_freshness.py -p FILE   # Check specific portfolio file")
            print()
            print("Exit codes:")
            print("  0 = Data is fresh (no update needed)")
            print("  1 = Data needs update (stale/missing)")
            sys.exit(0)
        else:
            verify_data_freshness(sys.argv[1])
    else:
        # Default: verify all cached data
        verify_data_freshness()
        
        print("\n")
        print("━"*80)
        print()
        
        # Also check portfolio symbols
        from config_manager import get_config
        _pf = get_config().get_setting('system_settings.portfolio_file', 'dpsr_report.xls.xlsx')
        if os.path.exists(_pf):
            verify_portfolio_symbols()
    
    print("\n")
    
    # Exit with appropriate code
    if needs_update:
        print("🔄 Exit code: 1 (update needed)")
        sys.exit(1)
    else:
        print("✅ Exit code: 0 (data is fresh)")
        sys.exit(0)
