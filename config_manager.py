#!/usr/bin/env python3
"""
Configuration Manager
Handles loading and managing configuration settings for the portfolio analysis system
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class BenchmarkConfig:
    """Benchmark configuration settings"""
    primary_benchmark: str
    benchmark_name: str
    rs_benchmark_index: str
    rs_benchmark_name: str
    alternative_benchmarks: Dict[str, str]
    rs_calculation_period: int
    rs_smoothing_period: int

@dataclass
class TechnicalConfig:
    """Technical indicators configuration"""
    rsi_period: int
    rsi_overbought: float
    rsi_oversold: float
    macd_fast: int
    macd_slow: int
    macd_signal: int
    sma_periods: list
    ema_periods: list
    wema_periods: list
    dsma_periods: list
    dsma_displacement: Dict[str, int]
    bollinger_period: int
    bollinger_std: float
    atr_period: int

@dataclass
class FilterConfig:
    """Filter threshold configuration"""
    rs_very_strong: float
    rs_strong: float
    rs_weak: float
    rs_very_weak: float
    high_change_thresholds: list
    low_change_thresholds: list

class ConfigManager:
    """Manages configuration settings for the portfolio analysis system"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                print(f"✅ Configuration loaded from {self.config_file}")
            else:
                print(f"⚠️  Configuration file {self.config_file} not found, using defaults")
                self.create_default_config()
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            self.create_default_config()
    
    def create_default_config(self) -> None:
        """Create default configuration if file doesn't exist"""
        self.config = {
            "benchmark_settings": {
                "primary_benchmark": "^NSEI",
                "benchmark_name": "NIFTY 50",
                "rs_calculation_period": 252,
                "rs_smoothing_period": 14
            },
            "technical_indicators": {
                "momentum_indicators": {
                    "rsi": {"period": 14, "overbought_threshold": 70, "oversold_threshold": 30}
                }
            }
        }
    
    def get_benchmark_config(self) -> BenchmarkConfig:
        """Get benchmark configuration"""
        bench_settings = self.config.get("benchmark_settings", {})
        # Use rs_benchmark_index if specified, otherwise fallback to primary_benchmark
        rs_benchmark = bench_settings.get("rs_benchmark_index", bench_settings.get("primary_benchmark", "^NSEI"))
        rs_benchmark_name = bench_settings.get("rs_benchmark_name", bench_settings.get("benchmark_name", "NIFTY 50"))
        return BenchmarkConfig(
            primary_benchmark=bench_settings.get("primary_benchmark", "^NSEI"),
            benchmark_name=bench_settings.get("benchmark_name", "NIFTY 50"),
            rs_benchmark_index=rs_benchmark,
            rs_benchmark_name=rs_benchmark_name,
            alternative_benchmarks=bench_settings.get("alternative_benchmarks", {}),
            rs_calculation_period=bench_settings.get("rs_calculation_period", 252),
            rs_smoothing_period=bench_settings.get("rs_smoothing_period", 14)
        )
    
    def get_technical_config(self) -> TechnicalConfig:
        """Get technical indicators configuration"""
        tech_settings = self.config.get("technical_indicators", {})
        
        # Moving averages
        ma_settings = tech_settings.get("moving_averages", {})
        
        # Momentum indicators
        momentum_settings = tech_settings.get("momentum_indicators", {})
        rsi_settings = momentum_settings.get("rsi", {})
        macd_settings = momentum_settings.get("macd", {})
        
        # Volatility indicators
        vol_settings = tech_settings.get("volatility_indicators", {})
        bb_settings = vol_settings.get("bollinger_bands", {})
        atr_settings = vol_settings.get("atr", {})
        
        return TechnicalConfig(
            rsi_period=rsi_settings.get("period", 14),
            rsi_overbought=rsi_settings.get("overbought_threshold", 70),
            rsi_oversold=rsi_settings.get("oversold_threshold", 30),
            macd_fast=macd_settings.get("fast_period", 12),
            macd_slow=macd_settings.get("slow_period", 26),
            macd_signal=macd_settings.get("signal_period", 9),
            sma_periods=ma_settings.get("sma_periods", [20, 50, 200]),
            ema_periods=ma_settings.get("ema_periods", [12, 26, 50]),
            wema_periods=ma_settings.get("wema_periods", [21, 30]),
            dsma_periods=ma_settings.get("dsma_periods", [50, 200]),
            dsma_displacement=ma_settings.get("dsma_displacement", {"50": 10, "200": 25}),
            bollinger_period=bb_settings.get("period", 20),
            bollinger_std=bb_settings.get("std_deviation", 2),
            atr_period=atr_settings.get("period", 14)
        )
    
    def get_filter_config(self) -> FilterConfig:
        """Get filter threshold configuration"""
        filter_settings = self.config.get("filter_thresholds", {})
        rs_settings = filter_settings.get("relative_strength", {})
        week52_settings = filter_settings.get("52_week_performance", {})
        
        return FilterConfig(
            rs_very_strong=rs_settings.get("very_strong", 10.0),
            rs_strong=rs_settings.get("strong", 3.0),
            rs_weak=rs_settings.get("weak", -3.0),
            rs_very_weak=rs_settings.get("very_weak", -10.0),
            high_change_thresholds=week52_settings.get("high_change_thresholds", [-10, -20, -30]),
            low_change_thresholds=week52_settings.get("low_change_thresholds", [10, 20, 30])
        )
    
    def get_setting(self, path: str, default: Any = None) -> Any:
        """Get a specific setting using dot notation (e.g., 'benchmark_settings.primary_benchmark')"""
        keys = path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def update_setting(self, path: str, value: Any) -> None:
        """Update a specific setting using dot notation"""
        keys = path.split('.')
        config_ref = self.config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config_ref:
                config_ref[key] = {}
            config_ref = config_ref[key]
        
        # Set the value
        config_ref[keys[-1]] = value
        
        # Save to file
        self.save_config()
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"✅ Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
    
    def get_benchmark_symbol(self, benchmark_name: Optional[str] = None) -> str:
        """Get benchmark symbol for RS calculation"""
        if benchmark_name:
            # Check if it's an alternative benchmark
            alt_benchmarks = self.get_setting("benchmark_settings.alternative_benchmarks", {})
            if benchmark_name in alt_benchmarks:
                return alt_benchmarks[benchmark_name]
        
        # Return primary benchmark
        return self.get_setting("benchmark_settings.primary_benchmark", "^NSEI")
    
    def print_current_config(self) -> None:
        """Print current configuration in a readable format"""
        print("\n📋 CURRENT CONFIGURATION SETTINGS")
        print("=" * 50)
        
        # Benchmark settings
        bench_config = self.get_benchmark_config()
        print(f"\n🎯 Benchmark Settings:")
        print(f"   Primary Benchmark: {bench_config.primary_benchmark} ({bench_config.benchmark_name})")
        print(f"   RS Calculation Period: {bench_config.rs_calculation_period} days")
        print(f"   RS Smoothing Period: {bench_config.rs_smoothing_period} days")
        
        # Technical settings
        tech_config = self.get_technical_config()
        print(f"\n📊 Technical Indicators:")
        print(f"   RSI Period: {tech_config.rsi_period} | Overbought: {tech_config.rsi_overbought} | Oversold: {tech_config.rsi_oversold}")
        print(f"   MACD: {tech_config.macd_fast}/{tech_config.macd_slow}/{tech_config.macd_signal}")
        print(f"   WEMA Periods: {tech_config.wema_periods}")
        print(f"   DSMA Periods: {tech_config.dsma_periods}")
        
        # Filter settings
        filter_config = self.get_filter_config()
        print(f"\n🔍 Filter Thresholds:")
        print(f"   RS Very Strong: > {filter_config.rs_very_strong}")
        print(f"   RS Very Weak: < {filter_config.rs_very_weak}")
        print(f"   52w High Change: {filter_config.high_change_thresholds}%")
        print(f"   52w Low Change: {filter_config.low_change_thresholds}%")

# Global configuration instance
config_manager = ConfigManager()

def get_config() -> ConfigManager:
    """Get the global configuration manager instance"""
    return config_manager
