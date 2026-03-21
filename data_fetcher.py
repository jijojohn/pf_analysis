#!/usr/bin/env python3
"""
Data Fetcher Module
Handles all data fetching operations using existing smart data fetcher logic
"""

import pandas as pd
import numpy as np
import os
import pickle
import requests
import time
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional, Tuple

def get_stock_data_smart(symbol: str, force_update: bool = False) -> pd.DataFrame:
    """Smart data fetcher with incremental updates and intelligent cache management"""
    
    cache_filename = f"{symbol}_data.pkl"
    cache_path = os.path.join('price_cache', cache_filename)
    
    # Step 1: Check for existing data and determine what needs to be fetched
    if not force_update:
        existing_data = _load_from_cache_with_fallback(symbol)
        if not existing_data.empty:
            # Clean NaN close rows from cached data (incomplete market-open fetches)
            if 'close' in existing_data.columns:
                existing_data = existing_data.dropna(subset=['close'])
            
            # Get the date range that needs to be updated
            missing_range = _get_missing_date_range(symbol, existing_data)
            
            if missing_range is None:
                # Data is up to date
                print(f"✅ Data for {symbol} is already up to date ({len(existing_data)} records)")
                return existing_data
            else:
                # Fetch only missing data incrementally
                print(f"� Fetching incremental data for {symbol} from {missing_range[0]} to {missing_range[1]}")
                new_data = _fetch_incremental_data(symbol, missing_range)
                
                if new_data is not None and not new_data.empty:
                    # Combine existing and new data
                    combined_data = _combine_historical_data(existing_data, new_data, symbol)
                    
                    # Save combined data
                    os.makedirs('price_cache', exist_ok=True)
                    combined_data.to_pickle(cache_path)
                    
                    print(f"✅ Updated {symbol} with {len(new_data)} new records (total: {len(combined_data)} records)")
                    return combined_data
                else:
                    # No new data available, use existing
                    print(f"📁 Using existing data for {symbol} ({len(existing_data)} records)")
                    return existing_data
    
    # Step 2: No existing data, fetch full historical data
    print(f"🔍 Fetching full historical data for {symbol}...")
    historical_data = _fetch_full_historical_data(symbol)
    
    if historical_data is not None and not historical_data.empty:
        print(f"✅ Retrieved full historical data for {symbol} ({len(historical_data)} records)")
        # Save data to cache
        os.makedirs('price_cache', exist_ok=True)
        historical_data.to_pickle(cache_path)
        return historical_data
    
    # Step 3: Try alternative exchange
    alt_symbol = _get_alternative_exchange_symbol(symbol)
    if alt_symbol and alt_symbol != symbol:
        print(f"🔄 Trying alternative exchange: {symbol} → {alt_symbol}")
        historical_data = _fetch_full_historical_data(alt_symbol)
        
        if historical_data is not None and not historical_data.empty:
            print(f"✅ Retrieved data from alternative exchange {alt_symbol} ({len(historical_data)} records)")
            # Save under original symbol name
            os.makedirs('price_cache', exist_ok=True)
            historical_data.to_pickle(cache_path)
            return historical_data
    
    # Step 4: No data available
    print(f"❌ No data available for {symbol} from any source")
    return pd.DataFrame()

def _get_missing_date_range(symbol: str, existing_data: pd.DataFrame) -> Optional[Tuple[date, date]]:
    """Determine the date range that needs to be fetched for incremental updates.
    
    Uses IST (Asia/Kolkata) for date comparisons since this is Indian stock market data.
    Dynamically checks the actual last data date against the latest expected trading day,
    rather than assuming fixed weekend rules (handles Saturday trading sessions, holidays, etc.).
    """
    if existing_data.empty:
        return None
    
    # Get the last date in existing data - handle both datetime and date types
    last_index = existing_data.index.max()
    if hasattr(last_index, 'date'):
        last_date = last_index.date()
    else:
        # Convert to date if it's a string or other format
        if isinstance(last_index, str):
            last_date = pd.to_datetime(last_index).date()
        elif isinstance(last_index, pd.Timestamp):
            last_date = last_index.date()
        else:
            last_date = last_index
    
    # Use IST for Indian stock market
    try:
        from zoneinfo import ZoneInfo
        ist = ZoneInfo('Asia/Kolkata')
    except ImportError:
        from datetime import timezone
        ist = timezone(timedelta(hours=5, minutes=30))
    
    from datetime import datetime as dt
    now_ist = dt.now(ist)
    today_ist = now_ist.date()
    
    # Determine the latest expected trading date
    # The market data for a day becomes available after market close (~3:30 PM IST)
    # We consider data "expected" only after 4:00 PM IST to allow time for Yahoo to update
    latest_expected = _get_latest_expected_trading_date(now_ist)
    
    # Check if data is already up to date
    if last_date >= latest_expected:
        return None
    
    # Calculate start date for missing data (5 days before last date to handle gaps)
    fetch_start_date = last_date - timedelta(days=5)
    
    # Fetch up to today
    print(f"📅 Will fetch data from {fetch_start_date} to {today_ist} (last cached: {last_date}, expected: {latest_expected})")
    return (fetch_start_date, today_ist)


def _get_latest_expected_trading_date(now_ist) -> date:
    """Determine the latest date for which we should expect market data.
    
    Logic:
    - Before 4 PM IST on a weekday: expect previous trading day's data
    - After 4 PM IST on a weekday: expect today's data
    - On weekends: expect the most recent Friday's data (unless market had a special session)
    - This is a best-effort heuristic; actual trading calendars may differ for holidays
    
    The function does NOT hardcode "no data on weekends" — it only determines
    what the latest expected date is. If Saturday/Sunday data actually exists
    in the cache, _get_missing_date_range will see last_date >= latest_expected
    and correctly skip fetching.
    """
    today = now_ist.date()
    weekday = today.weekday()  # 0=Monday, 6=Sunday
    hour = now_ist.hour
    
    if weekday <= 4:  # Monday–Friday
        if hour >= 16:  # After 4 PM: today's data should be available
            return today
        else:
            # Before 4 PM: previous trading day
            return _previous_weekday(today)
    elif weekday == 5:  # Saturday
        # Most recent expected data is Friday
        return today - timedelta(days=1)
    else:  # Sunday
        # Most recent expected data is Friday
        return today - timedelta(days=2)


def _previous_weekday(d: date) -> date:
    """Return the previous weekday (Mon-Fri) before date d."""
    d = d - timedelta(days=1)
    while d.weekday() > 4:  # Skip Saturday(5) and Sunday(6)
        d = d - timedelta(days=1)
    return d

