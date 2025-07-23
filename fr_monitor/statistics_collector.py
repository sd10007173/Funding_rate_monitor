"""
統計資料收集模組
用於記錄監控檢查結果和計算統計資訊
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CheckResult:
    """單次檢查結果"""
    timestamp: float
    success: bool
    arbitrage_pairs: Dict[str, Dict] = field(default_factory=dict)
    funding_data: Dict[str, Dict] = field(default_factory=dict)
    error_message: Optional[str] = None
    no_arbitrage_detected: bool = False


@dataclass
class SymbolStats:
    """交易對統計資料"""
    symbol: str
    check_count: int = 0
    alert_count: int = 0
    rate_differences: List[float] = field(default_factory=list)
    current_rate_diff: float = 0.0
    
    @property
    def alert_rate(self) -> float:
        """警示率"""
        if self.check_count == 0:
            return 0.0
        return (self.alert_count / self.check_count) * 100
    
    @property
    def avg_rate_diff(self) -> float:
        """平均費率差值"""
        if not self.rate_differences:
            return 0.0
        return sum(self.rate_differences) / len(self.rate_differences)
    
    @property
    def max_rate_diff(self) -> float:
        """最高費率差值"""
        return max(self.rate_differences) if self.rate_differences else 0.0
    
    @property
    def min_rate_diff(self) -> float:
        """最低費率差值"""
        return min(self.rate_differences) if self.rate_differences else 0.0


class StatisticsCollector:
    """統計資料收集器"""
    
    def __init__(self):
        self.check_results: List[CheckResult] = []
        self.symbol_stats: Dict[str, SymbolStats] = {}
        self.summary_start_time: float = time.time()
        self.no_arbitrage_count: int = 0
        
    def record_check_result(self, success: bool, arbitrage_pairs: Dict[str, Dict] = None,
                          funding_data: Dict[str, Dict] = None, error_message: str = None):
        """記錄檢查結果"""
        if arbitrage_pairs is None:
            arbitrage_pairs = {}
        if funding_data is None:
            funding_data = {}
            
        # 記錄無套利組合情況
        no_arbitrage_detected = len(arbitrage_pairs) == 0
        if no_arbitrage_detected:
            self.no_arbitrage_count += 1
            
        # 建立檢查結果
        check_result = CheckResult(
            timestamp=time.time(),
            success=success,
            arbitrage_pairs=arbitrage_pairs,
            funding_data=funding_data,
            error_message=error_message,
            no_arbitrage_detected=no_arbitrage_detected
        )
        
        self.check_results.append(check_result)
        
        # 更新交易對統計
        if success and arbitrage_pairs and funding_data:
            self._update_symbol_stats(arbitrage_pairs, funding_data)
    
    def _update_symbol_stats(self, arbitrage_pairs: Dict[str, Dict], funding_data: Dict[str, Dict]):
        """更新交易對統計資料"""
        for symbol, pair_info in arbitrage_pairs.items():
            if symbol not in funding_data:
                continue
                
            # 初始化交易對統計
            if symbol not in self.symbol_stats:
                self.symbol_stats[symbol] = SymbolStats(symbol=symbol)
                
            stats = self.symbol_stats[symbol]
            stats.check_count += 1
            
            # 計算費率差值
            funding_info = funding_data[symbol]
            long_exchange = pair_info['long_exchange']
            short_exchange = pair_info['short_exchange']
            
            if long_exchange in funding_info and short_exchange in funding_info:
                long_rate = funding_info[long_exchange]['rate']
                short_rate = funding_info[short_exchange]['rate']
                rate_diff = short_rate - long_rate
                
                stats.rate_differences.append(rate_diff)
                stats.current_rate_diff = rate_diff
    
    def record_alert(self, symbol: str):
        """記錄警示觸發"""
        # 確保交易對統計存在
        if symbol not in self.symbol_stats:
            self.symbol_stats[symbol] = SymbolStats(symbol=symbol)
        
        self.symbol_stats[symbol].alert_count += 1
    
    def get_total_checks(self) -> int:
        """獲取總檢查次數"""
        return len(self.check_results)
    
    def get_successful_checks(self) -> int:
        """獲取成功檢查次數"""
        return sum(1 for result in self.check_results if result.success)
    
    def get_failed_checks(self) -> int:
        """獲取失敗檢查次數"""
        return sum(1 for result in self.check_results if not result.success)
    
    def get_total_alerts(self) -> int:
        """獲取總警示次數"""
        return sum(stats.alert_count for stats in self.symbol_stats.values())
    
    def get_alert_rate(self) -> float:
        """獲取整體警示率"""
        successful_checks = self.get_successful_checks()
        if successful_checks == 0:
            return 0.0
        return (self.get_total_alerts() / successful_checks) * 100
    
    def get_summary_duration(self) -> str:
        """獲取統計時間區間"""
        current_time = time.time()
        duration_seconds = current_time - self.summary_start_time
        
        start_dt = datetime.fromtimestamp(self.summary_start_time, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
        
        return f"{start_dt.strftime('%Y-%m-%d %H:%M')}-{end_dt.strftime('%H:%M')} UTC"
    
    def reset_stats(self):
        """重置統計資料（用於新的彙整週期）"""
        self.check_results.clear()
        self.symbol_stats.clear()
        self.summary_start_time = time.time()
        self.no_arbitrage_count = 0
    
    def get_current_monitored_symbols(self) -> List[str]:
        """獲取當前監控的交易對列表"""
        return list(self.symbol_stats.keys())