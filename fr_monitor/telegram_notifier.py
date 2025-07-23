"""
Telegram 通知模組
"""

import aiohttp
import asyncio
from typing import Optional


class TelegramNotifier:
    """Telegram 通知器"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
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
            
    async def send_message(self, text: str, parse_mode: Optional[str] = None) -> bool:
        """發送訊息到 Telegram"""
        try:
            session = await self._get_session()
            
            data = {
                'chat_id': self.chat_id,
                'text': text
            }
            
            if parse_mode:
                data['parse_mode'] = parse_mode
                
            url = f"{self.base_url}/sendMessage"
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        print("Telegram 訊息發送成功")
                        return True
                    else:
                        print(f"Telegram API 錯誤: {result.get('description', 'Unknown error')}")
                        return False
                else:
                    text = await response.text()
                    print(f"Telegram HTTP 錯誤 {response.status}: {text}")
                    return False
                    
        except Exception as e:
            print(f"發送 Telegram 訊息時發生錯誤: {e}")
            return False
            
    async def send_formatted_message(self, text: str) -> bool:
        """發送格式化訊息（使用等寬字體）"""
        # 使用 Markdown 格式的程式碼區塊來保持格式
        formatted_text = f"```\n{text}\n```"
        return await self.send_message(formatted_text, parse_mode='Markdown')
        
    async def test_connection(self) -> bool:
        """測試 Telegram Bot 連接"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/getMe"
            
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        bot_info = result.get('result', {})
                        bot_name = bot_info.get('username', 'Unknown')
                        print(f"Telegram Bot 連接成功: @{bot_name}")
                        return True
                    else:
                        print(f"Telegram Bot API 錯誤: {result.get('description', 'Unknown error')}")
                        return False
                else:
                    text = await response.text()
                    print(f"Telegram Bot HTTP 錯誤 {response.status}: {text}")
                    return False
                    
        except Exception as e:
            print(f"測試 Telegram Bot 連接時發生錯誤: {e}")
            return False
            
    async def send_test_message(self) -> bool:
        """發送測試訊息"""
        test_message = "資金費率監控系統 - 連接測試成功"
        return await self.send_message(test_message)
        
    async def send_error_notification(self, error: str) -> bool:
        """發送錯誤通知"""
        error_message = f"錯誤通知\n\n{error}"
        return await self.send_message(error_message)
        
    async def send_startup_notification(self) -> bool:
        """發送啟動通知"""
        startup_message = "資金費率監控系統已啟動\n正在監控套利組合的資金費率..."
        return await self.send_message(startup_message)
        
    async def send_shutdown_notification(self) -> bool:
        """發送關閉通知"""
        shutdown_message = "資金費率監控系統已停止"
        return await self.send_message(shutdown_message)