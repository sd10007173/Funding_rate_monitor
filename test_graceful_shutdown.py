#!/usr/bin/env python3
"""
測試優雅關閉功能
啟動程式後，等待 10 秒鐘，然後發送 SIGTERM 信號測試優雅關閉
"""

import asyncio
import signal
import subprocess
import time
import os


async def test_graceful_shutdown():
    print("測試優雅關閉功能...")
    
    # 啟動監控程式
    env = os.environ.copy()
    env['QUERY_INTERVAL_MINUTES'] = '1'  # 設置為 1 分鐘間隔以便測試
    
    process = subprocess.Popen(
        ['python', 'FR_monitor_v1.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    print(f"監控程式已啟動，PID: {process.pid}")
    
    # 等待 10 秒讓程式初始化
    print("等待 10 秒讓程式初始化...")
    await asyncio.sleep(10)
    
    # 發送 SIGTERM 信號
    print("發送 SIGTERM 信號進行優雅關閉...")
    process.send_signal(signal.SIGTERM)
    
    # 等待程式結束
    try:
        stdout, _ = process.communicate(timeout=30)
        print(f"程式已結束，返回碼: {process.returncode}")
        print("程式輸出:")
        print(stdout)
    except subprocess.TimeoutExpired:
        print("程式未在 30 秒內結束，強制終止...")
        process.kill()
        stdout, _ = process.communicate()
        print("程式輸出:")
        print(stdout)


if __name__ == "__main__":
    asyncio.run(test_graceful_shutdown())