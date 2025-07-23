"""
套利組合偵測模組
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from .binance_client import BinanceClient
from .bybit_client import BybitClient


class ArbitrageDetector:
    """套利組合偵測器"""
    
    def __init__(self, binance_client: BinanceClient, bybit_client: BybitClient):
        self.binance_client = binance_client
        self.bybit_client = bybit_client
        
    def _normalize_symbol(self, symbol: str, exchange: str) -> str:
        """標準化交易對名稱"""
        if exchange.lower() == 'binance':
            # Binance: BTCUSDT
            return symbol
        elif exchange.lower() == 'bybit':
            # Bybit: BTCUSDT
            return symbol
        return symbol
        
    def _normalize_side(self, side: str, exchange: str) -> str:
        """標準化持倉方向"""
        if exchange.lower() == 'binance':
            # Binance: LONG, SHORT
            return side.upper()
        elif exchange.lower() == 'bybit':
            # Bybit: Buy, Sell -> LONG, SHORT
            if side.upper() == 'BUY':
                return 'LONG'
            elif side.upper() == 'SELL':
                return 'SHORT'
        return side.upper()
        
    async def get_all_positions(self) -> Tuple[List[Dict], List[Dict]]:
        """獲取兩個交易所的所有持倉"""
        try:
            binance_positions, bybit_positions = await asyncio.gather(
                self.binance_client.get_positions(),
                self.bybit_client.get_positions(),
                return_exceptions=True
            )
            
            if isinstance(binance_positions, Exception):
                print(f"獲取 Binance 持倉失敗: {binance_positions}")
                binance_positions = []
                
            if isinstance(bybit_positions, Exception):
                print(f"獲取 Bybit 持倉失敗: {bybit_positions}")
                bybit_positions = []
                
            return binance_positions, bybit_positions
            
        except Exception as e:
            print(f"獲取持倉資訊時發生錯誤: {e}")
            return [], []
            
    def _find_arbitrage_pairs(self, binance_positions: List[Dict], bybit_positions: List[Dict]) -> Dict[str, Dict]:
        """找出套利組合"""
        arbitrage_pairs = {}
        
        # 將持倉按交易所分組
        binance_pos_map = {}
        for pos in binance_positions:
            symbol = self._normalize_symbol(pos['symbol'], 'binance')
            side = self._normalize_side(pos['side'], 'binance')
            binance_pos_map[symbol] = {
                'side': side,
                'size': pos['size'],
                'original_data': pos
            }
            
        bybit_pos_map = {}
        for pos in bybit_positions:
            symbol = self._normalize_symbol(pos['symbol'], 'bybit')
            side = self._normalize_side(pos['side'], 'bybit')
            bybit_pos_map[symbol] = {
                'side': side,
                'size': pos['size'],
                'original_data': pos
            }
            
        # 找出套利組合：交易對相同、方向相反、數量相同
        for symbol in binance_pos_map:
            if symbol not in bybit_pos_map:
                continue
                
            binance_pos = binance_pos_map[symbol]
            bybit_pos = bybit_pos_map[symbol]
            
            # 檢查方向是否相反
            if binance_pos['side'] == bybit_pos['side']:
                continue
                
            # 檢查數量是否相同（允許小幅誤差）
            size_diff = abs(binance_pos['size'] - bybit_pos['size'])
            size_avg = (binance_pos['size'] + bybit_pos['size']) / 2
            
            if size_avg > 0 and size_diff / size_avg > 0.05:  # 允許 5% 誤差
                continue
                
            # 確定多空方向
            if binance_pos['side'] == 'LONG':
                long_exchange = 'binance'
                short_exchange = 'bybit'
                long_size = binance_pos['size']
                short_size = bybit_pos['size']
            else:
                long_exchange = 'bybit'
                short_exchange = 'binance'
                long_size = bybit_pos['size']
                short_size = binance_pos['size']
                
            arbitrage_pairs[symbol] = {
                'symbol': symbol,
                'long_exchange': long_exchange,
                'short_exchange': short_exchange,
                'long_size': long_size,
                'short_size': short_size,
                'size_difference': size_diff,
                'binance_position': binance_pos['original_data'],
                'bybit_position': bybit_pos['original_data']
            }
            
        return arbitrage_pairs
        
    async def detect_arbitrage_pairs(self) -> Dict[str, Dict]:
        """偵測套利組合"""
        print("正在獲取持倉資訊...")
        binance_positions, bybit_positions = await self.get_all_positions()
        
        print(f"Binance 持倉數量: {len(binance_positions)}")
        print(f"Bybit 持倉數量: {len(bybit_positions)}")
        
        if not binance_positions and not bybit_positions:
            print("未發現任何持倉")
            return {}
            
        # 輸出持倉詳情（調試用）
        print("\nBinance 持倉:")
        for pos in binance_positions:
            print(f"  {pos['symbol']}: {pos['side']} {pos['size']}")
            
        print("\nBybit 持倉:")
        for pos in bybit_positions:
            print(f"  {pos['symbol']}: {pos['side']} {pos['size']}")
            
        # 找出套利組合
        arbitrage_pairs = self._find_arbitrage_pairs(binance_positions, bybit_positions)
        
        print(f"\n發現 {len(arbitrage_pairs)} 個套利組合:")
        for symbol, pair_info in arbitrage_pairs.items():
            print(f"  {symbol}: {pair_info['long_exchange']}(多) vs {pair_info['short_exchange']}(空)")
            
        return arbitrage_pairs
        
    async def test_connections(self) -> bool:
        """測試兩個交易所的連接"""
        try:
            binance_ok, bybit_ok = await asyncio.gather(
                self.binance_client.test_connection(),
                self.bybit_client.test_connection(),
                return_exceptions=True
            )
            
            if isinstance(binance_ok, Exception):
                print(f"Binance 連接測試異常: {binance_ok}")
                binance_ok = False
                
            if isinstance(bybit_ok, Exception):
                print(f"Bybit 連接測試異常: {bybit_ok}")
                bybit_ok = False
                
            print(f"Binance 連接: {'OK' if binance_ok else 'FAIL'}")
            print(f"Bybit 連接: {'OK' if bybit_ok else 'FAIL'}")
            
            return binance_ok and bybit_ok
            
        except Exception as e:
            print(f"連接測試時發生錯誤: {e}")
            return False