def _fetch_incremental_data(symbol: str, date_range: Tuple[date, date]) -> Optional[pd.DataFrame]:
    """Fetch data for a specific date range (incremental update)"""
    start_date, end_date = date_range
    
    # Extend end date by 1 day to ensure we get the latest data
    extended_end = end_date + timedelta(days=1)
    
    try:
        print(f"🔄 Fetching incremental data for {symbol} from {start_date} to {end_date}")
        return _yahoo_finance_fetch(symbol, 
                                  start_date.strftime("%Y-%m-%d"), 
                                  extended_end.strftime("%Y-%m-%d"), 
                                  '1d')
    except Exception as e:
        print(f"⚠️ Error fetching incremental data for {symbol}: {e}")
        return None

def _fetch_full_historical_data(symbol: str) -> Optional[pd.DataFrame]:
    """Fetch full 6-year historical data for a symbol"""
    today = date.today()
    # Add 1 day to ensure we get today's data if available
    end_date = today + timedelta(days=1)
    start_date = today - relativedelta(years=6)
    
    try:
        print(f"� Fetching 6-year historical data for {symbol} from {start_date} to {today}")
        return _yahoo_finance_fetch(symbol, 
                                  start_date.strftime("%Y-%m-%d"), 
                                  end_date.strftime("%Y-%m-%d"), 
                                  '1d')
    except Exception as e:
        print(f"⚠️ Error fetching full historical data for {symbol}: {e}")
        return None

def _extend_dates_if_needed(date_range: Tuple[date, date]) -> Tuple[date, date]:
    """Extend date range to handle weekends and ensure minimum range"""
    start_date, end_date = date_range
    
    # Convert to list for manipulation
    date_list = [start_date, end_date]
    
    # Extend dates to ensure at least 5-day range (handles weekends)
    while len(date_list) < 5:
        # Add one day before the first date
        new_start = date_list[0] - timedelta(days=1)
        date_list.insert(0, new_start)
        
        # Check again before adding to avoid overshooting
        if len(date_list) < 5:
            # Add one day after the last date
            new_end = date_list[-1] + timedelta(days=1)
            date_list.append(new_end)
    
    # Return extended start and end dates
    return (date_list[0], date_list[-1])

def _combine_historical_data(existing_data: pd.DataFrame, new_data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Combine existing and new data, removing duplicates"""
    if existing_data.empty:
        return new_data
    if new_data.empty:
        return existing_data
    
    # Ensure both dataframes have Symbol column
    if 'Symbol' not in existing_data.columns:
        existing_data['Symbol'] = symbol.split('.')[0]
    if 'Symbol' not in new_data.columns:
        new_data['Symbol'] = symbol.split('.')[0]
    
    # Drop rows with NaN close before combining (incomplete/market-open data)
    if 'close' in existing_data.columns:
        existing_data = existing_data.dropna(subset=['close'])
    if 'close' in new_data.columns:
        new_data = new_data.dropna(subset=['close'])
    
    # Combine dataframes
    combined_data_list = [existing_data, new_data]
    combined_data = pd.concat(combined_data_list)
    
    # Reset index to handle duplicates
    combined_data = combined_data.reset_index()
    
    # Remove duplicates based on date and Symbol, keeping first occurrence
    if 'date' in combined_data.columns:
        combined_data = combined_data.drop_duplicates(subset=['date', 'Symbol'], keep='first')
        combined_data = combined_data.set_index('date')
    else:
        # If index is already datetime, reset and deduplicate
        combined_data['date'] = combined_data.index
        combined_data = combined_data.drop_duplicates(subset=['date', 'Symbol'], keep='first')
        combined_data = combined_data.set_index('date')
        combined_data = combined_data.drop(columns=['date'])
    
    # Sort by date
    combined_data = combined_data.sort_index()
    
    return combined_data

# Legacy function - now replaced by _fetch_full_historical_data and _fetch_incremental_data
def _fetch_real_market_data(symbol: str) -> Optional[pd.DataFrame]:
    """Fetch real market data from Yahoo Finance API (legacy function)"""
    return _fetch_full_historical_data(symbol)

# Module-level cache for dynamic crumb/cookie session
_yahoo_session_cache = {
    'crumb': None,
    'cookies': None,
    'fetched': False
}

# Original hardcoded crumb as fallback
_FALLBACK_CRUMB = 'J2oUJNHQwXU'

def _get_yahoo_crumb_dynamic():
    """Dynamically fetch a fresh Yahoo Finance crumb and cookies.
    Falls back to hardcoded crumb if dynamic fetch fails."""
    global _yahoo_session_cache
    
    # Return cached crumb if already fetched this session
    if _yahoo_session_cache['fetched'] and _yahoo_session_cache['crumb']:
        return _yahoo_session_cache['crumb'], _yahoo_session_cache['cookies']
    
    import requests as req
    
    for attempt in range(2):
        try:
            # Step 1: Get cookies from Yahoo Finance consent page
            session = req.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # Hit the finance page to get consent cookies
            session.get('https://fc.yahoo.com', timeout=10)
            
            # Step 2: Fetch crumb using the session cookies
            crumb_url = 'https://query2.finance.yahoo.com/v1/test/getcrumb'
            crumb_response = session.get(crumb_url, timeout=10)
            crumb_response.raise_for_status()
            
            crumb = crumb_response.text.strip()
            if crumb and len(crumb) > 0:
                _yahoo_session_cache['crumb'] = crumb
                _yahoo_session_cache['cookies'] = session.cookies
                _yahoo_session_cache['fetched'] = True
                print(f"✅ Dynamic Yahoo crumb fetched successfully")
                return crumb, session.cookies
                
        except Exception as e:
            if attempt == 0:
                print(f"⚠️  Dynamic crumb fetch attempt {attempt+1} failed: {e}, retrying...")
                time.sleep(2)
            else:
                print(f"⚠️  Dynamic crumb fetch failed after 2 attempts, using fallback crumb")
    
    # Fallback to hardcoded crumb
    _yahoo_session_cache['crumb'] = _FALLBACK_CRUMB
    _yahoo_session_cache['cookies'] = None
    _yahoo_session_cache['fetched'] = True
    return _FALLBACK_CRUMB, None

def _yahoo_finance_fetch(symbol: str, start_date: str, end_date: str, interval: str) -> pd.DataFrame:
    """Fetch stock data from Yahoo Finance API with dynamic crumb and fallback"""
    import requests
    import time
    
    past_date = pd.to_datetime(start_date)
    end_date_dt = pd.to_datetime(end_date)
    time.sleep(1)  # Rate limiting

    # Get dynamic crumb (or fallback)
    crumb, cookies = _get_yahoo_crumb_dynamic()
    
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}'
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    payload = {
        'formatted': 'true',
        'crumb': crumb,
        'lang': 'en-GB',
        'region': 'GB',
        'includeAdjustedClose': 'true',
        'interval': interval,
        'period1': int(past_date.timestamp()),
        'period2': int(end_date_dt.timestamp()),
        'events': 'div|split',
        'useYfid': 'true',
        'corsDomain': 'uk.finance.yahoo.com'
    }

    response = requests.get(url, headers=headers, params=payload, cookies=cookies)
    response.raise_for_status()
    jsonData = response.json()

    # Check if valid data exists
    if ('chart' in jsonData and jsonData['chart']['result'] and 
        'indicators' in jsonData['chart']['result'][0] and 
        'timestamp' in jsonData['chart']['result'][0]):
        
        result = jsonData['chart']['result'][0]
        indicators = result['indicators']
        timestamps = result['timestamp']
        rows = indicators['adjclose'][0].copy()
        rows.update(indicators['quote'][0])
        df = pd.DataFrame(rows)

        # Add date column from timestamp
        df['date'] = pd.to_datetime(timestamps, unit='s').date
        df.set_index('date', inplace=True)
        
        # Clean up columns
        if 'close' in df.columns:
            df.drop(columns='close', inplace=True)
        if 'adjclose' in df.columns:
            df.rename(columns={'adjclose': 'close'}, inplace=True)
            
        # Drop rows where close price is NaN (incomplete data, e.g. market still open)
        if 'close' in df.columns:
            before_len = len(df)
            df = df.dropna(subset=['close'])
            dropped = before_len - len(df)
            if dropped > 0:
                print(f"   🧹 Dropped {dropped} row(s) with NaN close price for {symbol}")
            
        # Round to 2 decimal places
        df = df.round(2)
        return df
    else:
        print(f"⚠️ Could not retrieve valid data for {symbol} from Yahoo Finance")
        return pd.DataFrame()

def _convert_to_standard_format(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Yahoo Finance format to our standard OHLCV format"""
    if df.empty:
        return df
    
    # Create a copy to avoid modifying original
    df_standard = df.copy()
    
    # Ensure we have the required columns
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df_standard.columns:
            print(f"⚠️ Missing column {col} in Yahoo Finance data")
            return pd.DataFrame()
    
    # Convert date index to datetime if needed
    if not isinstance(df_standard.index, pd.DatetimeIndex):
        df_standard.index = pd.to_datetime(df_standard.index)
    
    # Sort by date
    df_standard = df_standard.sort_index()
    
    # Keep only required columns
    df_standard = df_standard[required_cols]
    
    return df_standard

def _get_cache_age(symbol: str) -> Optional[timedelta]:
    """Get the age of cached data for a symbol"""
    cache_path = os.path.join('price_cache', f"{symbol}_data.pkl")
    
    if os.path.exists(cache_path):
        try:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
            return datetime.now() - file_mtime
        except Exception:
            return None
    
    # Try alternative exchange
    alt_symbol = _get_alternative_exchange_symbol(symbol)
    if alt_symbol and alt_symbol != symbol:
        alt_cache_path = os.path.join('price_cache', f"{alt_symbol}_data.pkl")
        if os.path.exists(alt_cache_path):
            try:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(alt_cache_path))
                return datetime.now() - file_mtime
            except Exception:
                return None
    
    return None

