#!/usr/bin/env python3
"""
Configuration Utility Script
Manage configuration settings for the portfolio analysis system
"""

from config_manager import get_config
import sys

def main():
    """Main configuration utility"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    config = get_config()
    command = sys.argv[1].lower()
    
    if command == "show":
        config.print_current_config()
    
    elif command == "set":
        if len(sys.argv) < 4:
            print("Usage: python config_util.py set <setting_path> <value>")
            print("Example: python config_util.py set benchmark_settings.primary_benchmark ^BSESN")
            return
        
        setting_path = sys.argv[2]
        value = sys.argv[3]
        
        # Try to convert value to appropriate type
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.replace('.', '').replace('-', '').isdigit():
            value = float(value) if '.' in value else int(value)
        
        config.update_setting(setting_path, value)
        print(f"✅ Updated {setting_path} = {value}")
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: python config_util.py get <setting_path>")
            return
        
        setting_path = sys.argv[2]
        value = config.get_setting(setting_path)
        print(f"{setting_path} = {value}")
    
    elif command == "benchmark":
        if len(sys.argv) < 3:
            print("Available benchmarks:")
            bench_config = config.get_benchmark_config()
            print(f"  Primary: {bench_config.primary_benchmark} ({bench_config.benchmark_name})")
            for name, symbol in bench_config.alternative_benchmarks.items():
                print(f"  {name}: {symbol}")
            return
        
        benchmark_name = sys.argv[2]
        symbol = config.get_benchmark_symbol(benchmark_name)
        print(f"Benchmark '{benchmark_name}' symbol: {symbol}")
    
    elif command == "reset":
        print("⚠️  This will reset configuration to defaults. Are you sure? (y/n)")
        if input().lower() == 'y':
            config.create_default_config()
            config.save_config()
            print("✅ Configuration reset to defaults")
    
    else:
        show_help()

def show_help():
    """Show help information"""
    print("Configuration Utility for Portfolio Analysis System")
    print("=" * 55)
    print()
    print("Commands:")
    print("  show                     - Show current configuration")
    print("  set <path> <value>       - Set configuration value")
    print("  get <path>               - Get configuration value")
    print("  benchmark [name]         - Show/get benchmark symbols")
    print("  reset                    - Reset to default configuration")
    print()
    print("Examples:")
    print("  python config_util.py show")
    print("  python config_util.py set benchmark_settings.primary_benchmark ^BSESN")
    print("  python config_util.py get technical_indicators.momentum_indicators.rsi.period")
    print("  python config_util.py benchmark nifty_500")
    print()
    print("Common Settings:")
    print("  benchmark_settings.primary_benchmark")
    print("  benchmark_settings.rs_calculation_period")
    print("  technical_indicators.momentum_indicators.rsi.period")
    print("  technical_indicators.momentum_indicators.rsi.overbought_threshold")
    print("  filter_thresholds.relative_strength.very_strong")

if __name__ == "__main__":
    main()
