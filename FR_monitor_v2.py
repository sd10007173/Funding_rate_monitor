#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資金費率監控系統 V2.0
用途：監控套利組合的資金費率並推送到 Telegram

功能：
1. 偵測套利組合（交易對相同、方向相反、數量相同）
2. 監控兩交易所資金費率
3. 計算費率差值並檢查閾值
4. 即時警示通知（只在觸發警示時發送）
5. 定期彙整報告（包含統計資訊）

使用方式：
    python FR_monitor_v2.py

環境變數設定：
    請參考 .env.example 檔案
    新增參數：
    - MONITOR_INTERVAL_MINUTES：監控檢查間隔（預設1分鐘）
    - SUMMARY_INTERVAL_MINUTES：彙整報告間隔（預設60分鐘）
"""

import os
import sys
import signal
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List

# 將專案模組加入路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fr_monitor.config import Config
from fr_monitor.binance_client import BinanceClient
from fr_monitor.bybit_client import BybitClient
from fr_monitor.arbitrage_detector import ArbitrageDetector
from fr_monitor.funding_rate_monitor import FundingRateMonitor
from fr_monitor.telegram_notifier import TelegramNotifier
from fr_monitor.statistics_collector import StatisticsCollector


class FRMonitorV2:
    """資金費率監控主程式 V2"""
    
    def __init__(self):
        self.config = Config()
        self.binance_client = BinanceClient(
            self.config.binance_api_key,
            self.config.binance_api_secret
        )
        self.bybit_client = BybitClient(
            self.config.bybit_api_key,
            self.config.bybit_api_secret
        )
        self.arbitrage_detector = ArbitrageDetector(
            self.binance_client,
            self.bybit_client
        )
        self.funding_monitor = FundingRateMonitor(
            self.binance_client,
            self.bybit_client
        )
        self.telegram_notifier = TelegramNotifier(
            self.config.telegram_bot_token,
            self.config.telegram_chat_id
        )
        self.statistics_collector = StatisticsCollector()
        
        # 優雅關閉標記
        self._shutdown_event = asyncio.Event()
        
        # 定時器任務
        self._monitoring_task = None
        self._summary_task = None
        
        # 設置日誌
        self._setup_logging()
        
        # 設置信號處理
        self._setup_signal_handlers()
        
    def _setup_logging(self):
        """設置日誌配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('fr_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _setup_signal_handlers(self):
        """設置信號處理器，用於優雅關閉"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到信號 {signum}，開始優雅關閉...")
            self._shutdown_event.set()
            
        # 註冊信號處理器
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # 終止信號
        
    async def _cleanup(self):
        """清理資源"""
        self.logger.info("正在清理資源...")
        try:
            # 取消定時器任務
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
            if self._summary_task and not self._summary_task.done():
                self._summary_task.cancel()
                
            await self.binance_client.close()
            await self.bybit_client.close()
            await self.telegram_notifier.close()
            self.logger.info("資源清理完成")
        except Exception as e:
            self.logger.error(f"清理資源時發生錯誤: {e}")
        
    async def check_and_send_alert(self):
        """檢查套利組合並在觸發警示時發送通知"""
        arbitrage_pairs = {}
        funding_data = {}
        success = False
        error_message = None
        
        try:
            # 1. 偵測套利組合
            self.logger.info("偵測套利組合中...")
            arbitrage_pairs = await self.arbitrage_detector.detect_arbitrage_pairs()
            
            if not arbitrage_pairs:
                self.logger.info("未發現套利組合")
                success = True
                return
                
            self.logger.info(f"發現 {len(arbitrage_pairs)} 個套利組合: {list(arbitrage_pairs.keys())}")
            
            # 2. 查詢資金費率
            self.logger.info("查詢資金費率中...")
            funding_data = await self.funding_monitor.get_funding_rates(list(arbitrage_pairs.keys()))
            
            # 3. 檢查是否有觸發警示的交易對
            alert_pairs = self._check_for_alerts(arbitrage_pairs, funding_data)
            
            if alert_pairs:
                # 4. 產生警示報告
                alert_report = self._generate_alert_report(alert_pairs, funding_data)
                
                # 5. 發送警示通知
                await self.telegram_notifier.send_formatted_message(alert_report)
                self.logger.info(f"警示報告已發送到 Telegram，觸發 {len(alert_pairs)} 個交易對")
                
                # 記錄警示
                for symbol in alert_pairs:
                    self.statistics_collector.record_alert(symbol)
            else:
                self.logger.info("未觸發警示閾值，無需發送通知")
            
            success = True
            
        except Exception as e:
            error_message = f"監控過程發生錯誤: {str(e)}"
            self.logger.error(error_message)
            await self.telegram_notifier.send_message(f"錯誤通知\n{error_message}")
            
        finally:
            # 記錄檢查結果 (包含成功和失敗)
            self.statistics_collector.record_check_result(
                success=success,
                arbitrage_pairs=arbitrage_pairs,
                funding_data=funding_data,
                error_message=error_message
            )
            
    def _check_for_alerts(self, arbitrage_pairs: Dict[str, Dict], funding_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """檢查是否有觸發警示的交易對"""
        alert_pairs = {}
        
        for symbol, pair_info in arbitrage_pairs.items():
            if symbol not in funding_data:
                continue
                
            funding_info = funding_data[symbol]
            long_exchange = pair_info['long_exchange']
            short_exchange = pair_info['short_exchange']
            
            if long_exchange not in funding_info or short_exchange not in funding_info:
                continue
                
            long_rate = funding_info[long_exchange]['rate']
            short_rate = funding_info[short_exchange]['rate']
            rate_diff = short_rate - long_rate
            
            # 檢查是否觸發警示
            if rate_diff <= self.config.funding_rate_threshold:
                alert_pairs[symbol] = pair_info
                
        return alert_pairs
    
    def _generate_alert_report(self, alert_pairs: Dict[str, Dict], funding_data: Dict[str, Dict]) -> str:
        """產生警示報告"""
        now = datetime.now(timezone.utc)
        report_lines = [
            "資費差警告",
            f"  {now.strftime('%Y-%m-%d %H:%M UTC')}",
            ""
        ]
        
        for symbol, pair_info in alert_pairs.items():
            if symbol not in funding_data:
                continue
                
            funding_info = funding_data[symbol]
            long_exchange = pair_info['long_exchange']
            short_exchange = pair_info['short_exchange']
            
            long_rate = funding_info[long_exchange]['rate']
            short_rate = funding_info[short_exchange]['rate']
            rate_diff = short_rate - long_rate
            
            report_lines.extend([
                f"    {symbol} (警告🔴)",
                f"    ├ {long_exchange.title()}(多)：{long_rate:+.4f}%",
                f"    ├ {short_exchange.title()}(空)：{short_rate:+.4f}%",
                f"    └ 資費差：{rate_diff:+.4f}%",
                ""
            ])
            
        return "\n".join(report_lines)
    
    async def send_summary_report(self):
        """發送彙整報告"""
        try:
            self.logger.info("生成彙整報告...")
            summary_report = self._generate_summary_report()
            
            await self.telegram_notifier.send_formatted_message(summary_report)
            self.logger.info("彙整報告已發送到 Telegram")
            
            # 重置統計資料
            self.statistics_collector.reset_stats()
            
        except Exception as e:
            error_msg = f"發送彙整報告時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            # 不重置統計資料，留待下次重試
    
    def _generate_summary_report(self) -> str:
        """產生彙整報告"""
        stats = self.statistics_collector
        report_lines = [
            "系統報告",
            stats.get_summary_duration(),
            "",
            "監控統計",
            f"├ 總檢查次數：{stats.get_total_checks()} 次",
            f"├ 失敗檢查：{stats.get_failed_checks()} 次",
            f"└ 觸發警示：{stats.get_total_alerts()} 次",
            ""
        ]
        
        # 交易對詳情
        if stats.symbol_stats:
            report_lines.append("交易對詳情")
            
            for symbol, symbol_stats in stats.symbol_stats.items():
                report_lines.extend([
                    f"  {symbol} 套利組合",
                    f"  ├ 當前資費差：{symbol_stats.current_rate_diff:+.4f}%",
                    f"  ├ 平均資費差：{symbol_stats.avg_rate_diff:+.4f}%",
                    f"  └ 警示次數：{symbol_stats.alert_count}/{symbol_stats.check_count} ({symbol_stats.alert_rate:.1f}%)",
                    ""
                ])
        else:
            report_lines.extend([
                "交易對詳情",
                "  無監控的套利組合",
                ""
            ])
        
        return "\n".join(report_lines)
        
    async def run_once(self):
        """執行一次檢查"""
        self.logger.info("開始執行資金費率監控 V2...")
        try:
            await self.check_and_send_alert()
        finally:
            await self._cleanup()
        self.logger.info("監控完成")
        
    async def run_continuously(self):
        """持續運行監控"""
        self.logger.info(f"開始持續監控 V2")
        self.logger.info(f"監控間隔: {self.config.monitor_interval_minutes} 分鐘")
        self.logger.info(f"彙整間隔: {self.config.summary_interval_minutes} 分鐘")
        
        # 發送啟動通知
        try:
            await self.telegram_notifier.send_startup_notification()
        except Exception as e:
            self.logger.warning(f"發送啟動通知失敗: {e}")
        
        try:
            # 啟動雙重定時器
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._summary_task = asyncio.create_task(self._summary_loop())
            
            # 等待關閉信號
            await self._shutdown_event.wait()
            
        finally:
            # 發送關閉通知
            try:
                await self.telegram_notifier.send_shutdown_notification()
            except Exception as e:
                self.logger.warning(f"發送關閉通知失敗: {e}")
                
            # 清理資源
            await self._cleanup()
            self.logger.info("監控系統 V2 已優雅關閉")
    
    async def _monitoring_loop(self):
        """監控循環（即時警示）"""
        while not self._shutdown_event.is_set():
            try:
                await self.check_and_send_alert()
                
                # 等待下次檢查
                wait_seconds = self.config.monitor_interval_minutes * 60
                self.logger.debug(f"等待 {self.config.monitor_interval_minutes} 分鐘後下次檢查...")
                
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=wait_seconds
                    )
                    break
                except asyncio.TimeoutError:
                    pass
                    
            except Exception as e:
                if self._shutdown_event.is_set():
                    break
                self.logger.error(f"監控循環錯誤: {e}")
                
                # 錯誤後等待 1 分鐘再重試
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=60)
                    break
                except asyncio.TimeoutError:
                    pass
    
    async def _summary_loop(self):
        """彙整報告循環"""
        while not self._shutdown_event.is_set():
            try:
                # 等待彙整間隔
                wait_seconds = self.config.summary_interval_minutes * 60
                self.logger.debug(f"等待 {self.config.summary_interval_minutes} 分鐘後發送彙整報告...")
                
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=wait_seconds
                    )
                    break
                except asyncio.TimeoutError:
                    pass
                
                if self._shutdown_event.is_set():
                    break
                    
                # 發送彙整報告
                await self.send_summary_report()
                
            except Exception as e:
                if self._shutdown_event.is_set():
                    break
                self.logger.error(f"彙整報告循環錯誤: {e}")
                
                # 錯誤後等待 5 分鐘再重試
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=300)
                    break
                except asyncio.TimeoutError:
                    pass


async def main():
    """主函數"""
    print("資金費率監控系統 V2.0")
    print("=" * 40)
    
    # 檢查配置
    try:
        config = Config()
        config.validate()
    except Exception as e:
        print(f"配置錯誤: {e}")
        print("請檢查 .env 檔案設定")
        return
        
    # 初始化監控器
    monitor = FRMonitorV2()
    
    # 檢查是否為一次性執行
    if "--once" in sys.argv:
        await monitor.run_once()
    else:
        await monitor.run_continuously()


if __name__ == "__main__":
    asyncio.run(main())