def _load_from_cache_with_fallback(symbol: str) -> pd.DataFrame:
    """Load data from cache with automatic NSE/BSE fallback"""
    cache_dir = 'price_cache'
    
    # Try primary symbol first
    primary_cache = os.path.join(cache_dir, f"{symbol}_data.pkl")
    if os.path.exists(primary_cache):
        try:
            data = pd.read_pickle(primary_cache)
            if not data.empty:
                print(f"� Loaded cached data from {symbol}_data.pkl")
                return data
        except Exception as e:
            print(f"⚠️ Error loading primary cache for {symbol}: {e}")
    
    # Try alternative exchange symbol
    alt_symbol = _get_alternative_exchange_symbol(symbol)
    if alt_symbol and alt_symbol != symbol:
        alt_cache = os.path.join(cache_dir, f"{alt_symbol}_data.pkl")
        if os.path.exists(alt_cache):
            try:
                data = pd.read_pickle(alt_cache)
                if not data.empty:
                    print(f"📁 Using alternative exchange data: {symbol} → {alt_symbol}")
                    return data
            except Exception as e:
                print(f"⚠️ Error loading alternative cache for {alt_symbol}: {e}")
    
    return pd.DataFrame()

def _get_alternative_exchange_symbol(symbol: str) -> str:
    """Convert between NSE (.NS) and BSE (.BO) symbols"""
    if symbol.endswith('.NS'):
        return symbol.replace('.NS', '.BO')
    elif symbol.endswith('.BO'):
        return symbol.replace('.BO', '.NS')
    else:
        # If no exchange suffix, try BSE
        return f"{symbol}.BO"

# No synthetic data generation - only real data or cached data allowed

# Old create_fallback_data function removed - now using cache-first approach

