#!/usr/bin/env python3
"""
Quick Portfolio Data Update Script
Updates all portfolio symbols to the latest available data
Can also update non-portfolio symbols (benchmarks, indices, watchlist)
"""

import pandas as pd
import os
import glob
from data_fetcher import get_stock_data_smart
from config_manager import get_config


def _default_portfolio_file() -> str:
    return get_config().get_setting('system_settings.portfolio_file', 'dpsr_report.xls.xlsx')


def update_portfolio_data(portfolio_file=None, force_update=False):
    """Update data for all symbols in the portfolio
    
    Args:
        portfolio_file: Excel file containing portfolio symbols
        force_update: If False (default), fetches only delta data from 5 days before last cached date.
                     If True, fetches full 6-year historical data.
    """
    if portfolio_file is None:
        portfolio_file = _default_portfolio_file()
    
    if not os.path.exists(portfolio_file):
        print(f"❌ Portfolio file '{portfolio_file}' not found!")
        return False
    
    try:
        # Load portfolio
        df = pd.read_excel(portfolio_file)
        
        # Find symbol column
        symbol_col = None
        for col in ['Symbol', 'ScripCode', 'Scrip Code', 'symbol', 'scrip_code']:
            if col in df.columns:
                symbol_col = col
                break
        
        if symbol_col is None:
            print("❌ Could not find symbol column in portfolio file")
            return False
        
        symbols = df[symbol_col].dropna().tolist()
        
        print("="*80)
        print("🔄 PORTFOLIO DATA UPDATE")
        print("="*80)
        print(f"📁 Portfolio file: {portfolio_file}")
        print(f"📈 Total symbols: {len(symbols)}")
        print(f"🔄 Force update: {force_update}")
        print("="*80)
        print()
        
        success_count = 0
        failed_symbols = []
        
        for i, symbol in enumerate(symbols, 1):
            # Add .NS if not present
            if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
                symbol = f"{symbol}.NS"
            
            print(f"[{i}/{len(symbols)}] Updating {symbol}...")
            
            try:
                data = get_stock_data_smart(symbol, force_update=force_update)
                
                if not data.empty:
                    last_date = data.index.max()
                    last_close = data['close'].iloc[-1]
                    print(f"    ✅ Updated: {last_date} | Close: ₹{last_close:.2f} | Records: {len(data)}")
                    success_count += 1
                else:
                    print(f"    ❌ No data retrieved")
                    failed_symbols.append(symbol)
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
                failed_symbols.append(symbol)
            
            print()
        
        # Summary
        print("="*80)
        print("📊 UPDATE SUMMARY")
        print("="*80)
        print(f"✅ Successfully updated: {success_count}/{len(symbols)}")
        
        if failed_symbols:
            print(f"❌ Failed symbols ({len(failed_symbols)}):")
            for sym in failed_symbols:
                print(f"   - {sym}")
        else:
            print("🎉 All symbols updated successfully!")
        
        print("="*80)
        
        return len(failed_symbols) == 0
        
    except Exception as e:
        print(f"❌ Error updating portfolio: {e}")
        return False

def update_benchmark_data_only(force_update=False):
    """Update only configured benchmark indices data
    
    Args:
        force_update: If False (default), fetches only delta data.
                     If True, fetches full 6-year historical data.
    
    Returns:
        bool: True if all updates succeeded, False otherwise
    """
    try:
        from data_fetcher import update_benchmark_data
        
        print("="*80)
        print("📊 BENCHMARK DATA UPDATE")
        print("="*80)
        print(f"🔄 Force update: {force_update}")
        print("="*80)
        print()
        
        success = update_benchmark_data(force_update=force_update)
        
        print()
        print("="*80)
        if success:
            print("✅ All benchmark indices updated successfully!")
        else:
            print("⚠️  Benchmark update completed with some errors")
        print("="*80)
        
        return success
        
    except Exception as e:
        print(f"❌ Error updating benchmark data: {e}")
        return False


