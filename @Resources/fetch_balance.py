"""
DeepSeek-Meter 后台余额查询脚本
每5分钟查询一次 DeepSeek API 余额，写入 balance.txt
Rainmeter 读取该文件显示余额

用法：
  python fetch_balance.py                    # 启动后台查询（每5分钟）
  python fetch_balance.py --once             # 查询一次立即退出
  python fetch_balance.py --api-key sk-xxx   # 指定 API Key
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# ========== 配置 ==========
API_URL = "https://api.deepseek.com/user/balance"
BALANCE_FILE = Path(__file__).parent / "balance.txt"
CONFIG_FILE = Path(__file__).parent / "config.json"
INTERVAL = 300  # 5分钟
BALANCE_WARN = 10.0  # 低于此值标红
# ==========================


def load_api_key():
    """从命令行参数或 config.json 加载 API Key"""
    # 命令行优先
    if "--api-key" in sys.argv:
        idx = sys.argv.index("--api-key")
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]

    # config.json
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get("api_key", "")

    return ""


def fetch_balance(api_key):
    """查询 DeepSeek 余额，返回 (balance_str, is_valid)"""
    if not api_key:
        return ("NO_KEY", False)

    req = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

            # 兼容两种 API 格式
            balance = data.get("balance", None)
            if balance is None:
                # 新格式：balance_infos 数组
                balance_infos = data.get("balance_infos", [])
                if balance_infos:
                    balance = balance_infos[0].get("total_balance", 0)
                else:
                    balance = 0

            balance_float = float(balance)

            if balance_float < BALANCE_WARN:
                return (f"¥{balance_float:.2f} ALERT", True)
            else:
                return (f"¥{balance_float:.2f}", True)

    except urllib.error.HTTPError as e:
        return (f"ERR_{e.code}", False)
    except Exception as e:
        return ("ERR_NET", False)


def write_balance(balance_str):
    """写入余额到 balance.txt"""
    with open(BALANCE_FILE, "w", encoding="utf-8") as f:
        f.write(balance_str)


def main():
    once = "--once" in sys.argv
    api_key = load_api_key()

    if not api_key:
        print("[DeepSeek-Meter] 未找到 API Key！")
        print("  方法1: python fetch_balance.py --api-key sk-xxx")
        print(f"  方法2: 编辑 {CONFIG_FILE}")
        write_balance("NO_KEY")
        return

    print(f"[DeepSeek-Meter] API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"[DeepSeek-Meter] 余额文件: {BALANCE_FILE}")

    while True:
        balance_str, ok = fetch_balance(api_key)
        write_balance(balance_str)
        print(f"[{time.strftime('%H:%M:%S')}] 余额: {balance_str}")

        if once:
            break

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
