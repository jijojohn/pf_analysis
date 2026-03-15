#!/usr/bin/env python3
"""
Smart Data Updater
Efficiently checks and updates only stale or missing stock data
"""

import pandas as pd
import numpy as np
import os
import pickle
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

class SmartDataUpdater:
    """Smart data updater that only fetches missing or stale data"""
    
    def __init__(self, cache_dir: str = 'price_cache'):
        self.cache_dir = cache_dir
        self.ensure_cache_dir()
        
    def ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def check_data_freshness(self) -> Dict[str, bool]:
        """Check which symbols need data updates based on age and completeness"""
        results = {}
        
        # Check individual stock files (single source of truth)
        individual_files = [f for f in os.listdir(self.cache_dir) if f.endswith('_data.pkl')]
        if not individual_files:
            print("📡 No individual stock files found - full update needed")
            return {'full_update_needed': True}
        
        try:
            # Check freshness of individual files by sampling a few
            sample_files = individual_files[:10]  # Check first 10 files
            oldest_date = None
            
            for file in sample_files:
                file_path = os.path.join(self.cache_dir, file)
                try:
                    data = pd.read_pickle(file_path)
                    if not data.empty and hasattr(data.index, 'max'):
                        file_latest = data.index.max()
                        if oldest_date is None or file_latest < oldest_date:
                            oldest_date = file_latest
                except:
                    continue
            
            if oldest_date is None:
                print("📡 Could not determine data freshness - update recommended")
                return {'update_needed': True}
            
            # Check data freshness from sample
            # Convert oldest_date to datetime if it's a pandas Timestamp
            if hasattr(oldest_date, 'to_pydatetime'):
                oldest_date = oldest_date.to_pydatetime()
            elif isinstance(oldest_date, date) and not isinstance(oldest_date, datetime):
                oldest_date = datetime.combine(oldest_date, datetime.min.time())
            days_old = (datetime.now() - oldest_date).days
            
            print(f"📅 Sample data is {days_old} days old (oldest sampled: {oldest_date.strftime('%Y-%m-%d')})")
            
            # If data is recent (less than 2 days old) and we have individual files
            if days_old < 2 and len(individual_files) > 100:
                print("✅ Data is fresh - no update needed")
                return {'update_needed': False}
            elif days_old > 7:
                print("🔄 Data is stale - full update recommended")
                return {'full_update_needed': True}
            else:
                print("⚡ Data needs refresh - standard update")
                return {'update_needed': True}
                
        except Exception as e:
            print(f"❌ Error checking data freshness: {e}")
            return {'full_update_needed': True}
    
    def smart_update_data(self, symbols: List[str], force_update: bool = False) -> bool:
        """Smart update that only refreshes what's needed"""
        
        if force_update:
            print("🔄 Force update requested - updating all data")
            return self._full_data_update(symbols)
        
        # Check data freshness
        freshness_check = self.check_data_freshness()
        
        if freshness_check.get('update_needed') == False:
            print("✅ Data is current - skipping update")
            return True
        elif freshness_check.get('quick_update_needed'):
            print("⚡ Performing quick incremental update - missing data only")
            return self._update_missing_data_only(symbols, freshness_check.get('days_old', 1))
        else:
            print("📡 Performing targeted update - missing and stale data only")
            return self._update_missing_and_stale_data(symbols)
    
    def _quick_data_update(self, symbols: List[str], days_old: int) -> bool:
        """Quick update - only add recent data"""
        try:
            historical_file = os.path.join(self.cache_dir, 'pf_historical_data.pkl')
            
            if os.path.exists(historical_file):
                existing_data = pd.read_pickle(historical_file)
                
                # For this system using fallback data, we just verify completeness
                if len(existing_data) > 100000 and 'Symbol' in existing_data.columns:
                    existing_symbols = set(existing_data['Symbol'].unique())
                    required_symbols = set(symbols)
                    
                    missing_symbols = required_symbols - existing_symbols
                    
                    if missing_symbols:
                        print(f"📊 Adding data for {len(missing_symbols)} missing symbols")
                        self._add_missing_symbols(missing_symbols, existing_data)
                    else:
                        print("✅ All symbols present - no update needed")
                    
                    return True
            
            # Fallback to full update
            return self._full_data_update(symbols)
            
        except Exception as e:
            print(f"❌ Quick update failed: {e}")
            return self._full_data_update(symbols)
    
    def _add_missing_symbols(self, missing_symbols: List[str], existing_data: pd.DataFrame) -> bool:
        """Add data for missing symbols only"""
        try:
            from data_fetcher import get_stock_data_smart
            
            new_data_frames = []
            
            for symbol in missing_symbols:
                print(f"  📊 Generating data for {symbol}")
                symbol_data = get_stock_data_smart(symbol, force_update=True)
                
                if not symbol_data.empty:
                    # Reset index to match existing data format
                    symbol_data = symbol_data.reset_index()
                    symbol_data['Symbol'] = symbol
                    new_data_frames.append(symbol_data)
            
            if new_data_frames:
                new_data = pd.concat(new_data_frames, ignore_index=True)
                combined_data = pd.concat([existing_data, new_data], ignore_index=True)
                
                # Save updated data
                historical_file = os.path.join(self.cache_dir, 'pf_historical_data.pkl')
                combined_data.to_pickle(historical_file)
                print(f"💾 Updated historical data with {len(new_data)} new records")
                
            return True
            
        except Exception as e:
            print(f"❌ Error adding missing symbols: {e}")
            return False

    def _update_missing_data_only(self, symbols: List[str], days_old: int) -> bool:
        """Update only missing data - most efficient approach"""
        try:
            historical_file = os.path.join(self.cache_dir, 'pf_historical_data.pkl')
            
            if os.path.exists(historical_file):
                existing_data = pd.read_pickle(historical_file)
                
                if not existing_data.empty and 'Symbol' in existing_data.columns:
                    existing_symbols = set(existing_data['Symbol'].unique())
                    required_symbols = set(symbols)
                    
                    missing_symbols = required_symbols - existing_symbols
                    
                    if missing_symbols:
                        print(f"📊 Updating {len(missing_symbols)} missing symbols only")
                        return self._add_missing_symbols(list(missing_symbols), existing_data)
                    else:
                        print("✅ All symbols present - no missing data to update")
                        return True
            
            # If no existing data, do minimal update
            print("📡 No existing data - creating minimal dataset")
            return self._create_minimal_dataset(symbols)
            
        except Exception as e:
            print(f"❌ Missing data update failed: {e}")
            return False

    def _update_missing_and_stale_data(self, symbols: List[str]) -> bool:
        """Update missing and significantly stale data only"""
        try:
            historical_file = os.path.join(self.cache_dir, 'pf_historical_data.pkl')
            
            if os.path.exists(historical_file):
                existing_data = pd.read_pickle(historical_file)
                
                if not existing_data.empty and 'Symbol' in existing_data.columns:
                    existing_symbols = set(existing_data['Symbol'].unique())
                    required_symbols = set(symbols)
                    
                    missing_symbols = required_symbols - existing_symbols
                    
                    # Check for symbols with very old data (>7 days)
                    stale_symbols = self._identify_stale_symbols(existing_data, threshold_days=7)
                    
                    symbols_to_update = missing_symbols.union(stale_symbols)
                    
                    if symbols_to_update:
                        print(f"📊 Updating {len(symbols_to_update)} symbols (missing: {len(missing_symbols)}, stale: {len(stale_symbols)})")
                        return self._update_specific_symbols(list(symbols_to_update), existing_data)
                    else:
                        print("✅ All data is sufficiently current")
                        return True
            
            # If no existing data, create minimal dataset
            return self._create_minimal_dataset(symbols)
            
        except Exception as e:
            print(f"❌ Targeted update failed: {e}")
            return False

    def _identify_stale_symbols(self, data: pd.DataFrame, threshold_days: int = 7) -> set:
        """Identify symbols with stale data"""
        stale_symbols = set()
        
        try:
            if 'Date' in data.columns and 'Symbol' in data.columns:
                # Group by symbol and find the latest date for each
                latest_dates = data.groupby('Symbol')['Date'].max()
                
                current_time = datetime.now()
                threshold = timedelta(days=threshold_days)
                
                for symbol, latest_date in latest_dates.items():
                    if isinstance(latest_date, str):
                        latest_date = pd.to_datetime(latest_date)
                    
                    # Convert to datetime if it's a pandas Timestamp or date object
                    if hasattr(latest_date, 'to_pydatetime'):
                        latest_date = latest_date.to_pydatetime()
                    elif isinstance(latest_date, pd.Timestamp):
                        latest_date = latest_date.to_pydatetime()
                    
                    # Handle datetime.date objects by converting to datetime
                    if isinstance(latest_date, date) and not isinstance(latest_date, datetime):
                        latest_date = datetime.combine(latest_date, datetime.min.time())
                    
                    if current_time - latest_date > threshold:
                        stale_symbols.add(symbol)
            
        except Exception as e:
            print(f"⚠️ Error identifying stale symbols: {e}")
        
        return stale_symbols

    def _update_specific_symbols(self, symbols_to_update: List[str], existing_data: pd.DataFrame) -> bool:
        """Update specific symbols only"""
        try:
            from data_fetcher import get_stock_data_smart
            
            # Remove old data for symbols being updated
            if 'Symbol' in existing_data.columns:
                existing_data = existing_data[~existing_data['Symbol'].isin(symbols_to_update)]
            
            new_data_frames = []
            
            for symbol in symbols_to_update:
                print(f"  🔄 Updating data for {symbol}")
                symbol_data = get_stock_data_smart(symbol, force_update=True)
                
                if not symbol_data.empty:
                    symbol_data = symbol_data.reset_index()
                    symbol_data['Symbol'] = symbol
                    new_data_frames.append(symbol_data)
            
            if new_data_frames:
                new_data = pd.concat(new_data_frames, ignore_index=True)
                combined_data = pd.concat([existing_data, new_data], ignore_index=True)
                
                # Save updated data
                historical_file = os.path.join(self.cache_dir, 'pf_historical_data.pkl')
                combined_data.to_pickle(historical_file)
                print(f"💾 Updated data for {len(symbols_to_update)} symbols")
                
            return True
            
        except Exception as e:
            print(f"❌ Error updating specific symbols: {e}")
            return False

    def _create_minimal_dataset(self, symbols: List[str]) -> bool:
        """Create minimal dataset with just essential symbols"""
        try:
            print(f"📊 Creating minimal dataset for {len(symbols)} symbols")
            # Limit to first 50 symbols for quick processing
            essential_symbols = symbols[:50] if len(symbols) > 50 else symbols
            
            return self._full_data_update(essential_symbols)
            
        except Exception as e:
            print(f"❌ Error creating minimal dataset: {e}")
            return False
    
    def _full_data_update(self, symbols: List[str]) -> bool:
        """Full data update - regenerate all data"""
        try:
            from data_fetcher import get_stock_data_smart
            
            print(f"📡 Updating data for {len(symbols)} symbols...")
            all_data_frames = []
            
            for i, symbol in enumerate(symbols, 1):
                if i % 50 == 0:  # Progress update every 50 symbols
                    print(f"  📊 Progress: {i}/{len(symbols)} symbols processed")
                
                # Generate data for this symbol
                symbol_data = get_stock_data_smart(symbol, force_update=True)
                
                if not symbol_data.empty:
                    # Reset index and add symbol column
                    symbol_data = symbol_data.reset_index()
                    symbol_data['Symbol'] = symbol
                    all_data_frames.append(symbol_data)
            
            if all_data_frames:
                # Combine all data
                combined_data = pd.concat(all_data_frames, ignore_index=True)
                
                # Save to cache
                historical_file = os.path.join(self.cache_dir, 'pf_historical_data.pkl')
                combined_data.to_pickle(historical_file)
                
                print(f"💾 Data saved to cache: {historical_file}")
                print(f"✅ Historical data updated: {len(combined_data)} records")
                return True
            else:
                print("❌ No data generated")
                return False
                
        except Exception as e:
            print(f"❌ Full update failed: {e}")
            return False

def main():
    """Test the smart data updater"""
    updater = SmartDataUpdater()
    
    # Example symbol list (you would get this from your portfolio)
    test_symbols = ['WIPRO.NS', 'RELIANCE.NS', 'TCS.NS']
    
    result = updater.smart_update_data(test_symbols)
    print(f"Update result: {result}")

if __name__ == "__main__":
    main()