def update_non_portfolio_data(portfolio_file=None, force_update=False):
    """Update all cached symbols EXCEPT those in the portfolio
    
    Args:
        portfolio_file: Excel file containing portfolio symbols (to exclude)
        force_update: If False (default), fetches only delta data from 5 days before last cached date.
                     If True, fetches full 6-year historical data.
    
    Returns:
        bool: True if all updates succeeded, False otherwise
    """
    if portfolio_file is None:
        portfolio_file = _default_portfolio_file()
    
    try:
        # Get portfolio symbols to exclude
        portfolio_symbols = set()
        if os.path.exists(portfolio_file):
            df = pd.read_excel(portfolio_file)
            symbol_col = None
            for col in ['Symbol', 'ScripCode', 'Scrip Code', 'symbol', 'scrip_code']:
                if col in df.columns:
                    symbol_col = col
                    break
            
            if symbol_col:
                for sym in df[symbol_col].dropna().tolist():
                    # Add both with and without .NS/.BO suffix
                    base_sym = sym.split('.')[0]
                    portfolio_symbols.add(f"{base_sym}.NS")
                    portfolio_symbols.add(f"{base_sym}.BO")
                    portfolio_symbols.add(base_sym)
        
        # Get all cached symbols
        cache_files = glob.glob('price_cache/*_data.pkl')
        all_symbols = []
        
        for cache_file in cache_files:
            # Extract symbol from filename
            filename = os.path.basename(cache_file)
            symbol = filename.replace('_data.pkl', '')
            
            # Skip portfolio symbols
            if symbol not in portfolio_symbols:
                all_symbols.append(symbol)
        
        if not all_symbols:
            print("✅ No non-portfolio symbols found in cache")
            return True
        
        print("="*80)
        print("🔄 NON-PORTFOLIO DATA UPDATE")
        print("="*80)
        print(f"📁 Excluded portfolio: {portfolio_file}")
        print(f"📈 Non-portfolio symbols to update: {len(all_symbols)}")
        print(f"🔄 Force update: {force_update}")
        print("="*80)
        print()
        
        success_count = 0
        failed_symbols = []
        
        for i, symbol in enumerate(sorted(all_symbols), 1):
            print(f"[{i}/{len(all_symbols)}] Updating {symbol}...")
            
            try:
                data = get_stock_data_smart(symbol, force_update=force_update)
                
                if not data.empty:
                    last_date = data.index.max()
                    last_close = data['close'].iloc[-1]
                    print(f"    ✅ Updated: {last_date} | Close: ₹{last_close:.2f} | Records: {len(data)}")
                    success_count += 1
                else:
                    print(f"    ❌ No data retrieved")
                    failed_symbols.append(symbol)
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
                failed_symbols.append(symbol)
            
            print()
        
        # Summary
        print("="*80)
        print("📊 UPDATE SUMMARY")
        print("="*80)
        print(f"✅ Successfully updated: {success_count}/{len(all_symbols)}")
        
        if failed_symbols:
            print(f"❌ Failed symbols ({len(failed_symbols)}):")
            for sym in failed_symbols:
                print(f"   - {sym}")
        else:
            print("🎉 All non-portfolio symbols updated successfully!")
        
        print("="*80)
        
        return len(failed_symbols) == 0
        
    except Exception as e:
        print(f"❌ Error updating non-portfolio data: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    print("\n")
    
    force_update = False  # Changed default to False for incremental updates
    portfolio_file = _default_portfolio_file()
    update_non_portfolio = False
    update_benchmarks_only = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--force":
            force_update = True
            print("ℹ️  Running in force mode (full 6-year data refresh)")
        elif sys.argv[1] == "--non-portfolio" or sys.argv[1] == "-n":
            update_non_portfolio = True
            print("ℹ️  Running in non-portfolio mode (updating all except portfolio symbols)")
            if len(sys.argv) > 2 and sys.argv[2] == "--force":
                force_update = True
                print("ℹ️  With force mode enabled")
        elif sys.argv[1] == "--benchmarks" or sys.argv[1] == "-b":
            update_benchmarks_only = True
            print("ℹ️  Running in benchmarks-only mode")
            if len(sys.argv) > 2 and sys.argv[2] == "--force":
                force_update = True
                print("ℹ️  With force mode enabled")
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage:")
            print("  python3 update_portfolio_data.py                    # Incremental update (delta data only)")
            print("  python3 update_portfolio_data.py --force            # Force full 6-year data refresh")
            print("  python3 update_portfolio_data.py --benchmarks       # Update only benchmark indices")
            print("  python3 update_portfolio_data.py -b --force         # Benchmarks with full refresh")
            print("  python3 update_portfolio_data.py --non-portfolio    # Update all cached symbols EXCEPT portfolio")
            print("  python3 update_portfolio_data.py -n --force         # Non-portfolio with full refresh")
            print("  python3 update_portfolio_data.py FILE               # Update specific file")
            print()
            print("Options:")
            print("  --benchmarks, -b      Update only configured benchmark indices")
            print("  --non-portfolio, -n   Update only non-portfolio symbols (indices, benchmarks, watchlist)")
            print("  --force               Force full 6-year historical data refresh")
            print()
            exit(0)
        else:
            portfolio_file = sys.argv[1]
    
    if update_benchmarks_only:
        success = update_benchmark_data_only(force_update)
    elif update_non_portfolio:
        success = update_non_portfolio_data(portfolio_file, force_update)
    else:
        success = update_portfolio_data(portfolio_file, force_update)
    
    print("\n")
    
    if success:
        if update_benchmarks_only:
            print("✅ Benchmark data update completed successfully!")
        elif update_non_portfolio:
            print("✅ Non-portfolio data update completed successfully!")
        else:
            print("✅ Portfolio data update completed successfully!")
        
        if force_update:
            print("💡 Full 6-year data refresh completed")
        else:
            print("💡 Incremental delta update completed (5 days backward to today)")
        
        if not update_benchmarks_only:
            print("💡 Run 'python3 verify_data_freshness.py -p' to verify the updates")
    else:
        if update_benchmarks_only:
            print("⚠️  Benchmark data update completed with some errors")
        elif update_non_portfolio:
            print("⚠️  Non-portfolio data update completed with some errors")
        else:
            print("⚠️  Portfolio data update completed with some errors")
    
    print("\n")
