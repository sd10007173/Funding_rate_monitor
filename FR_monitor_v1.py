#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資金費率監控系統 V1.0
用途：監控套利組合的資金費率並推送到 Telegram

功能：
1. 偵測套利組合（交易對相同、方向相反、數量相同）
2. 監控兩交易所資金費率
3. 計算費率差值並檢查閾值
4. 定時推送到 Telegram 頻道

使用方式：
    python FR_monitor_v1.py

環境變數設定：
    請參考 .env.example 檔案
"""

import os
import sys
import signal
import asyncio
import logging
from datetime import datetime, timezone

# 將專案模組加入路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fr_monitor.config import Config
from fr_monitor.binance_client import BinanceClient
from fr_monitor.bybit_client import BybitClient
from fr_monitor.arbitrage_detector import ArbitrageDetector
from fr_monitor.funding_rate_monitor import FundingRateMonitor
from fr_monitor.telegram_notifier import TelegramNotifier


class FRMonitor:
    """資金費率監控主程式"""
    
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
        
        # 優雅關閉標記
        self._shutdown_event = asyncio.Event()
        
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
            await self.binance_client.close()
            await self.bybit_client.close()
            await self.telegram_notifier.close()
            self.logger.info("資源清理完成")
        except Exception as e:
            self.logger.error(f"清理資源時發生錯誤: {e}")
        
    async def check_and_notify(self):
        """檢查套利組合並發送通知"""
        try:
            # 1. 偵測套利組合
            self.logger.info("偵測套利組合中...")
            arbitrage_pairs = await self.arbitrage_detector.detect_arbitrage_pairs()
            
            if not arbitrage_pairs:
                self.logger.info("未發現套利組合")
                return
                
            self.logger.info(f"發現 {len(arbitrage_pairs)} 個套利組合: {list(arbitrage_pairs.keys())}")
            
            # 2. 查詢資金費率
            self.logger.info("查詢資金費率中...")
            funding_data = await self.funding_monitor.get_funding_rates(list(arbitrage_pairs.keys()))
            
            # 3. 產生報告
            report = self._generate_report(arbitrage_pairs, funding_data)
            
            # 4. 發送通知
            await self.telegram_notifier.send_formatted_message(report)
            self.logger.info("報告已發送到 Telegram")
            
        except Exception as e:
            error_msg = f"監控過程發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            await self.telegram_notifier.send_message(f"錯誤通知\n{error_msg}")
            
    def _generate_report(self, arbitrage_pairs, funding_data):
        """產生監控報告"""
        now = datetime.now(timezone.utc)
        report_lines = [
            "資金費率監控報告",
            now.strftime("%Y-%m-%d %H:%M UTC"),
            ""
        ]
        
        for symbol, pair_info in arbitrage_pairs.items():
            if symbol not in funding_data:
                continue
                
            funding_info = funding_data[symbol]
            
            # 確定多空方向
            long_exchange = pair_info['long_exchange']
            short_exchange = pair_info['short_exchange']
            
            long_rate = funding_info[long_exchange]['rate']
            short_rate = funding_info[short_exchange]['rate']
            
            # 費率差值 = 做空交易所資金費率 - 做多交易所資金費率
            rate_diff = short_rate - long_rate
            
            # 檢查閾值
            threshold_warning = ""
            if rate_diff <= self.config.funding_rate_threshold:
                threshold_warning = " [警告]"
            
            report_lines.extend([
                f"  {symbol} 套利組合",
                f"  ├ {long_exchange.title()}(多)：{long_rate:+.4f}%",
                f"  ├ {short_exchange.title()}(空)：{short_rate:+.4f}%",
                f"  └ 費率差值：{rate_diff:+.4f}%{threshold_warning}",
                ""
            ])
            
        return "\n".join(report_lines)
        
    async def run_once(self):
        """執行一次檢查"""
        self.logger.info("開始執行資金費率監控...")
        try:
            await self.check_and_notify()
        finally:
            await self._cleanup()
        self.logger.info("監控完成")
        
    async def run_continuously(self):
        """持續運行監控"""
        self.logger.info(f"開始持續監控，間隔 {self.config.query_interval_minutes} 分鐘")
        
        # 發送啟動通知
        try:
            await self.telegram_notifier.send_startup_notification()
        except Exception as e:
            self.logger.warning(f"發送啟動通知失敗: {e}")
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # 檢查是否需要關閉
                    if self._shutdown_event.is_set():
                        break
                        
                    await self.check_and_notify()
                    
                    # 等待下次執行或關閉信號
                    wait_seconds = self.config.query_interval_minutes * 60
                    self.logger.info(f"等待 {self.config.query_interval_minutes} 分鐘後下次執行...")
                    
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), 
                            timeout=wait_seconds
                        )
                        # 如果等到了關閉信號，跳出循環
                        break
                    except asyncio.TimeoutError:
                        # 超時是正常的，繼續下一輪監控
                        pass
                        
                except Exception as e:
                    if self._shutdown_event.is_set():
                        break
                    self.logger.error(f"監控循環錯誤: {e}")
                    # 發送錯誤通知
                    try:
                        await self.telegram_notifier.send_error_notification(str(e))
                    except:
                        pass
                    
                    # 錯誤後等待 1 分鐘再重試，或直到收到關閉信號
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=60)
                        break
                    except asyncio.TimeoutError:
                        pass
                        
        finally:
            # 發送關閉通知
            try:
                await self.telegram_notifier.send_shutdown_notification()
            except Exception as e:
                self.logger.warning(f"發送關閉通知失敗: {e}")
                
            # 清理資源
            await self._cleanup()
            self.logger.info("監控系統已優雅關閉")


async def main():
    """主函數"""
    print("資金費率監控系統 V1.0")
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
    monitor = FRMonitor()
    
    # 檢查是否為一次性執行
    if "--once" in sys.argv:
        await monitor.run_once()
    else:
        await monitor.run_continuously()


if __name__ == "__main__":
    asyncio.run(main())