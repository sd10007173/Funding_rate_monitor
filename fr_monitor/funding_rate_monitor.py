"""
資金費率監控模組
"""

import asyncio
from typing import Dict, List
from .binance_client import BinanceClient
from .bybit_client import BybitClient


class FundingRateMonitor:
    """資金費率監控器"""
    
    def __init__(self, binance_client: BinanceClient, bybit_client: BybitClient):
        self.binance_client = binance_client
        self.bybit_client = bybit_client
        
    async def get_funding_rates(self, symbols: List[str]) -> Dict[str, Dict]:
        """獲取指定交易對的資金費率"""
        if not symbols:
            return {}
            
        print(f"正在查詢 {len(symbols)} 個交易對的資金費率...")
        
        try:
            # 並行查詢兩個交易所的資金費率
            binance_rates, bybit_rates = await asyncio.gather(
                self.binance_client.get_multiple_funding_rates(symbols),
                self.bybit_client.get_multiple_funding_rates(symbols),
                return_exceptions=True
            )
            
            if isinstance(binance_rates, Exception):
                print(f"獲取 Binance 資金費率失敗: {binance_rates}")
                binance_rates = {}
                
            if isinstance(bybit_rates, Exception):
                print(f"獲取 Bybit 資金費率失敗: {bybit_rates}")
                bybit_rates = {}
                
            # 整合資金費率資料
            funding_data = {}
            
            for symbol in symbols:
                symbol_data = {}
                
                # Binance 資金費率
                if symbol in binance_rates:
                    binance_rate = binance_rates[symbol]
                    symbol_data['binance'] = {
                        'rate': binance_rate['lastFundingRate'] * 100,  # 轉換為百分比
                        'next_funding_time': binance_rate['nextFundingTime'],
                        'mark_price': binance_rate['markPrice'],
                        'raw_data': binance_rate
                    }
                else:
                    print(f"未能獲取 {symbol} 的 Binance 資金費率")
                    symbol_data['binance'] = {
                        'rate': 0.0,
                        'next_funding_time': 0,
                        'mark_price': 0.0,
                        'error': 'API 查詢失敗'
                    }
                    
                # Bybit 資金費率
                if symbol in bybit_rates:
                    bybit_rate = bybit_rates[symbol]
                    symbol_data['bybit'] = {
                        'rate': bybit_rate['fundingRate'] * 100,  # 轉換為百分比
                        'next_funding_time': bybit_rate['nextFundingTime'],
                        'funding_interval': bybit_rate['fundingInterval'],
                        'raw_data': bybit_rate
                    }
                else:
                    print(f"未能獲取 {symbol} 的 Bybit 資金費率")
                    symbol_data['bybit'] = {
                        'rate': 0.0,
                        'next_funding_time': 0,
                        'funding_interval': 8,
                        'error': 'API 查詢失敗'
                    }
                    
                funding_data[symbol] = symbol_data
                
                # 輸出查詢結果
                binance_rate_pct = symbol_data['binance']['rate']
                bybit_rate_pct = symbol_data['bybit']['rate']
                print(f"  {symbol}: Binance {binance_rate_pct:+.4f}%, Bybit {bybit_rate_pct:+.4f}%")
                
            return funding_data
            
        except Exception as e:
            print(f"查詢資金費率時發生錯誤: {e}")
            # 返回空的資金費率資料
            return {symbol: {
                'binance': {'rate': 0.0, 'error': str(e)},
                'bybit': {'rate': 0.0, 'error': str(e)}
            } for symbol in symbols}
            
    async def get_single_funding_rate(self, symbol: str, exchange: str) -> Dict:
        """獲取單一交易所的資金費率"""
        try:
            if exchange.lower() == 'binance':
                rate_data = await self.binance_client.get_funding_rate(symbol)
                return {
                    'rate': rate_data['lastFundingRate'] * 100,
                    'next_funding_time': rate_data['nextFundingTime'],
                    'mark_price': rate_data['markPrice'],
                    'raw_data': rate_data
                }
            elif exchange.lower() == 'bybit':
                rate_data = await self.bybit_client.get_funding_rate(symbol)
                return {
                    'rate': rate_data['fundingRate'] * 100,
                    'next_funding_time': rate_data['nextFundingTime'],
                    'funding_interval': rate_data['fundingInterval'],
                    'raw_data': rate_data
                }
            else:
                raise ValueError(f"不支援的交易所: {exchange}")
                
        except Exception as e:
            print(f"獲取 {exchange} {symbol} 資金費率失敗: {e}")
            return {
                'rate': 0.0,
                'error': str(e)
            }
            
    def calculate_rate_difference(self, funding_data: Dict[str, Dict], 
                                 long_exchange: str, short_exchange: str) -> float:
        """計算費率差值"""
        try:
            long_rate = funding_data[long_exchange]['rate']
            short_rate = funding_data[short_exchange]['rate']
            
            # 費率差值 = 做空交易所資金費率 - 做多交易所資金費率
            rate_diff = short_rate - long_rate
            
            return rate_diff
            
        except KeyError as e:
            print(f"計算費率差值時缺少資料: {e}")
            return 0.0
        except Exception as e:
            print(f"計算費率差值時發生錯誤: {e}")
            return 0.0
            
    async def test_funding_rate_apis(self) -> bool:
        """測試資金費率 API"""
        test_symbol = "BTCUSDT"
        
        print(f"測試資金費率 API，使用測試交易對: {test_symbol}")
        
        try:
            # 測試 Binance 資金費率 API
            print("測試 Binance 資金費率 API...")
            binance_rate = await self.binance_client.get_funding_rate(test_symbol)
            print(f"  Binance {test_symbol} 資金費率: {binance_rate['lastFundingRate'] * 100:+.4f}%")
            
            # 測試 Bybit 資金費率 API
            print("測試 Bybit 資金費率 API...")
            bybit_rate = await self.bybit_client.get_funding_rate(test_symbol)
            print(f"  Bybit {test_symbol} 資金費率: {bybit_rate['fundingRate'] * 100:+.4f}%")
            
            print("資金費率 API 測試通過")
            return True
            
        except Exception as e:
            print(f"資金費率 API 測試失敗: {e}")
            return False