class StreamlinedDataManager:
    """Streamlined data manager with integrated freshness checking and smart updating"""
    
    def __init__(self, cache_dir: str = 'price_cache'):
        self.cache_dir = cache_dir
        self.current_date = datetime.now()
        self.tolerance_hours = 6  # Data older than 6 hours is considered stale
        self.ensure_cache_dir()
        
    def ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            print(f"📁 Created cache directory: {self.cache_dir}")
        
    def ensure_latest_data(self, symbols: List[str] = None, force_full_update: bool = False) -> Dict[str, any]:
        """Main entry point: Ensure we always have the latest available data"""
        print("🚀 STREAMLINED DATA FETCH: Ensuring latest available data...")
        
        # Step 1: Quick freshness assessment
        freshness_status = self._quick_freshness_check(symbols)
        
        # Step 2: Determine update strategy
        if force_full_update or freshness_status['critical_update_needed']:
            print("🔄 CRITICAL UPDATE: Performing comprehensive data refresh...")
            return self._perform_full_update(symbols)
        elif freshness_status['selective_update_needed']:
            print("⚡ SELECTIVE UPDATE: Refreshing stale data only...")
            return self._perform_selective_update(freshness_status['stale_symbols'])
        else:
            print("✅ OPTIMAL: Data is current and fresh")
            return {'status': 'current', 'updated_symbols': [], 'total_symbols': len(symbols or [])}
            
    def _quick_freshness_check(self, symbols: List[str] = None) -> Dict[str, any]:
        """Quick assessment of data freshness without heavy processing"""
        if symbols is None:
            symbols = self._get_cached_symbols()
            
        stale_symbols = []
        missing_symbols = []
        
        for symbol in symbols:
            cache_file = os.path.join(self.cache_dir, f"{symbol}_data.pkl")
            
            if not os.path.exists(cache_file):
                missing_symbols.append(symbol)
            else:
                # Check file age
                file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
                if file_age.total_seconds() > (self.tolerance_hours * 3600):
                    stale_symbols.append(symbol)
                    
        critical_update_needed = len(missing_symbols) > len(symbols) * 0.1  # >10% missing
        selective_update_needed = len(stale_symbols) > 0 or len(missing_symbols) > 0
        
        return {
            'stale_symbols': stale_symbols,
            'missing_symbols': missing_symbols,
            'critical_update_needed': critical_update_needed,
            'selective_update_needed': selective_update_needed,
            'total_symbols': len(symbols)
        }
        
    def _perform_full_update(self, symbols: List[str]) -> Dict[str, any]:
        """Perform comprehensive data update for all symbols"""
        updated_symbols = []
        failed_symbols = []
        
        for symbol in symbols:
            try:
                data = self._fetch_fresh_data(symbol)
                if not data.empty:
                    self.save_to_cache(data, f"{symbol}_data.pkl")
                    updated_symbols.append(symbol)
                else:
                    failed_symbols.append(symbol)
            except Exception as e:
                print(f"⚠️ Failed to update {symbol}: {e}")
                failed_symbols.append(symbol)
                
        return {
            'status': 'full_update_completed',
            'updated_symbols': updated_symbols,
            'failed_symbols': failed_symbols,
            'total_symbols': len(symbols)
        }
        
    def _perform_selective_update(self, stale_symbols: List[str]) -> Dict[str, any]:
        """Perform selective update only for stale/missing symbols"""
        updated_symbols = []
        
        for symbol in stale_symbols:
            try:
                data = self._fetch_fresh_data(symbol)
                if not data.empty:
                    self.save_to_cache(data, f"{symbol}_data.pkl")
                    updated_symbols.append(symbol)
                    print(f"📈 Updated: {symbol}")
            except Exception as e:
                print(f"⚠️ Failed to update {symbol}: {e}")
                
        return {
            'status': 'selective_update_completed',
            'updated_symbols': updated_symbols,
            'total_symbols': len(stale_symbols)
        }
        
    def _get_cached_symbols(self) -> List[str]:
        """Get list of symbols from existing cache files"""
        symbols = []
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                if file.endswith('_data.pkl'):
                    symbol = file.replace('_data.pkl', '')
                    symbols.append(symbol)
        return symbols
        
    def _convert_nse_to_bse(self, symbol: str) -> str:
        """Convert NSE symbol (.NS) to BSE symbol (.BO)"""
        if symbol.endswith('.NS'):
            base_symbol = symbol.replace('.NS', '')
            return f"{base_symbol}.BO"
        return symbol
        
    def _convert_bse_to_nse(self, symbol: str) -> str:
        """Convert BSE symbol (.BO) to NSE symbol (.NS)"""
        if symbol.endswith('.BO'):
            base_symbol = symbol.replace('.BO', '')
            return f"{base_symbol}.NS"
        return symbol
        
    def _get_alternative_symbol(self, symbol: str) -> Optional[str]:
        """Get alternative exchange symbol for fallback"""
        if symbol.endswith('.NS'):
            return self._convert_nse_to_bse(symbol)
        elif symbol.endswith('.BO'):
            return self._convert_bse_to_nse(symbol)
        return None
        
    def _get_alternative_symbol(self, symbol: str) -> Optional[str]:
        """Get alternative exchange symbol for fallback"""
        if symbol.endswith('.NS'):
            return self._convert_nse_to_bse(symbol)
        elif symbol.endswith('.BO'):
            return self._convert_bse_to_nse(symbol)
        return None
        
    def _fetch_fresh_data(self, symbol: str) -> pd.DataFrame:
        """Fetch fresh data for a symbol with NSE to BSE fallback"""
        try:
            # Try primary symbol first
            print(f"📡 Fetching data for {symbol}...")
            data = get_stock_data_smart(symbol, force_update=True)
            
            if not data.empty:
                print(f"✅ Data fetched for {symbol}: {len(data)} records")
                return data
            else:
                print(f"⚠️ No data found for primary symbol {symbol}")
                
        except Exception as e:
            print(f"⚠️ Error fetching primary symbol {symbol}: {e}")
            
        # Try alternative exchange if primary fails
        alt_symbol = self._get_alternative_symbol(symbol)
        if alt_symbol and alt_symbol != symbol:
            try:
                print(f"🔄 Trying alternative exchange: {symbol} → {alt_symbol}")
                data = get_stock_data_smart(alt_symbol, force_update=True)
                
                if not data.empty:
                    print(f"✅ Data fetched from alternative exchange {alt_symbol}: {len(data)} records")
                    return data
                else:
                    print(f"⚠️ No data found for alternative symbol {alt_symbol}")
                    
            except Exception as e:
                print(f"⚠️ Error fetching alternative symbol {alt_symbol}: {e}")
                
        print(f"❌ Failed to fetch data for {symbol} on both exchanges")
        return pd.DataFrame()
            
    def save_to_cache(self, data: pd.DataFrame, filename: str):
        """Save data to cache file"""
        if data.empty:
            return
            
        filepath = os.path.join(self.cache_dir, filename)
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            print(f"💾 Cached data: {filename} ({len(data)} records)")
        except Exception as e:
            print(f"❌ Failed to cache {filename}: {e}")
            
    def get_stock_data(self, symbol: str) -> pd.DataFrame:
        """Get stock data for a symbol with exchange fallback - loads from cache if available"""
        # Try primary symbol cache first
        cache_file = os.path.join(self.cache_dir, f"{symbol}_data.pkl")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                if not data.empty:
                    return data
            except Exception as e:
                print(f"⚠️ Error loading cached data for {symbol}: {e}")
                
        # Only check BSE cache if NSE cache not found and symbol is NSE
        if symbol.endswith('.NS'):
            alt_symbol = self._get_alternative_symbol(symbol)
            alt_cache_file = os.path.join(self.cache_dir, f"{alt_symbol}_data.pkl")
            if os.path.exists(alt_cache_file):
                try:
                    with open(alt_cache_file, 'rb') as f:
                        data = pickle.load(f)
                    if not data.empty:
                        print(f"📊 Using BSE cached data: {symbol} → {alt_symbol}")
                        return data
                except Exception as e:
                    print(f"⚠️ Error loading BSE cached data for {alt_symbol}: {e}")
                
        # If no cache or error, return empty DataFrame
        return pd.DataFrame()
        
    def get_multiple_stocks_data(self, symbols: List[str]) -> pd.DataFrame:
        """Get data for multiple symbols and combine into one DataFrame"""
        combined_data = []
        
        for symbol in symbols:
            data = self.get_stock_data(symbol)
            if not data.empty:
                data['Symbol'] = symbol
                combined_data.append(data)
                
        if combined_data:
            return pd.concat(combined_data, ignore_index=True)
        else:
            return pd.DataFrame()

