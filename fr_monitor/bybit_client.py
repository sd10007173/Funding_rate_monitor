"""
Bybit API 客戶端
"""

import hashlib
import hmac
import time
import aiohttp
import asyncio
from typing import Dict, List, Optional
from urllib.parse import urlencode


class BybitClient:
    """Bybit API 客戶端"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.bybit.com"
        self.session = None
        
    async def _get_session(self):
        """獲取或創建 aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def close(self):
        """關閉 HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            
    def _generate_signature(self, params: Dict) -> str:
        """生成 API 簽名"""
        # Bybit V5 API 簽名方式
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        param_str = ""
        if params:
            param_str = urlencode(sorted(params.items()))
            
        payload = timestamp + self.api_key + recv_window + param_str
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp, recv_window
        
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None, signed: bool = False) -> Dict:
        """發送 API 請求"""
        if params is None:
            params = {}
            
        headers = {
            'X-BAPI-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        if signed:
            signature, timestamp, recv_window = self._generate_signature(params)
            headers.update({
                'X-BAPI-SIGN': signature,
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': recv_window
            })
            
        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        async with session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Bybit API 錯誤 {response.status}: {text}")
            
            result = await response.json()
            if result.get('retCode') != 0:
                raise Exception(f"Bybit API 業務錯誤: {result.get('retMsg', 'Unknown error')}")
                
            return result.get('result', {})
            
    async def get_positions(self) -> List[Dict]:
        """獲取所有持倉資訊"""
        params = {
            'category': 'linear',  # USDT 永續合約
            'settleCoin': 'USDT'
        }
        
        data = await self._make_request('/v5/position/list', params, signed=True)
        positions = []
        
        for position in data.get('list', []):
            position_size = float(position['size'])
            if position_size > 0:  # 有持倉
                positions.append({
                    'symbol': position['symbol'],
                    'side': position['side'],  # Buy 或 Sell
                    'size': position_size,
                    'unrealizedPnl': float(position['unrealisedPnl']),
                    'percentage': float(position['unrealisedPnl']) / float(position['positionValue']) * 100 if float(position['positionValue']) != 0 else 0,
                    'markPrice': float(position['markPrice']),
                    'entryPrice': float(position['avgPrice'])
                })
                
        return positions
        
    async def get_funding_rate(self, symbol: str) -> Dict:
        """獲取指定交易對的當前資金費率"""
        # 先獲取合約資訊中的資金費率時間
        params = {
            'category': 'linear',
            'symbol': symbol
        }
        
        instruments_data = await self._make_request('/v5/market/instruments-info', params)
        instrument_info = instruments_data.get('list', [])
        
        if not instrument_info:
            raise Exception(f"找不到交易對 {symbol} 的合約資訊")
            
        instrument = instrument_info[0]
        
        # 獲取資金費率歷史（最新一筆）
        funding_params = {
            'category': 'linear',
            'symbol': symbol,
            'limit': 1
        }
        
        funding_data = await self._make_request('/v5/market/funding/history', funding_params)
        funding_list = funding_data.get('list', [])
        
        if not funding_list:
            raise Exception(f"找不到交易對 {symbol} 的資金費率資訊")
            
        latest_funding = funding_list[0]
        
        return {
            'symbol': symbol,
            'fundingRate': float(latest_funding['fundingRate']),
            'fundingRateTimestamp': int(latest_funding['fundingRateTimestamp']),
            'nextFundingTime': int(instrument.get('nextFundingTime', 0)),
            'fundingInterval': int(instrument.get('fundingInterval', 8))  # 小時
        }
        
    async def get_multiple_funding_rates(self, symbols: List[str]) -> Dict[str, Dict]:
        """批量獲取多個交易對的資金費率"""
        tasks = []
        for symbol in symbols:
            tasks.append(self.get_funding_rate(symbol))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        funding_rates = {}
        for i, result in enumerate(results):
            symbol = symbols[i]
            if isinstance(result, Exception):
                print(f"獲取 {symbol} 資金費率失敗: {result}")
                continue
            funding_rates[symbol] = result
            
        return funding_rates
        
    async def test_connection(self) -> bool:
        """測試 API 連接"""
        try:
            await self._make_request('/v5/market/time')
            return True
        except Exception as e:
            print(f"Bybit 連接測試失敗: {e}")
            return False