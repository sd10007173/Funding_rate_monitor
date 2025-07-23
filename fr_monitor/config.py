"""
配置管理模組
"""

import os
from typing import Optional
from dotenv import load_dotenv


class Config:
    """配置類別，管理所有環境變數和設定"""
    
    def __init__(self):
        # 載入 .env 檔案
        load_dotenv()
        
        # API 憑證
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_api_secret = os.getenv('BINANCE_API_SECRET')
        self.bybit_api_key = os.getenv('BYBIT_API_KEY')
        self.bybit_api_secret = os.getenv('BYBIT_API_SECRET')
        
        # Telegram 設定
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # 監控參數
        self.query_interval_minutes = int(os.getenv('QUERY_INTERVAL_MINUTES', '30'))
        self.funding_rate_threshold = float(os.getenv('FUNDING_RATE_THRESHOLD', '0.0'))
        
    def validate(self):
        """驗證必要的配置是否存在"""
        required_configs = [
            ('BINANCE_API_KEY', self.binance_api_key),
            ('BINANCE_API_SECRET', self.binance_api_secret),
            ('BYBIT_API_KEY', self.bybit_api_key),
            ('BYBIT_API_SECRET', self.bybit_api_secret),
            ('TELEGRAM_BOT_TOKEN', self.telegram_bot_token),
            ('TELEGRAM_CHAT_ID', self.telegram_chat_id),
        ]
        
        missing_configs = []
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)
                
        if missing_configs:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing_configs)}")
            
        # 驗證數值參數
        if self.query_interval_minutes <= 0:
            raise ValueError("QUERY_INTERVAL_MINUTES 必須大於 0")
            
    def __str__(self):
        """返回配置摘要（隱藏敏感資訊）"""
        return f"""
配置摘要:
- Binance API: {'已設定' if self.binance_api_key else '未設定'}
- Bybit API: {'已設定' if self.bybit_api_key else '未設定'}
- Telegram: {'已設定' if self.telegram_bot_token else '未設定'}
- 查詢間隔: {self.query_interval_minutes} 分鐘
- 費率閾值: {self.funding_rate_threshold}
        """.strip()