class DataManager:
    """Enhanced data management with smart fetching capabilities"""
    
    def __init__(self, cache_dir: str = 'price_cache'):
        self.cache_dir = cache_dir
        self.ensure_cache_dir()
        
    def ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            print(f"📁 Created cache directory: {self.cache_dir}")
    
    def get_stock_data(self, symbol: str, force_update: bool = False) -> pd.DataFrame:
        """Get stock data for a symbol - only loads from cache when force_update=False"""
        try:
            # Check if we have cached data
            cache_filename = f"{symbol}_data.pkl"
            cached_data = self.load_from_cache(cache_filename)
            
            # If force_update, always fetch fresh data (used by update_portfolio_data.py)
            if force_update:
                print(f"🔄 Force updating data for {symbol}")
                data = self._fetch_fresh_data(symbol)
                if not data.empty:
                    print(f"✅ Retrieved {len(data)} records for {symbol}")
                    self.save_to_cache(data, cache_filename)
                    return data
                else:
                    # Fallback to cached data if available
                    if not cached_data.empty:
                        print(f"⚠️  Using cached data as fallback for {symbol}")
                        return self._ensure_proper_index(cached_data)
                    print(f"❌ No data available for {symbol}")
                    return pd.DataFrame()
            
            # When force_update=False, ONLY use cached data (no fetching, no delta updates)
            # This is the behavior for main_pf_app.py analysis - NO NETWORK CALLS
            if cached_data.empty:
                print(f"⚠️  No cached data found for {symbol}")
                return pd.DataFrame()
            
            # Use cached data as-is without any updates
            cached_data = self._ensure_proper_index(cached_data)
            return cached_data
                
        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {e}")
            # Try to use cached data as fallback
            cache_filename = f"{symbol}_data.pkl"
            cached_data = self.load_from_cache(cache_filename)
            if not cached_data.empty:
                print(f"♻️  Using cached data as fallback for {symbol}")
                return self._ensure_proper_index(cached_data)
            return pd.DataFrame()
    
    def _ensure_proper_index(self, data: pd.DataFrame) -> pd.DataFrame:
        """Ensure data has proper datetime index and clean NaN close rows"""
        if 'Date' in data.columns and not isinstance(data.index, pd.DatetimeIndex):
            data = data.set_index('Date')
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        # Drop rows where close is NaN (incomplete data from market-open fetches)
        if 'close' in data.columns:
            data = data.dropna(subset=['close'])
        return data.sort_index()
    
    def _get_alternative_symbol(self, symbol: str) -> str:
        """Convert between NSE (.NS) and BSE (.BO) symbols dynamically"""
        if symbol.endswith('.NS'):
            # Convert NSE to BSE
            base_symbol = symbol[:-3]  # Remove .NS
            return f"{base_symbol}.BO"
        elif symbol.endswith('.BO'):
            # Convert BSE to NSE
            base_symbol = symbol[:-3]  # Remove .BO
            return f"{base_symbol}.NS"
        else:
            # If no exchange suffix, assume NSE and try BSE
            return f"{symbol}.BO"
    
    def _fetch_fresh_data(self, symbol: str) -> pd.DataFrame:
        """Fetch fresh 3-year data for a symbol with NSE to BSE fallback"""
        current_date = datetime.now()
        three_years_ago = current_date - timedelta(days=365 * 3)
        
        try:
            # Try primary symbol first
            print(f"📡 Fetching 3-year data for {symbol}...")
            data = get_stock_data_smart(symbol, force_update=True)
            
            if not data.empty:
                print(f"✅ Data fetched for {symbol}: {len(data)} records")
                return data
            else:
                print(f"⚠️ No data found for primary symbol {symbol}")
                
        except Exception as e:
            print(f"⚠️ Error fetching {symbol}: {e}, trying BSE fallback...")
            
        # Only try BSE fallback if NSE failed and symbol is NSE
        if symbol.endswith('.NS'):
            alt_symbol = self._get_alternative_symbol(symbol)
            try:
                print(f"🔄 Trying BSE fallback: {symbol} → {alt_symbol}")
                data = get_stock_data_smart(alt_symbol, force_update=True)
                
                if not data.empty:
                    print(f"✅ BSE fallback successful for {alt_symbol}: {len(data)} records")
                    return data
                else:
                    print(f"⚠️ BSE fallback also failed for {alt_symbol}")
                    
            except Exception as e:
                print(f"⚠️ BSE fallback error for {alt_symbol}: {e}")
                
        print(f"❌ Failed to fetch data for {symbol} on both exchanges")
        return pd.DataFrame()
        return data
    
    def _fetch_delta_update(self, symbol: str, cached_data: pd.DataFrame, latest_date: pd.Timestamp, current_date: datetime) -> pd.DataFrame:
        """Fetch only missing data (delta) and merge with cached data"""
        try:
            # Calculate missing date range
            start_missing = latest_date + timedelta(days=1)
            
            if start_missing.date() >= current_date.date():
                print(f"📊 No new data needed for {symbol}")
                return self._ensure_proper_index(cached_data)
            
            # Fetch only missing data
            missing_data = get_stock_data_smart(symbol, force_update=True)
            
            if missing_data.empty:
                return self._ensure_proper_index(cached_data)
            
            # Ensure both datasets have proper datetime index
            cached_data = self._ensure_proper_index(cached_data)
            missing_data = self._ensure_proper_index(missing_data)
            
            # Combine cached and new data
            combined_data = pd.concat([cached_data, missing_data]).sort_index()
            
            # Keep only last 3 years to maintain size limit
            three_years_ago = current_date - timedelta(days=365 * 3)
            combined_data = combined_data[combined_data.index >= three_years_ago]
            
            # Remove duplicates if any
            combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
            
            print(f"📊 Added {len(missing_data)} new records for {symbol} (delta update)")
            
            # Save updated data to cache
            cache_filename = f"{symbol}_data.pkl"
            self.save_to_cache(combined_data, cache_filename)
            
            return combined_data
            
        except Exception as e:
            print(f"⚠️  Error in delta update for {symbol}: {e}")
            # Fallback to cached data
            return self._ensure_proper_index(cached_data)
    
    def get_multiple_stocks_data(self, symbols: List[str], force_update: bool = False) -> pd.DataFrame:
        """Get data for multiple stocks and combine"""
        # Use individual files as single source of truth - build consolidated view on demand
        
        print(f"🔄 Fetching data for {len(symbols)} stocks...")
        all_data = []
        
        for symbol in symbols:
            stock_data = self.get_stock_data(symbol, force_update)
            if not stock_data.empty:
                # Reset index to get date as a column (pandas creates lowercase 'date' from index)
                stock_data_copy = stock_data.reset_index()
                stock_data_copy['Symbol'] = symbol
                all_data.append(stock_data_copy)
        
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            print(f"✅ Combined data for {len(symbols)} stocks: {len(combined_data)} records")
            
            # Individual files are already saved - using single source of truth approach
            return combined_data
        else:
            # Try to use any existing cache as fallback
            cached_combined = self.load_from_cache(combined_cache_filename)
            if not cached_combined.empty:
                print(f"♻️  Using existing cache: {len(cached_combined)} records")
                return cached_combined
            
            print("❌ No data available")
            return pd.DataFrame()
    
    def _is_combined_cache_valid(self, cached_data: pd.DataFrame, symbols: List[str]) -> bool:
        """Check if combined cache is valid and recent"""
        try:
            # Check if all symbols are present
            cached_symbols = set(cached_data['Symbol'].unique())
            required_symbols = set(symbols)
            
            if not required_symbols.issubset(cached_symbols):
                missing_symbols = required_symbols - cached_symbols
                print(f"📊 Missing symbols from cache: {missing_symbols}, updating...")
                return False
            
            # Check extra symbols (cleanup needed)
            extra_symbols = cached_symbols - required_symbols
            if extra_symbols:
                print(f"📊 Extra symbols in cache: {extra_symbols}, updating for cleanup...")
                return False
            
            # Check data freshness - be stricter for better data quality
            latest_date = pd.to_datetime(cached_data['Date']).max()
            current_date = datetime.now()
            days_old = (current_date - latest_date).days
            
            # Always use fresh data (max 1 day old) for accurate analysis
            max_days = 1
            
            if days_old > max_days:
                print(f"📊 Combined cache is {days_old} days old (max {max_days} allowed), updating...")
                return False
            
            # Check data completeness - ensure we have recent 3-year range
            oldest_date = pd.to_datetime(cached_data['Date']).min()
            three_years_ago = current_date - timedelta(days=365 * 3)
            
            if oldest_date > three_years_ago:
                print(f"📊 Cache doesn't have full 3-year range, updating...")
                return False
            
            print(f"✅ Combined cache is valid and fresh (last updated {days_old} days ago)")
            return True
            
        except Exception as e:
            print(f"⚠️  Error validating combined cache: {e}")
            return False
    
    def save_to_cache(self, data: pd.DataFrame, filename: str):
        """Save data to cache"""
        try:
            cache_path = os.path.join(self.cache_dir, filename)
            
            if filename.endswith('.pkl'):
                data.to_pickle(cache_path)
            elif filename.endswith('.csv'):
                data.to_csv(cache_path, index=False)
            else:
                # Default to pickle
                data.to_pickle(cache_path + '.pkl')
            
            print(f"💾 Data saved to cache: {cache_path}")
            
        except Exception as e:
            print(f"⚠️  Could not save to cache: {e}")
    
    def load_from_cache(self, filename: str) -> pd.DataFrame:
        """Load data from cache"""
        try:
            cache_path = os.path.join(self.cache_dir, filename)
            
            if not os.path.exists(cache_path):
                return pd.DataFrame()
            
            if filename.endswith('.pkl'):
                data = pd.read_pickle(cache_path)
            elif filename.endswith('.csv'):
                data = pd.read_csv(cache_path)
            else:
                # Try pickle first
                try:
                    data = pd.read_pickle(cache_path + '.pkl')
                except:
                    data = pd.read_csv(cache_path + '.csv')
            
            print(f"📂 Loaded from cache: {cache_path}")
            return data
            
        except Exception as e:
            print(f"⚠️  Could not load from cache: {e}")
            return pd.DataFrame()
    
    def get_cache_info(self) -> Dict:
        """Get information about cached files with data statistics"""
        cache_info = {
            'cache_dir': self.cache_dir,
            'total_files': 0,
            'files': [],
            'data_statistics': {}
        }
        
        try:
            if os.path.exists(self.cache_dir):
                files = os.listdir(self.cache_dir)
                cache_info['total_files'] = len(files)
                
                for file in files:
                    file_path = os.path.join(self.cache_dir, file)
                    file_size = os.path.getsize(file_path)
                    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    file_info = {
                        'name': file,
                        'size_kb': round(file_size / 1024, 2),
                        'modified': file_modified.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Add data statistics for stock data files
                    if file.endswith('_data.pkl'):
                        try:
                            data = pd.read_pickle(file_path)
                            if not data.empty:
                                date_range = self._get_date_range(data)
                                file_info['records'] = len(data)
                                file_info['date_range'] = date_range
                                file_info['data_span_days'] = date_range['days_span']
                        except:
                            pass
                    
                    cache_info['files'].append(file_info)
                
                # Calculate total cache statistics
                cache_info['data_statistics'] = self._calculate_cache_statistics(cache_info['files'])
        
        except Exception as e:
            print(f"⚠️  Error getting cache info: {e}")
        
        return cache_info
    
    def _get_date_range(self, data: pd.DataFrame) -> Dict:
        """Get date range information from data"""
        try:
            if 'Date' in data.columns:
                dates = pd.to_datetime(data['Date'])
            elif isinstance(data.index, pd.DatetimeIndex):
                dates = data.index
            else:
                dates = pd.to_datetime(data.index)
            
            min_date = dates.min()
            max_date = dates.max()
            days_span = (max_date - min_date).days
            
            return {
                'start_date': min_date.strftime('%Y-%m-%d'),
                'end_date': max_date.strftime('%Y-%m-%d'),
                'days_span': days_span
            }
        except:
            return {'start_date': 'N/A', 'end_date': 'N/A', 'days_span': 0}
    
    def _calculate_cache_statistics(self, files: List[Dict]) -> Dict:
        """Calculate overall cache statistics"""
        stats = {
            'total_size_mb': 0,
            'stock_data_files': 0,
            'total_records': 0,
            'avg_data_span_days': 0
        }
        
        data_files = []
        for file_info in files:
            stats['total_size_mb'] += file_info['size_kb'] / 1024
            
            if file_info['name'].endswith('_data.pkl'):
                stats['stock_data_files'] += 1
                if 'records' in file_info:
                    stats['total_records'] += file_info['records']
                    data_files.append(file_info)
        
        if data_files:
            avg_span = sum(f.get('data_span_days', 0) for f in data_files) / len(data_files)
            stats['avg_data_span_days'] = round(avg_span, 1)
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        return stats
    
    def clear_cache(self, older_than_days: int = None, pattern: str = None):
        """Clear cache files with intelligent filtering"""
        try:
            if not os.path.exists(self.cache_dir):
                print("📁 Cache directory doesn't exist")
                return
            
            files = os.listdir(self.cache_dir)
            removed_count = 0
            total_size_removed = 0
            
            for file in files:
                file_path = os.path.join(self.cache_dir, file)
                should_remove = False
                
                # Check age filter
                if older_than_days is not None:
                    file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_age.days >= older_than_days:
                        should_remove = True
                
                # Check pattern filter
                if pattern is not None:
                    if pattern in file:
                        should_remove = True
                
                # If no filters specified, remove all
                if older_than_days is None and pattern is None:
                    should_remove = True
                
                if should_remove:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    removed_count += 1
                    total_size_removed += file_size
            
            size_mb = round(total_size_removed / (1024 * 1024), 2)
            print(f"🗑️  Removed {removed_count} files from cache ({size_mb} MB freed)")
            
        except Exception as e:
            print(f"⚠️  Error clearing cache: {e}")
    
    def optimize_cache(self):
        """Optimize cache by removing old delta files and maintaining 3-year limit"""
        try:
            print("🔧 Optimizing cache...")
            
            # Remove delta files (they're temporary)
            self.clear_cache(pattern="delta")
            
            # Check each stock data file for 3-year limit
            cache_info = self.get_cache_info()
            for file_info in cache_info['files']:
                if file_info['name'].endswith('_data.pkl'):
                    self._enforce_three_year_limit(file_info['name'])
            
            print("✅ Cache optimization completed")
            
        except Exception as e:
            print(f"⚠️  Error optimizing cache: {e}")
    
    def _enforce_three_year_limit(self, filename: str):
        """Ensure stock data file contains only 3 years of data"""
        try:
            file_path = os.path.join(self.cache_dir, filename)
            data = pd.read_pickle(file_path)
            
            if data.empty:
                return
            
            # Ensure proper datetime index
            data = self._ensure_proper_index(data)
            
            # Keep only last 3 years
            three_years_ago = datetime.now() - timedelta(days=365 * 3)
            filtered_data = data[data.index >= three_years_ago]
            
            # Only save if we actually removed data
            if len(filtered_data) < len(data):
                filtered_data.to_pickle(file_path)
                removed_records = len(data) - len(filtered_data)
                print(f"📊 Trimmed {removed_records} old records from {filename}")
                
        except Exception as e:
            print(f"⚠️  Error enforcing 3-year limit for {filename}: {e}")

def _calculate_dynamic_base_price(symbol: str) -> float:
    """Calculate dynamic base price based on symbol characteristics"""
    # Remove exchange suffix for analysis
    base_symbol = symbol.replace('.NS', '').replace('.BO', '')
    
    # Use symbol hash for consistent but varied pricing
    symbol_hash = hash(base_symbol) % 1000
    
    # Different price ranges based on symbol patterns
    if base_symbol.startswith('3B') or 'MICRO' in base_symbol or 'SMALL' in base_symbol:
        # Small cap stocks: 50-200 range
        return 50 + (symbol_hash % 150)
    elif any(x in base_symbol.upper() for x in ['ETF', 'INDEX', 'FUND']):
        # ETFs and Index funds: 50-150 range
        return 50 + (symbol_hash % 100)
    elif len(base_symbol) <= 4 and base_symbol.isalpha():
        # Large cap stocks (short names): 200-2000 range
        return 200 + (symbol_hash % 1800)
    elif 'BANK' in base_symbol or 'FINANCIAL' in base_symbol:
        # Banking/Financial stocks: 100-500 range
        return 100 + (symbol_hash % 400)
    elif 'TECH' in base_symbol or 'IT' in base_symbol or 'SOFT' in base_symbol:
        # Tech stocks: 300-800 range
        return 300 + (symbol_hash % 500)
    else:
        # Default mid-cap range: 100-400
        return 100 + (symbol_hash % 300)

def _calculate_dynamic_base_price(symbol: str) -> float:
    """Calculate dynamic base price based on symbol characteristics"""
    # Remove exchange suffix for analysis
    base_symbol = symbol.replace('.NS', '').replace('.BO', '')
    
    # Use symbol hash for consistent but varied pricing
    symbol_hash = hash(base_symbol) % 1000
    
    # Different price ranges based on symbol patterns
    if base_symbol.startswith('3B') or 'MICRO' in base_symbol or 'SMALL' in base_symbol:
        # Small cap stocks: 50-200 range
        return 50 + (symbol_hash % 150)
    elif any(x in base_symbol.upper() for x in ['ETF', 'INDEX', 'FUND']):
        # ETFs and Index funds: 50-150 range
        return 50 + (symbol_hash % 100)
    elif len(base_symbol) <= 4 and base_symbol.isalpha():
        # Large cap stocks (short names): 200-2000 range
        return 200 + (symbol_hash % 1800)
    elif 'BANK' in base_symbol or 'FINANCIAL' in base_symbol:
        # Banking/Financial stocks: 100-500 range
        return 100 + (symbol_hash % 400)
    elif 'TECH' in base_symbol or 'IT' in base_symbol or 'SOFT' in base_symbol:
        # Tech stocks: 300-800 range
        return 300 + (symbol_hash % 500)
    else:
        # Default mid-cap range: 100-400
        return 100 + (symbol_hash % 300)

def calculate_percentage_change(new_value: float, old_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0
    return ((new_value - old_value) / old_value) * 100

# Convenience functions for streamlined data fetching
def ensure_latest_data_for_portfolio(portfolio_file: str = None, force_update: bool = False) -> Dict[str, any]:
    """Streamlined function to ensure latest data for all portfolio symbols"""
    if portfolio_file is None:
        from config_manager import get_config
        portfolio_file = get_config().get_setting('system_settings.portfolio_file', 'dpsr_report.xls.xlsx')
    print("🎯 STREAMLINED DATA FETCH: Ensuring latest data for portfolio...")
    
    # Load portfolio to get symbols
    try:
        if portfolio_file.endswith('.xlsx') or portfolio_file.endswith('.xls'):
            portfolio_data = pd.read_excel(portfolio_file)
        else:
            portfolio_data = pd.read_csv(portfolio_file)
            
        # Handle different column names for symbols
        symbol_column = None
        for col in ['Symbol', 'ScripCode', 'scripcode', 'symbol', 'Stock', 'stock']:
            if col in portfolio_data.columns:
                symbol_column = col
                break
                
        if symbol_column is None:
            available_cols = list(portfolio_data.columns)
            return {'status': 'error', 'message': f'No symbol column found. Available columns: {available_cols}'}
            
        # Get base symbols
        base_symbols = portfolio_data[symbol_column].tolist()
        
        # Convert to proper exchange format (add .NS suffix if needed)
        symbols = []
        for symbol in base_symbols:
            if pd.isna(symbol):
                continue
            symbol = str(symbol).strip()
            if symbol and not symbol.endswith(('.NS', '.BO')):
                # Default to NSE, but we'll have BSE fallback
                symbol = f"{symbol}.NS"
            symbols.append(symbol)
            
        print(f"📊 Portfolio loaded: {len(symbols)} symbols from '{symbol_column}' column")
        print(f"📈 First few symbols: {symbols[:5]}")
        
    except Exception as e:
        print(f"❌ Error loading portfolio: {e}")
        return {'status': 'error', 'message': str(e)}
        
    # Use streamlined data manager
    manager = StreamlinedDataManager()
    result = manager.ensure_latest_data(symbols, force_full_update=force_update)
    
    print(f"✅ Data fetch completed: {result['status']}")
    if 'updated_symbols' in result:
        print(f"🔄 Updated symbols: {len(result['updated_symbols'])}/{result['total_symbols']}")
        
    return result

def quick_data_freshness_check() -> Dict[str, any]:
    """Quick check of data freshness without heavy processing"""
    manager = StreamlinedDataManager()
    symbols = manager._get_cached_symbols()
    
    if not symbols:
        return {'status': 'no_data', 'message': 'No cached data found'}
        
    freshness = manager._quick_freshness_check(symbols)
    
    status = 'fresh'
    if freshness['critical_update_needed']:
        status = 'critical_update_needed'
    elif freshness['selective_update_needed']:
        status = 'update_needed'
        
    return {
        'status': status,
        'total_symbols': freshness['total_symbols'],
        'stale_symbols': len(freshness['stale_symbols']),
        'missing_symbols': len(freshness['missing_symbols'])
    }

if __name__ == "__main__":
    # Test the streamlined data manager
    print("🧪 Testing Streamlined Data Manager...")
    
    # Test quick freshness check
    freshness = quick_data_freshness_check()
    print(f"📊 Freshness status: {freshness}")
    
    # Test portfolio data fetch
    from config_manager import get_config
    _pf = get_config().get_setting('system_settings.portfolio_file', 'dpsr_report.xls.xlsx')
    if os.path.exists(_pf):
        result = ensure_latest_data_for_portfolio()
        print(f"🎯 Portfolio data fetch result: {result}")
    
    # Test regular data manager
    print("\n🧪 Testing Regular Data Manager...")
    dm = DataManager()
    
    # Test with a few symbols
    test_symbols = ['AEROFLEX.NS', 'WIPRO.NS']
    
    for symbol in test_symbols:
        data = dm.get_stock_data(symbol)
        if not data.empty:
            print(f"📊 {symbol}: {len(data)} records")
            print(f"   Latest price: ₹{data['close'].iloc[-1]:.2f}")
            print(f"   Date range: {data.index[0]} to {data.index[-1]}")
        else:
            print(f"❌ No data for {symbol}")
    
    # Test cache info
    cache_info = dm.get_cache_info()
    print(f"\n📁 Cache info: {cache_info['total_files']} files")


def get_index_constituents(index_symbol: str) -> pd.DataFrame:
    """
    Fetch constituents of an index if available
    
    Note: This is a placeholder function. Index constituent data is not readily available
    from free data sources. You may need to:
    1. Use a premium data service (e.g., NSE/BSE official APIs, Bloomberg, etc.)
    2. Manually maintain a CSV file with index constituents
    3. Use web scraping (subject to terms of service)
    
    Args:
        index_symbol: Index symbol (e.g., ^NSEI, ^CNXSC)
        
    Returns:
        DataFrame with columns: ['Symbol', 'Name', 'Sector', 'Weight'] or empty DataFrame
    """
    print(f"🔍 Attempting to fetch constituents for {index_symbol}...")
    
    # Mapping of index symbols to their common names
    index_mapping = {
        '^NSEI': 'NIFTY 50',
        '^CNX100': 'NIFTY 100',
        '^CNXSC': 'NIFTY SMALLCAP 100',
        '^CNXMID': 'NIFTY MIDCAP 100',
        '^CRSLDX': 'NIFTY 500',
        '^BSESN': 'SENSEX'
    }
    
    index_name = index_mapping.get(index_symbol, index_symbol)
    
    # Check if a manual CSV file exists
    constituents_file = f'index_constituents/{index_symbol.replace("^", "").replace(".", "_")}_constituents.csv'
    
    if os.path.exists(constituents_file):
        try:
            df = pd.read_csv(constituents_file)
            print(f"✅ Loaded {len(df)} constituents for {index_name} from {constituents_file}")
            return df
        except Exception as e:
            print(f"❌ Error loading constituents file: {e}")
    
    # Placeholder: Return empty DataFrame with expected structure
    print(f"⚠️  No constituent data available for {index_name}")
    print(f"💡 To add constituent data:")
    print(f"   1. Create directory: index_constituents/")
    print(f"   2. Add CSV file: {constituents_file}")
    print(f"   3. Include columns: Symbol, Name, Sector, Weight (optional)")
    print(f"   4. Example: RELIANCE.NS, Reliance Industries, Energy, 10.5")
    
    return pd.DataFrame(columns=['Symbol', 'Name', 'Sector', 'Weight'])


def update_benchmark_data(force_update: bool = False) -> bool:
    """
    Update all configured benchmark indices data
    
    Args:
        force_update: If True, force update even if data is fresh
        
    Returns:
        True if all benchmarks updated successfully
    """
    from config_manager import get_config
    
    print("🔍 Updating benchmark data...")
    
    config = get_config()
    benchmark_config = config.get_benchmark_config()
    
    # Collect all benchmarks to update
    benchmarks_to_update = {
        'Primary Benchmark': benchmark_config.primary_benchmark,
        'RS Benchmark': benchmark_config.rs_benchmark_index
    }
    
    # Add alternative benchmarks
    for name, symbol in benchmark_config.alternative_benchmarks.items():
        benchmarks_to_update[name] = symbol
    
    success = True
    updated_count = 0
    
    for name, symbol in benchmarks_to_update.items():
        try:
            print(f"\n📊 Updating {name}: {symbol}")
            data = get_stock_data_smart(symbol, force_update=force_update)
            
            if not data.empty:
                print(f"✅ {name} updated: {len(data)} records")
                updated_count += 1
            else:
                print(f"⚠️  No data retrieved for {name}")
                success = False
        except Exception as e:
            print(f"❌ Error updating {name}: {e}")
            success = False
    
    print(f"\n{'✅' if success else '⚠️'} Updated {updated_count}/{len(benchmarks_to_update)} benchmarks")
    return success
