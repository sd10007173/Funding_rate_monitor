#!/usr/bin/env python3
"""
測試統計收集器的警示計數修復
"""

import sys
import os

# 將專案模組加入路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fr_monitor.statistics_collector import StatisticsCollector


def test_alert_counting():
    """測試警示計數邏輯"""
    print("測試警示計數修復...")
    
    collector = StatisticsCollector()
    
    # 模擬兩次檢查，每次都有相同的套利組合和警示
    arbitrage_pairs = {
        'BUSDT': {'long_exchange': 'bybit', 'short_exchange': 'binance'},
        'ALCHUSDT': {'long_exchange': 'bybit', 'short_exchange': 'binance'}
    }
    
    funding_data = {
        'BUSDT': {
            'bybit': {'rate': 0.005},
            'binance': {'rate': 0.0442}
        },
        'ALCHUSDT': {
            'bybit': {'rate': 0.005},
            'binance': {'rate': 0.034}
        }
    }
    
    # 第一次檢查
    collector.record_check_result(
        success=True,
        arbitrage_pairs=arbitrage_pairs,
        funding_data=funding_data
    )
    # 記錄兩個警示
    collector.record_alert('BUSDT')
    collector.record_alert('ALCHUSDT')
    
    # 第二次檢查
    collector.record_check_result(
        success=True,
        arbitrage_pairs=arbitrage_pairs,
        funding_data=funding_data
    )
    # 記錄兩個警示
    collector.record_alert('BUSDT')
    collector.record_alert('ALCHUSDT')
    
    # 驗證統計
    print(f"總檢查次數: {collector.get_total_checks()}")
    print(f"總警示次數: {collector.get_total_alerts()}")
    
    for symbol in ['BUSDT', 'ALCHUSDT']:
        stats = collector.symbol_stats[symbol]
        print(f"{symbol}:")
        print(f"  檢查次數: {stats.check_count}")
        print(f"  警示次數: {stats.alert_count}")
        print(f"  警示率: {stats.alert_rate:.1f}%")
    
    # 預期結果：
    # - 總檢查次數: 2
    # - 總警示次數: 4 (2個交易對 x 2次檢查)
    # - 每個交易對: 檢查次數2, 警示次數2, 警示率100%
    
    assert collector.get_total_checks() == 2
    assert collector.get_total_alerts() == 4
    assert collector.symbol_stats['BUSDT'].check_count == 2
    assert collector.symbol_stats['BUSDT'].alert_count == 2
    assert collector.symbol_stats['BUSDT'].alert_rate == 100.0
    assert collector.symbol_stats['ALCHUSDT'].check_count == 2
    assert collector.symbol_stats['ALCHUSDT'].alert_count == 2
    assert collector.symbol_stats['ALCHUSDT'].alert_rate == 100.0
    
    print("✅ 警示計數修復測試通過！")


if __name__ == "__main__":
    test_alert_counting()