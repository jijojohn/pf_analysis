#!/usr/bin/env python3
"""
Portfolio Manager Module
Handles portfolio data loading, management, and analysis
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Optional
from data_fetcher import DataManager
from config_manager import get_config


def _default_portfolio_file() -> str:
    """Get portfolio filename from config.json."""
    return get_config().get_setting('system_settings.portfolio_file', 'dpsr_report.xls.xlsx')


class PortfolioManager:
    """Portfolio management and data handling"""
    
    def __init__(self, data_manager: DataManager, portfolio_file: str = None):
        if portfolio_file is None:
            portfolio_file = _default_portfolio_file()
        self.data_manager = data_manager
        self.portfolio_file = portfolio_file
        self.portfolio_data = pd.DataFrame()
        self.stocks_data = pd.DataFrame()
        
    def load_portfolio_from_excel(self, filepath: str = None) -> pd.DataFrame:
        """Load portfolio data from Excel file - simple and direct approach"""
        if filepath is None:
            filepath = self.portfolio_file
            
        try:
            if not os.path.exists(filepath):
                print(f"❌ Portfolio file not found: {filepath}")
                return pd.DataFrame()
            
            print(f"📊 Loading portfolio from {filepath}...")
            
            # Try reading Excel file with different approaches
            df = None
            
            # Method 1: Try reading default sheet first
            try:
                df = pd.read_excel(filepath, engine='openpyxl')
                print(f"✅ Read using default sheet")
            except Exception as e1:
                print(f"❌ Default sheet failed: {e1}")
                
                # Method 2: Try reading with specific sheet name
                try:
                    df = pd.read_excel(filepath, engine='openpyxl', sheet_name='dpsr_report')
                    print(f"✅ Read using 'dpsr_report' sheet")
                except Exception as e2:
                    print(f"❌ 'dpsr_report' sheet failed: {e2}")
                    
                    # Method 3: Try reading with sheet index 0
                    try:
                        df = pd.read_excel(filepath, engine='openpyxl', sheet_name=0)
                        print(f"✅ Read using sheet index 0")
                    except Exception as e3:
                        print(f"❌ Sheet index 0 failed: {e3}")
                        raise Exception(f"All reading methods failed. Last error: {e3}")
            
            if df is None or df.empty:
                print("❌ Portfolio file is empty or unreadable")
                return pd.DataFrame()
                
            print(f"✅ Raw data loaded: {len(df)} rows, {len(df.columns)} columns")
            
            # Clean and process the data
            df = self._clean_portfolio_data(df)
            
            if not df.empty:
                self.portfolio_data = df
                print(f"✅ Portfolio loaded successfully: {len(df)} stocks")
                return df
            else:
                print("❌ No valid data after cleaning")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Error loading portfolio: {e}")
            print(f"💡 Please ensure {self.portfolio_file} is a valid Excel file")
            return pd.DataFrame()
    
    def _clean_portfolio_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize portfolio data"""
        try:
            cleaned_df = df.copy()
            
            # Remove rows where ScripCode or important columns are NaN (likely totals/summary rows)
            if 'ScripCode' in cleaned_df.columns:
                cleaned_df = cleaned_df.dropna(subset=['ScripCode'])
            
            # Remove rows where LTP is 'Total:' or other summary indicators
            if 'LTP' in cleaned_df.columns:
                cleaned_df = cleaned_df[~cleaned_df['LTP'].astype(str).str.contains('Total:', na=False)]
            
            # Remove completely empty rows
            cleaned_df = cleaned_df.dropna(how='all')
            
            # Reset index after filtering
            cleaned_df = cleaned_df.reset_index(drop=True)
            
            # Standardize column names
            # Column mapping for standardization
            column_mapping = {
                'symbol': 'Symbol',
                'Symbol': 'Symbol',
                'ScripCode': 'Symbol',  # Use ScripCode as Symbol
                'scripcode': 'Symbol',
                'scrip_code': 'Symbol',
                'stock': 'Symbol',
                'Stock': 'Symbol',
                'ticker': 'Symbol',
                'Ticker': 'Ticker',
                'dp_bal': 'DP_Bal',
                'DP_Bal': 'DP_Bal',
                'balance': 'DP_Bal',
                'Balance': 'DP_Bal',
                'buy_price': 'Buy_Price',
                'Buy_Price': 'Buy_Price',
                'BuyPrice': 'Buy_Price',
                'purchase_price': 'Buy_Price',
                'Purchase_Price': 'Buy_Price',
                'hold_price': 'Hold_Price',
                'Hold_Price': 'Hold_Price',
                'price': 'Hold_Price',
                'Price': 'Hold_Price',
                'percentage_allocation': 'Percentage_Allocation',
                'Percentage_Allocation': 'Percentage_Allocation',
                'allocation': 'Percentage_Allocation',
                'Allocation': 'Percentage_Allocation',
                'weight': 'Percentage_Allocation',
                'Weight': 'Percentage_Allocation'
            }
            
            # Rename columns
            for old_name, new_name in column_mapping.items():
                if old_name in cleaned_df.columns:
                    cleaned_df.rename(columns={old_name: new_name}, inplace=True)
            
            # Ensure required columns exist
            required_columns = ['Symbol', 'DP_Bal', 'Hold_Price']
            
            for col in required_columns:
                if col not in cleaned_df.columns:
                    if col == 'Symbol':
                        # Try to use ScripCode first, then index as fallback
                        if 'ScripCode' in cleaned_df.columns:
                            cleaned_df['Symbol'] = cleaned_df['ScripCode']
                        else:
                            # Use index as symbol (fallback)
                            cleaned_df['Symbol'] = cleaned_df.index
                    elif col == 'DP_Bal':
                        cleaned_df['DP_Bal'] = 1  # Default quantity
                    elif col == 'Hold_Price':
                        cleaned_df['Hold_Price'] = 100  # Default price
            
            # Validate Buy_Price column - add if missing
            if 'Buy_Price' not in cleaned_df.columns:
                if 'Hold_Price' in cleaned_df.columns:
                    print("⚠️  'Buy_Price' column not found - using 'Hold_Price' as fallback")
                    print("    💡 For accurate P&L, ensure Excel has 'Buy_Price' column")
                    cleaned_df['Buy_Price'] = cleaned_df['Hold_Price']
                else:
                    print("⚠️  Neither 'Buy_Price' nor 'Hold_Price' found - using default")
                    cleaned_df['Buy_Price'] = 100
            
            # Clean symbol names
            if 'Symbol' in cleaned_df.columns:
                cleaned_df['Symbol'] = cleaned_df['Symbol'].astype(str).str.strip()
                
                # Add exchange suffix if missing
                def add_exchange_suffix(symbol):
                    if pd.isna(symbol) or symbol == '':
                        return symbol
                    
                    symbol = str(symbol).upper()
                    
                    # Skip if already has exchange suffix
                    if '.NS' in symbol or '.BO' in symbol:
                        return symbol
                    
                    # Add appropriate exchange suffix
                    # Most Indian stocks are on NSE (.NS)
                    return f"{symbol}.NS"
                
                cleaned_df['Symbol'] = cleaned_df['Symbol'].apply(add_exchange_suffix)
            
            # Calculate percentage allocation if missing
            if 'Percentage_Allocation' not in cleaned_df.columns:
                if 'DP_Bal' in cleaned_df.columns and 'Hold_Price' in cleaned_df.columns:
                    # Calculate based on investment value
                    cleaned_df['Investment_Value'] = cleaned_df['DP_Bal'] * cleaned_df['Hold_Price']
                    total_investment = cleaned_df['Investment_Value'].sum()
                    
                    if total_investment > 0:
                        cleaned_df['Percentage_Allocation'] = (cleaned_df['Investment_Value'] / total_investment) * 100
                    else:
                        # Equal allocation
                        cleaned_df['Percentage_Allocation'] = 100 / len(cleaned_df)
                else:
                    # Equal allocation
                    cleaned_df['Percentage_Allocation'] = 100 / len(cleaned_df)
            
            # Convert numeric columns
            numeric_columns = ['DP_Bal', 'Hold_Price', 'Percentage_Allocation']
            for col in numeric_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce').fillna(0)
            
            # Remove rows with invalid symbols
            cleaned_df = cleaned_df[cleaned_df['Symbol'].notna() & (cleaned_df['Symbol'] != '')]
            
            # Set symbol as index
            if not cleaned_df.empty:
                cleaned_df.set_index('Symbol', inplace=True)
                cleaned_df['Symbol'] = cleaned_df.index  # Keep symbol as column too
            
            print(f"🧹 Cleaned portfolio data: {len(cleaned_df)} valid stocks")
            
            return cleaned_df
            
        except Exception as e:
            print(f"⚠️  Error cleaning portfolio data: {e}")
            return pd.DataFrame()
    
    def update_historical_data(self, force_update: bool = False) -> pd.DataFrame:
        """Update historical data for all portfolio stocks"""
        if self.portfolio_data.empty:
            print("❌ No portfolio data available")
            return pd.DataFrame()
        
        symbols = self.get_stock_symbols()
        print(f"🔄 Updating data for {len(symbols)} stocks...")
        
        # Get data for all symbols
        combined_data = self.data_manager.get_multiple_stocks_data(symbols, force_update)
        
        if not combined_data.empty:
            self.stocks_data = combined_data
            
            # Individual files are already saved by data_manager.get_multiple_stocks_data()
            # No need for redundant consolidated file
            
            print(f"✅ Historical data updated: {len(combined_data)} records")
            return combined_data
        else:
            print("❌ Failed to update historical data")
            return pd.DataFrame()
    
    def get_stock_symbols(self) -> List[str]:
        """Get list of stock symbols from portfolio"""
        if self.portfolio_data.empty:
            return []
        
        return self.portfolio_data['Symbol'].tolist()
    
    def get_stock_data(self, symbol: str) -> pd.DataFrame:
        """Get historical data for a specific stock"""
        if self.stocks_data.empty:
            # Load from individual stock file directly (single source of truth)
            return self.data_manager.get_stock_data(symbol)
        
        # Filter data for the specific symbol
        stock_data = self.stocks_data[self.stocks_data['Symbol'] == symbol].copy()
        
        if not stock_data.empty:
            # Set date as index if not already
            if 'Date' in stock_data.columns:
                stock_data.set_index('Date', inplace=True)
                # Ensure the index is datetime
                if not isinstance(stock_data.index, pd.DatetimeIndex):
                    stock_data.index = pd.to_datetime(stock_data.index)
            
            # Remove the Symbol column for cleaner data
            if 'Symbol' in stock_data.columns:
                stock_data = stock_data.drop('Symbol', axis=1)
            
            return stock_data
        else:
            # Fallback to individual fetch
            return self.data_manager.get_stock_data(symbol)
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary statistics"""
        if self.portfolio_data.empty:
            return {}
        
        summary = {
            'total_stocks': len(self.portfolio_data),
            'total_allocation': self.portfolio_data['Percentage_Allocation'].sum(),
            'total_investment': (self.portfolio_data['DP_Bal'] * self.portfolio_data['Hold_Price']).sum(),
            'average_allocation': self.portfolio_data['Percentage_Allocation'].mean(),
            'largest_holding': {
                'symbol': self.portfolio_data.loc[self.portfolio_data['Percentage_Allocation'].idxmax(), 'Symbol'],
                'allocation': self.portfolio_data['Percentage_Allocation'].max()
            },
            'smallest_holding': {
                'symbol': self.portfolio_data.loc[self.portfolio_data['Percentage_Allocation'].idxmin(), 'Symbol'],
                'allocation': self.portfolio_data['Percentage_Allocation'].min()
            }
        }
        
        return summary
    
    def get_portfolio_value(self) -> Dict:
        """Calculate current portfolio value using latest prices"""
        if self.portfolio_data.empty:
            return {'total_value': 0, 'total_cost': 0, 'total_pnl': 0, 'total_pnl_pct': 0}
        
        total_current_value = 0
        total_cost = 0
        
        for symbol in self.get_stock_symbols():
            stock_data = self.get_stock_data(symbol)
            
            if not stock_data.empty:
                current_price = stock_data['close'].iloc[-1]
                shares = self.portfolio_data.loc[self.portfolio_data['Symbol'] == symbol, 'DP_Bal'].iloc[0]
                cost_price = self.portfolio_data.loc[self.portfolio_data['Symbol'] == symbol, 'Hold_Price'].iloc[0]
                
                current_value = shares * current_price
                cost_value = shares * cost_price
                
                total_current_value += current_value
                total_cost += cost_value
        
        total_pnl = total_current_value - total_cost
        total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            'total_value': total_current_value,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct
        }
    
    def export_portfolio_data(self, filename: str = None):
        """Export portfolio data to Excel"""
        if self.portfolio_data.empty:
            print("❌ No portfolio data to export")
            return
        
        if filename is None:
            filename = f"portfolio_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Portfolio holdings
                self.portfolio_data.to_excel(writer, sheet_name='Portfolio', index=False)
                
                # Portfolio summary
                summary = self.get_portfolio_summary()
                summary_df = pd.DataFrame([summary])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Current values
                value_info = self.get_portfolio_value()
                value_df = pd.DataFrame([value_info])
                value_df.to_excel(writer, sheet_name='Current_Value', index=False)
            
            print(f"📁 Portfolio data exported to {filename}")
            
        except Exception as e:
            print(f"❌ Error exporting portfolio data: {e}")

if __name__ == "__main__":
    # Test the portfolio manager
    print("🧪 Testing Portfolio Manager...")
    
    # Create data manager
    dm = DataManager()
    
    # Create portfolio manager
    pm = PortfolioManager(dm)
    
    # Test loading portfolio
    portfolio_data = pm.load_portfolio_from_excel()
    
    if not portfolio_data.empty:
        print(f"\n📊 Portfolio loaded: {len(portfolio_data)} stocks")
        
        # Show summary
        summary = pm.get_portfolio_summary()
        print(f"📈 Portfolio Summary:")
        print(f"   Total Stocks: {summary['total_stocks']}")
        print(f"   Total Investment: ₹{summary['total_investment']:,.2f}")
        print(f"   Average Allocation: {summary['average_allocation']:.2f}%")
        
        # Test data update
        historical_data = pm.update_historical_data()
        if not historical_data.empty:
            print(f"📈 Historical data: {len(historical_data)} records")
            
            # Test individual stock data
            symbols = pm.get_stock_symbols()
            if symbols:
                test_symbol = symbols[0]
                stock_data = pm.get_stock_data(test_symbol)
                if not stock_data.empty:
                    print(f"📊 {test_symbol} data: {len(stock_data)} records")
                    print(f"   Latest price: ₹{stock_data['close'].iloc[-1]:.2f}")
    else:
        print("❌ No portfolio data loaded")
