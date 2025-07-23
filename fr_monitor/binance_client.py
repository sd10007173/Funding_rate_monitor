"""
Binance API 客戶端
"""

import hashlib
import hmac
import time
import aiohttp
import asyncio
from typing import Dict, List, Optional
from urllib.parse import urlencode


class BinanceClient:
    """Binance API 客戶端"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.binance.com"
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
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None, signed: bool = False) -> Dict:
        """發送 API 請求"""
        if params is None:
            params = {}
            
        headers = {
            'X-MBX-APIKEY': self.api_key
        }
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
            
        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        async with session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Binance API 錯誤 {response.status}: {text}")
            return await response.json()
            
    async def get_account_info(self) -> Dict:
        """獲取帳戶資訊"""
        return await self._make_request('/fapi/v2/account', signed=True)
        
    async def get_positions(self) -> List[Dict]:
        """獲取所有持倉資訊"""
        account_info = await self.get_account_info()
        positions = []
        
        for position in account_info.get('positions', []):
            # 只返回有持倉的交易對
            position_amt = float(position['positionAmt'])
            if position_amt != 0:
                positions.append({
                    'symbol': position['symbol'],
                    'side': 'LONG' if position_amt > 0 else 'SHORT',
                    'size': abs(position_amt),
                    'unrealizedPnl': float(position.get('unrealizedPnl', position.get('unRealizedProfit', 0))),
                    'percentage': float(position.get('percentage', 0)),
                    'markPrice': float(position.get('markPrice', 0)),
                    'entryPrice': float(position.get('entryPrice', 0))
                })
                
        return positions
        
    async def get_funding_rate(self, symbol: str) -> Dict:
        """獲取指定交易對的當前資金費率"""
        params = {'symbol': symbol}
        data = await self._make_request('/fapi/v1/premiumIndex', params)
        
        if isinstance(data, list):
            data = data[0]
            
        return {
            'symbol': data['symbol'],
            'markPrice': float(data['markPrice']),
            'indexPrice': float(data['indexPrice']),
            'estimatedSettlePrice': float(data['estimatedSettlePrice']),
            'lastFundingRate': float(data['lastFundingRate']),
            'nextFundingTime': int(data['nextFundingTime']),
            'interestRate': float(data['interestRate']),
            'time': int(data['time'])
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
            await self._make_request('/fapi/v1/ping')
            return True
        except Exception as e:
            print(f"Binance 連接測試失敗: {e}")
            return False