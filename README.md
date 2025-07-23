# 資金費率監控系統 V1.0

監控 Binance 和 Bybit 套利組合的資金費率，並定時推送到 Telegram 頻道。

## 功能

1. **套利組合偵測**：自動偵測交易對相同、方向相反、數量相同的持倉組合
2. **資金費率監控**：查詢兩交易所的當前資金費率
3. **費率差值計算**：計算做空交易所費率 - 做多交易所費率
4. **Telegram 通知**：定時推送監控結果到 Telegram 頻道
5. **閾值警告**：當費率差值低於設定閾值時發出警告

## 安裝

1. 安裝 Python 依賴：
```bash
pip install -r requirements.txt
```

2. 複製環境變數範本：
```bash
cp .env.example .env
```

3. 編輯 `.env` 檔案，填入您的 API 憑證和設定。

## 環境變數設定

在 `.env` 檔案中設定以下變數：

```bash
# API 憑證
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret

# Telegram 設定
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# 監控參數
QUERY_INTERVAL_MINUTES=30
FUNDING_RATE_THRESHOLD=0.0
```

## 使用方式

### 持續監控模式
```bash
python FR_monitor_v1.py
```

### 單次執行模式
```bash
python FR_monitor_v1.py --once
```

## 報告格式

Telegram 通知範例：
```
資金費率監控報告
2025-01-23 16:00 UTC

  BTCUSDT 套利組合
  ├ Binance(多)：+0.0125%
  ├ Bybit(空)：-0.0089%
  └ 費率差值：-0.0214%

  ETHUSDT 套利組合
  ├ Binance(空)：-0.0156%
  ├ Bybit(多)：+0.0098%
  └ 費率差值：+0.0254%
```

## 專案結構

```
FR_monitor_v1/
├── FR_monitor_v1.py           # 主程式
├── fr_monitor/                # 核心模組
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── binance_client.py      # Binance API 客戶端
│   ├── bybit_client.py        # Bybit API 客戶端
│   ├── arbitrage_detector.py  # 套利組合偵測
│   ├── funding_rate_monitor.py # 資金費率監控
│   └── telegram_notifier.py   # Telegram 通知
├── requirements.txt           # Python 依賴
├── .env.example              # 環境變數範本
└── README.md                 # 說明文件
```

## 注意事項

- 需要有效的 Binance 和 Bybit API 憑證
- 需要建立 Telegram Bot 並獲取 Token
- 確保 API 憑證有足夠的權限查詢持倉和市場資訊
- 程式會自動處理 API 錯誤並發送錯誤通知到 Telegram