"""
DeepSeek-Meter state updater v7
Writes state.txt in GBK encoding (Windows Chinese locale)
Lua reads with default encoding, gets correct Chinese text
"""
import time
import json
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "state.txt"
CONFIG_FILE = SCRIPT_DIR / "config.json"
BALANCE_WARN = 10.0
BALANCE_INTERVAL = 60

WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"]
PEAK_RANGES = [(540, 720), (840, 1080)]


def is_peak(h, m):
    t = h * 60 + m
    return any(s <= t < e for s, e in PEAK_RANGES)


def next_switch(h, m, s, peak):
    t = h * 60 + m
    if peak:
        nxt = (720 - t) if t < 720 else (1080 - t)
    else:
        if t < 540:
            nxt = 540 - t
        elif t < 840:
            nxt = 840 - t
        else:
            nxt = 540 + 1440 - t
    return max(nxt * 60 - s, 0)


def load_api_key():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("api_key", "")
    return ""


def fetch_balance(api_key):
    if not api_key:
        return "N/A|OK"
    req = urllib.request.Request(
        "https://api.deepseek.com/user/balance",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            bal = data.get("balance", None)
            if bal is None:
                infos = data.get("balance_infos", [])
                bal = float(infos[0].get("total_balance", 0)) if infos else 0
            else:
                bal = float(bal)
            return f"{bal:.2f}|{'ALERT' if bal < BALANCE_WARN else 'OK'}"
    except Exception:
        return "ERR|ERR"


def main():
    api_key = load_api_key()
    last_bal_time = 0
    balance = "N/A|OK"

    print("[DeepSeek-Meter] Running...")

    while True:
        now = time.time()
        t = time.localtime()
        h, m, s = t.tm_hour, t.tm_min, t.tm_sec
        peak = is_peak(h, m)
        rem = next_switch(h, m, s, peak)
        cd_m, cd_s = divmod(rem, 60)

        # Chinese strings
        datestr = f"{t.tm_mon}月{t.tm_mday}日 周{WEEKDAYS[t.tm_wday]}"
        phase_text = "\u6881\u6587\u5cf0" if peak else "\u6881\u6587\u8c37"

        if now - last_bal_time >= BALANCE_INTERVAL:
            balance = fetch_balance(api_key)
            last_bal_time = now
            print(f"[{h:02d}:{m:02d}:{s:02d}] {balance}")

        peak_flag = "1" if peak else "0"
        content = f"{h:02d}|{m:02d}|{s:02d}|{datestr}|{peak_flag}|{cd_m}|{cd_s:02d}|{balance}|{phase_text}"

        tmp = STATE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="gbk") as f:
            f.write(content)
        tmp.replace(STATE_FILE)
        time.sleep(1)


if __name__ == "__main__":
    main()
