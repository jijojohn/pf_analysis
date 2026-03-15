#!/usr/bin/env python3
"""
Data Freshness Checker
Ensures data is always current and up-to-date for report generation
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pickle

class DataFreshnessChecker:
    """Comprehensive data freshness checker with live data validation"""
    
    def __init__(self, cache_dir: str = 'price_cache'):
        self.cache_dir = cache_dir
        self.current_date = datetime.now()
        self.tolerance_hours = 6  # Data older than 6 hours is considered stale
        
    def check_comprehensive_freshness(self) -> Dict[str, any]:
        """Comprehensive check of all data freshness"""
        print("🔍 Performing comprehensive data freshness check...")
        
        results = {
            'historical_data_fresh': False,
            'datasets_fresh': False,
            'cache_files_fresh': False,
            'update_needed': True,
            'full_update_needed': False,
            'stale_files': [],
            'missing_files': [],
            'recommendations': []
        }
        
        # Check historical data
        historical_check = self._check_historical_data()
        results.update(historical_check)
        
        # Check comprehensive datasets
        dataset_check = self._check_comprehensive_datasets()
        results.update(dataset_check)
        
        # Check individual cache files
        cache_check = self._check_cache_files()
        results.update(cache_check)
        
        # Make recommendations
        results['recommendations'] = self._make_recommendations(results)
        
        return results
    
    def _check_historical_data(self) -> Dict[str, any]:
        """Check main historical data file"""
        historical_file = os.path.join(self.cache_dir, 'pf_historical_data.pkl')
        
        if not os.path.exists(historical_file):
            return {
                'historical_data_fresh': False,
                'historical_missing': True,
                'historical_age_hours': float('inf')
            }
        
        try:
            # Check file modification time
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(historical_file))
            age_hours = (self.current_date - file_mod_time).total_seconds() / 3600
            
            # Load and check data content
            data = pd.read_pickle(historical_file)
            
            if data.empty:
                return {
                    'historical_data_fresh': False,
                    'historical_empty': True,
                    'historical_age_hours': age_hours
                }
            
            # Check data date range
            if 'Date' in data.columns:
                latest_data_date = pd.to_datetime(data['Date']).max()
                # Convert to datetime if it's a date object
                if hasattr(latest_data_date, 'to_pydatetime'):
                    latest_data_date = latest_data_date.to_pydatetime()
                data_age_hours = (self.current_date - latest_data_date).total_seconds() / 3600
            else:
                data_age_hours = age_hours
            
            is_fresh = age_hours <= self.tolerance_hours and data_age_hours <= 24  # Data should be within 24 hours
            
            return {
                'historical_data_fresh': is_fresh,
                'historical_missing': False,
                'historical_empty': False,
                'historical_age_hours': age_hours,
                'historical_data_age_hours': data_age_hours,
                'historical_records': len(data),
                'historical_symbols': len(data['Symbol'].unique()) if 'Symbol' in data.columns else 0
            }
            
        except Exception as e:
            print(f"⚠️ Error checking historical data: {e}")
            return {
                'historical_data_fresh': False,
                'historical_error': str(e),
                'historical_age_hours': float('inf')
            }
    
    def _check_comprehensive_datasets(self) -> Dict[str, any]:
        """Check comprehensive dataset files"""
        current_date_str = self.current_date.strftime('%Y%m%d')
        
        csv_file = f'reports/comprehensive_dataset_{current_date_str}.csv'
        xlsx_file = f'reports/comprehensive_dataset_{current_date_str}.xlsx'
        
        csv_exists = os.path.exists(csv_file)
        xlsx_exists = os.path.exists(xlsx_file)
        
        if not csv_exists and not xlsx_exists:
            return {
                'datasets_fresh': False,
                'datasets_missing': True,
                'dataset_age_hours': float('inf')
            }
        
        try:
            # Check the CSV file (primary)
            if csv_exists:
                file_mod_time = datetime.fromtimestamp(os.path.getmtime(csv_file))
                age_hours = (self.current_date - file_mod_time).total_seconds() / 3600
                
                # Load and validate content
                data = pd.read_csv(csv_file)
                
                is_fresh = age_hours <= self.tolerance_hours and len(data) >= 250
                
                return {
                    'datasets_fresh': is_fresh,
                    'datasets_missing': False,
                    'dataset_age_hours': age_hours,
                    'dataset_records': len(data),
                    'dataset_columns': len(data.columns)
                }
            else:
                return {
                    'datasets_fresh': False,
                    'datasets_missing': True,
                    'dataset_age_hours': float('inf')
                }
                
        except Exception as e:
            print(f"⚠️ Error checking datasets: {e}")
            return {
                'datasets_fresh': False,
                'dataset_error': str(e),
                'dataset_age_hours': float('inf')
            }
    
    def _check_cache_files(self) -> Dict[str, any]:
        """Check individual cache files"""
        if not os.path.exists(self.cache_dir):
            return {
                'cache_files_fresh': False,
                'cache_missing': True
            }
        
        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl') and f != 'pf_historical_data.pkl']
        
        if not cache_files:
            return {
                'cache_files_fresh': False,
                'cache_empty': True,
                'cache_count': 0
            }
        
        stale_files = []
        fresh_files = 0
        
        for file in cache_files:
            file_path = os.path.join(self.cache_dir, file)
            try:
                file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                age_hours = (self.current_date - file_mod_time).total_seconds() / 3600
                
                if age_hours > 24:  # Individual cache files can be older
                    stale_files.append(file)
                else:
                    fresh_files += 1
            except:
                stale_files.append(file)
        
        return {
            'cache_files_fresh': len(stale_files) < len(cache_files) * 0.3,  # 70% should be fresh
            'cache_missing': False,
            'cache_empty': False,
            'cache_count': len(cache_files),
            'cache_fresh_count': fresh_files,
            'cache_stale_files': stale_files
        }
    
    def _make_recommendations(self, results: Dict[str, any]) -> List[str]:
        """Make recommendations based on freshness check"""
        recommendations = []
        
        if results.get('historical_missing'):
            recommendations.append("CRITICAL: Generate complete historical data cache")
            results['full_update_needed'] = True
        elif not results.get('historical_data_fresh'):
            if results.get('historical_age_hours', 0) > 24:
                recommendations.append("HIGH: Update missing/stale historical data only")
                results['targeted_update_needed'] = True
            else:
                recommendations.append("LOW: Historical data slightly stale but usable")
        
        if results.get('datasets_missing'):
            recommendations.append("CRITICAL: Generate comprehensive datasets")
            results['dataset_generation_needed'] = True
        elif not results.get('datasets_fresh'):
            recommendations.append("MEDIUM: Regenerate comprehensive datasets")
            results['dataset_generation_needed'] = True
        
        if not results.get('cache_files_fresh'):
            if results.get('cache_missing') or results.get('cache_empty'):
                recommendations.append("HIGH: Generate missing cache files only")
                results['cache_update_needed'] = True
            else:
                stale_count = len(results.get('cache_stale_files', []))
                total_count = results.get('cache_count', 0)
                if stale_count < total_count * 0.5:  # Less than 50% stale
                    recommendations.append("LOW: Update only stale cache files")
                    results['partial_cache_update'] = True
                else:
                    recommendations.append("MEDIUM: Update stale cache files")
                    results['cache_update_needed'] = True
        
        # Overall recommendation with priority on minimal updates
        if results.get('historical_missing') or results.get('datasets_missing'):
            results['full_update_needed'] = True
            recommendations.append("STRATEGY: Full data generation required")
        elif results.get('targeted_update_needed') or results.get('cache_update_needed'):
            results['update_needed'] = True
            recommendations.append("STRATEGY: Targeted update of missing/stale data only")
        elif results.get('dataset_generation_needed'):
            results['update_needed'] = True  
            recommendations.append("STRATEGY: Generate datasets from existing cache")
        else:
            results['update_needed'] = False
            recommendations.append("OPTIMAL: Data is current - no updates needed")
        
        return recommendations
    
    def force_data_update(self, symbols: List[str]) -> bool:
        """Force a complete data update"""
        print("🔄 Forcing complete data update...")
        
        try:
            from smart_data_updater import SmartDataUpdater
            
            updater = SmartDataUpdater(self.cache_dir)
            success = updater._full_data_update(symbols)
            
            if success:
                print("✅ Forced data update completed successfully")
                return True
            else:
                print("❌ Forced data update failed")
                return False
                
        except Exception as e:
            print(f"❌ Error in forced data update: {e}")
            return False
    
    def print_freshness_report(self, results: Dict[str, any]):
        """Print a comprehensive freshness report"""
        print("\n" + "="*60)
        print("📊 DATA FRESHNESS REPORT")
        print("="*60)
        
        # Historical data status
        if results.get('historical_missing'):
            print("📡 Historical Data: ❌ MISSING")
        elif results.get('historical_data_fresh'):
            print(f"📡 Historical Data: ✅ FRESH ({results.get('historical_age_hours', 0):.1f}h old)")
            print(f"   📊 Records: {results.get('historical_records', 0):,}")
            print(f"   🏢 Symbols: {results.get('historical_symbols', 0)}")
        else:
            print(f"📡 Historical Data: ⚠️ STALE ({results.get('historical_age_hours', 0):.1f}h old)")
        
        # Dataset status
        if results.get('datasets_missing'):
            print("📊 Comprehensive Datasets: ❌ MISSING")
        elif results.get('datasets_fresh'):
            print(f"📊 Comprehensive Datasets: ✅ FRESH ({results.get('dataset_age_hours', 0):.1f}h old)")
            print(f"   📈 Records: {results.get('dataset_records', 0):,}")
            print(f"   📋 Columns: {results.get('dataset_columns', 0)}")
        else:
            print(f"📊 Comprehensive Datasets: ⚠️ STALE ({results.get('dataset_age_hours', 0):.1f}h old)")
        
        # Cache files status
        if results.get('cache_missing'):
            print("💾 Cache Files: ❌ MISSING")
        elif results.get('cache_files_fresh'):
            print(f"💾 Cache Files: ✅ FRESH ({results.get('cache_fresh_count', 0)}/{results.get('cache_count', 0)} files)")
        else:
            print(f"💾 Cache Files: ⚠️ PARTIAL ({results.get('cache_fresh_count', 0)}/{results.get('cache_count', 0)} fresh)")
        
        # Recommendations
        print("\n🎯 RECOMMENDATIONS:")
        for i, rec in enumerate(results.get('recommendations', []), 1):
            print(f"   {i}. {rec}")
        
        print("="*60)

def main():
    """Test the data freshness checker"""
    checker = DataFreshnessChecker()
    results = checker.check_comprehensive_freshness()
    checker.print_freshness_report(results)

if __name__ == "__main__":
    main()