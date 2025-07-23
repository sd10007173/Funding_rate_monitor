#!/usr/bin/env python3
"""
簡單測試 FR_monitor_v2 的基本功能
"""

import asyncio
import sys
import os

# 將專案模組加入路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fr_monitor.statistics_collector import StatisticsCollector, CheckResult


def test_statistics_collector():
    """測試統計收集器基本功能"""
    print("測試統計收集器...")
    
    collector = StatisticsCollector()
    
    # 測試記錄檢查結果
    arbitrage_pairs = {
        'BTCUSDT': {
            'long_exchange': 'bybit',
            'short_exchange': 'binance'
        }
    }
    
    funding_data = {
        'BTCUSDT': {
            'bybit': {'rate': 0.005},
            'binance': {'rate': 0.01}
        }
    }
    
    # 記錄成功檢查
    collector.record_check_result(
        success=True,
        arbitrage_pairs=arbitrage_pairs,
        funding_data=funding_data
    )
    
    # 記錄警示
    collector.record_alert('BTCUSDT')
    
    # 記錄失敗檢查
    collector.record_check_result(
        success=False,
        error_message="API 連接失敗"
    )
    
    # 驗證統計
    assert collector.get_total_checks() == 2
    assert collector.get_successful_checks() == 1
    assert collector.get_failed_checks() == 1
    assert collector.get_total_alerts() == 1
    assert 'BTCUSDT' in collector.symbol_stats
    
    symbol_stats = collector.symbol_stats['BTCUSDT']
    assert symbol_stats.check_count == 1
    assert symbol_stats.alert_count == 1
    assert symbol_stats.alert_rate == 100.0
    assert len(symbol_stats.rate_differences) == 1
    assert symbol_stats.rate_differences[0] == 0.005  # 0.01 - 0.005
    
    print("✓ 統計收集器測試通過")


def test_config():
    """測試配置讀取"""
    print("測試配置讀取...")
    
    from fr_monitor.config import Config
    
    # 設置測試環境變數
    os.environ['MONITOR_INTERVAL_MINUTES'] = '2'
    os.environ['SUMMARY_INTERVAL_MINUTES'] = '30'
    os.environ['FUNDING_RATE_THRESHOLD'] = '0.01'
    
    config = Config()
    
    assert config.monitor_interval_minutes == 2
    assert config.summary_interval_minutes == 30
    assert config.funding_rate_threshold == 0.01
    
    print("✓ 配置讀取測試通過")


def main():
    """主測試函數"""
    print("開始 FR_monitor_v2 基本功能測試")
    print("=" * 40)
    
    try:
        test_statistics_collector()
        test_config()
        
        print("=" * 40)
        print("✅ 所有基本功能測試通過！")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)