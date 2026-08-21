"""
DeepSeek-Meter 独立桌面版
实时时钟 + DeepSeek API 余额监控
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── 常量 ───────────────────────────────────────────────
APP_NAME = "DeepSeek-Meter"
APP_VERSION = "2.0.3"
GITHUB_REPO = "xjzmStar/DeepSeek-Meter"
CONFIG_DIR = Path(os.environ.get("APPDATA", "~")) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"
AUTO_START_PATH = Path(os.environ.get("APPDATA", "")) / \
    r"Microsoft\Windows\Start Menu\Programs\Startup" / f"{APP_NAME}.vbs"

# ─── 主题配色 ────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg": "#1a1a2e",
        "time": "#FFFFFF",
        "date": "#888888",
    },
    "light": {
        "bg": "#f0f0f0",
        "time": "#1a1a2e",
        "date": "#666666",
    },
}

# ─── 配置管理 ────────────────────────────────────────────
DEFAULT_CONFIG = {
    "api_key": "",
    "auto_start": True,
    "low_balance_alert": True,
    "low_balance_threshold": 2.0,
    "topmost": True,
    "theme": "dark",  # "dark" / "light" / "system"
    "window_x": None,
    "window_y": None,
    "window_w": 280,
    "window_h": 160,
}


def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(saved)
            return cfg
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ─── 自动更新 ────────────────────────────────────────────
def parse_version(v: str):
    """将版本号字符串转为可比较的元组，如 '2.2.1' -> (2, 2, 1)"""
    try:
        parts = v.lstrip("v").split(".")
        return tuple(int(p) for p in parts)
    except Exception:
        return (0, 0, 0)


def check_update():
    """检查 GitHub Releases 是否有新版本，返回 (latest_ver, exe_url, body) 或 None"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{APP_NAME}/{APP_VERSION}",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        latest_ver = parse_version(latest_tag)
        current_ver = parse_version(APP_VERSION)

        if latest_ver <= current_ver:
            return None

        # 找 Windows exe 下载链接
        exe_url = None
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.lower().endswith(".exe"):
                exe_url = asset.get("browser_download_url")
                break

        if not exe_url:
            return None

        body = data.get("body", "") or ""
        return latest_tag, exe_url, body
    except Exception:
        return None


def download_and_install(exe_url: str, progress_cb=None):
    """下载新 exe 到临时位置，写 VBS 脚本替换并重启"""
    import tempfile

    # 下载到临时文件
    tmp_dir = Path(tempfile.gettempdir()) / APP_NAME
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_exe = tmp_dir / f"{APP_NAME}-update.exe"

    req = urllib.request.Request(exe_url, headers={
        "User-Agent": f"{APP_NAME}/{APP_VERSION}",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(tmp_exe, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total > 0:
                    progress_cb(downloaded, total)

    # 当前 exe 路径（PyInstaller onefile模式下 sys.executable 指向临时目录，用 sys.argv[0]）
    if getattr(sys, "frozen", False):
        current_exe = Path(sys.argv[0]).resolve()
    else:
        current_exe = Path(__file__).resolve()

    # 写 VBS 脚本：等旧进程退出 → 替换 → 启动 → 删除自身
    vbs_path = tmp_dir / "updater.vbs"
    vbs_content = f'''Set fso = CreateObject("Scripting.FileSystemObject")
WScript.Sleep 2000
On Error Resume Next
fso.CopyFile "{tmp_exe}", "{current_exe}", True
If Err.Number = 0 Then
    CreateObject("WScript.Shell").Run """{current_exe}"""
End If
WScript.Sleep 500
fso.DeleteFile "{tmp_exe}", True
fso.DeleteFile WScript.ScriptFullName, True
'''
    with open(vbs_path, "w", encoding="gbk") as f:
        f.write(vbs_content)

    # 启动 VBS 脚本，然后退出当前进程
    os.startfile(str(vbs_path))
    sys.exit(0)


# ─── API 查询 ────────────────────────────────────────────
WEEKDAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def fetch_balance(api_key: str):
    """查询 DeepSeek API 余额（兼容新旧两种 API 格式）"""
    if not api_key:
        return None, "NO_KEY"
    try:
        url = "https://api.deepseek.com/user/balance"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # 优先旧格式
            balance = data.get("balance", None)
            if balance is None:
                # 新格式：balance_infos 数组
                balance_infos = data.get("balance_infos", [])
                if balance_infos:
                    balance = balance_infos[0].get("total_balance", 0)
                else:
                    balance = 0
            return float(balance), "OK"
    except Exception as e:
        return None, str(e)


# ─── 峰谷判断 ────────────────────────────────────────────
def get_peak_valley():
    """返回当前时段的显示文本和颜色"""
    now = datetime.now()
    hour = now.hour
    # 峰段: 9:00-12:00, 14:00-18:00
    is_peak = (9 <= hour < 12) or (14 <= hour < 18)
    if is_peak:
        return "梁文峰", "#C83232"  # 红
    else:
        return "梁文谷", "#00A050"  # 绿


def get_balance_color(balance):
    """余额动态变色"""
    if balance is None:
        return "#FF4444"
    threshold = load_config().get("low_balance_threshold", 2.0)
    if balance <= 0:
        return "#FF4444"  # 欠费红色
    if balance <= threshold:
        return "#FF9800"  # 低余额橙色
    return "#00C853"  # 充足绿色


def get_system_theme():
    """检测系统主题（Windows）"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value else "dark"
    except Exception:
        return "dark"


def resolve_theme(theme_setting):
    """解析主题设置，返回实际使用的主题"""
    if theme_setting == "system":
        return get_system_theme()
    return theme_setting


# ─── 开机自启 ────────────────────────────────────────────
def set_auto_start(enable: bool):
    if enable:
        # PyInstaller onefile 模式：sys.executable 指向临时目录，
        # 需要用 sys.argv[0] 获取用户实际运行的 exe 路径
        if getattr(sys, 'frozen', False):
            exe_path = sys.argv[0]
        else:
            exe_path = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(exe_path):
                exe_path = sys.executable
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{exe_path}""", 0, False'''
        try:
            with open(AUTO_START_PATH, "w", encoding="gbk") as f:
                f.write(vbs_content)
            return True
        except Exception:
            return False
    else:
        try:
            if AUTO_START_PATH.exists():
                AUTO_START_PATH.unlink()
            return True
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════
#  主界面
# ═══════════════════════════════════════════════════════════
class DeepSeekMeter(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.cfg = load_config()
        self.balance = None
        self.balance_status = ""
        self.running = True
        self.current_theme = resolve_theme(self.cfg["theme"])

        # ── 主题 ──
        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        # ── 窗口设置 ──
        self.title(APP_NAME)
        self.geometry("280x160")
        self.minsize(220, 120)
        self.attributes("-topmost", self.cfg["topmost"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 恢复窗口位置和大小
        if self.cfg["window_x"] is not None:
            w = self.cfg.get("window_w", 280)
            h = self.cfg.get("window_h", 160)
            self.geometry(f"{w}x{h}+{self.cfg['window_x']}+{self.cfg['window_y']}")

        # 记录窗口位置
        self.bind("<ButtonRelease-1>", self._save_position)
        self.bind("<B1-Motion>", self._on_drag)

        # ── UI ──
        self._build_ui()

        # ── 启动后台线程 ──
        self._clock_after_id = None
        self._update_clock()
        self._start_balance_thread()

    def _get_colors(self):
        """获取当前主题配色"""
        return THEMES.get(self.current_theme, THEMES["dark"])

    def _build_ui(self):
        """构建界面"""
        colors = self._get_colors()
        self.configure(fg_color=colors["bg"])

        # ── 顶部栏：图钉按钮 ──
        top_bar = ctk.CTkFrame(self, fg_color="transparent", height=32)
        top_bar.pack(fill="x", padx=8, pady=(8, 0))
        top_bar.pack_propagate(False)

        self.pin_state = self.cfg["topmost"]
        pin_color = "#2196F3" if self.pin_state else "#666"
        self.pin_btn = ctk.CTkButton(
            top_bar, text="📌", width=32, height=28,
            font=ctk.CTkFont(size=16),
            fg_color=pin_color,
            hover_color="#1976D2",
            command=self._toggle_topmost
        )
        self.pin_btn.pack(side="right", padx=4)

        # 容器
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        # 时间
        self.time_label = ctk.CTkLabel(
            self.container, text="00:00:00",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=colors["time"]
        )
        self.time_label.pack(pady=(4, 0), expand=True)

        # 峰谷 + 金额 同一行
        self.info_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.info_frame.pack(pady=(4, 0), expand=True)

        pv_text, pv_color = get_peak_valley()
        self.pv_label = ctk.CTkLabel(
            self.info_frame, text=pv_text,
            font=ctk.CTkFont(size=18),
            text_color=pv_color
        )
        self.pv_label.pack(side="left", padx=(0, 12))

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="¥--",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#00C853"
        )
        self.balance_label.pack(side="left")

        # 日期
        self.date_label = ctk.CTkLabel(
            self.container, text="",
            font=ctk.CTkFont(size=11),
            text_color=colors["date"]
        )
        self.date_label.pack(pady=(6, 0), expand=True)

    def _refresh_theme(self):
        """刷新主题"""
        self.current_theme = resolve_theme(self.cfg["theme"])
        ctk.set_appearance_mode(self.current_theme)
        colors = self._get_colors()
        self.configure(fg_color=colors["bg"])
        self.time_label.configure(text_color=colors["time"])
        self.date_label.configure(text_color=colors["date"])

    def _update_clock(self):
        """每秒更新时钟"""
        if not self.running:
            return
        now = datetime.now()
        self.time_label.configure(text=now.strftime("%H:%M:%S"))
        wd = WEEKDAYS_CN[now.weekday()]
        self.date_label.configure(text=f"{now.strftime('%Y年%m月%d日')} {wd}")

        # 更新峰谷
        pv_text, pv_color = get_peak_valley()
        self.pv_label.configure(text=pv_text, text_color=pv_color)

        self._clock_after_id = self.after(1000, self._update_clock)

    def _toggle_topmost(self):
        """切换窗口置顶状态"""
        self.pin_state = not self.pin_state
        self.cfg["topmost"] = self.pin_state
        self.attributes("-topmost", self.pin_state)
        self._update_pin_style()
        save_config(self.cfg)

    def _update_pin_style(self):
        """更新图钉按钮样式"""
        if self.pin_state:
            self.pin_btn.configure(fg_color="#2196F3", hover_color="#1976D2")
        else:
            self.pin_btn.configure(fg_color="#666", hover_color="#555")

    def _start_balance_thread(self):
        """后台线程查余额"""
        def _worker():
            while self.running:
                if self.cfg["api_key"]:
                    balance, status = fetch_balance(self.cfg["api_key"])
                    if self.running:
                        self.after(0, self._update_balance, balance, status)
                time.sleep(60)  # 每分钟查一次

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        # 立即查一次
        self.after(500, self._do_first_query)

    def _do_first_query(self):
        if self.cfg["api_key"]:
            t = threading.Thread(target=self._first_query_worker, daemon=True)
            t.start()

    def _first_query_worker(self):
        balance, status = fetch_balance(self.cfg["api_key"])
        if self.running:
            self.after(0, self._update_balance, balance, status)

    def _update_balance(self, balance, status):
        self.balance = balance
        self.balance_status = status

        if status == "NO_KEY":
            self.balance_label.configure(text="¥未配置", text_color="#FF9800")
        elif status == "OK":
            color = get_balance_color(balance)
            self.balance_label.configure(text=f"¥{balance:.2f}", text_color=color)
            # 低余额提醒
            if (self.cfg["low_balance_alert"] and
                    balance < self.cfg["low_balance_threshold"]):
                self.after(0, self._low_balance_notify, balance)
        else:
            self.balance_label.configure(text="¥查询失败", text_color="#FF4444")

    def _low_balance_notify(self, balance):
        if not self.running:
            return
        if not hasattr(self, "_last_alert") or time.time() - self._last_alert > 3600:
            self._last_alert = time.time()
            messagebox.showwarning(
                "余额不足",
                f"DeepSeek 余额仅剩 ¥{balance:.2f}，请及时充值！"
            )

    # ── 窗口拖动 ──
    def _on_drag(self, event):
        x = self.winfo_x() + event.x
        y = self.winfo_y() + event.y
        self.geometry(f"+{x}+{y}")

    def _save_position(self, event=None):
        self.cfg["window_x"] = self.winfo_x()
        self.cfg["window_y"] = self.winfo_y()
        self.cfg["window_w"] = self.winfo_width()
        self.cfg["window_h"] = self.winfo_height()
        save_config(self.cfg)

    def _on_close(self):
        self._save_position()
        self.withdraw()  # 隐藏到托盘，不设 running=False

    def _on_show(self):
        """从托盘恢复显示时重启时钟"""
        self.deiconify()
        # 取消旧的定时器再重启，避免重复
        if self._clock_after_id:
            self.after_cancel(self._clock_after_id)
            self._clock_after_id = None
        self._update_clock()


# ═══════════════════════════════════════════════════════════
#  设置窗口
# ═══════════════════════════════════════════════════════════
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, cfg, on_save):
        super().__init__(parent)
        self.original_cfg = cfg.copy()  # 保存原始配置，用于取消时恢复
        self.cfg = cfg.copy()
        self.on_save = on_save

        # 获取当前主题颜色
        theme = resolve_theme(self.cfg["theme"])
        bg = THEMES[theme]["bg"]
        card_bg = "#252540" if theme == "dark" else "#e0e0e0"
        self._card_bg = card_bg

        self.title("设置")
        self.geometry("380x460")
        self.resizable(False, False)
        self.configure(fg_color=bg)
        self.transient(parent)
        self.grab_set()

        # ── 外观设置 ──
        appearance_frame = ctk.CTkFrame(self, fg_color=card_bg)
        appearance_frame.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(appearance_frame, text="外观",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))

        # 主题选择
        theme_frame = ctk.CTkFrame(appearance_frame, fg_color="transparent")
        theme_frame.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(theme_frame, text="主题",
                      font=ctk.CTkFont(size=12)).pack(side="left")

        self.theme_var = tk.StringVar(value=self.cfg["theme"])
        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            variable=self.theme_var,
            values=["dark", "light", "system"],
            width=120
        )
        self.theme_menu.pack(side="right")

        # 窗口置顶
        self.topmost_var = tk.BooleanVar(value=self.cfg["topmost"])
        ctk.CTkCheckBox(
            appearance_frame, text="窗口置顶",
            variable=self.topmost_var
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # ── 功能设置 ──
        func_frame = ctk.CTkFrame(self, fg_color=card_bg)
        func_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(func_frame, text="功能",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))

        # 开机自启
        self.autostart_var = tk.BooleanVar(value=self.cfg["auto_start"])
        ctk.CTkCheckBox(func_frame, text="开机自启动",
                         variable=self.autostart_var).pack(anchor="w", padx=12, pady=2)

        # 低余额提醒
        self.alert_var = tk.BooleanVar(value=self.cfg["low_balance_alert"])
        ctk.CTkCheckBox(func_frame, text="余额不足时提醒",
                         variable=self.alert_var).pack(anchor="w", padx=12, pady=2)

        # 阈值
        threshold_frame = ctk.CTkFrame(func_frame, fg_color="transparent")
        threshold_frame.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkLabel(threshold_frame, text="提醒阈值 ¥",
                      font=ctk.CTkFont(size=12)).pack(side="left")
        self.threshold_entry = ctk.CTkEntry(threshold_frame, width=80)
        self.threshold_entry.pack(side="left", padx=(4, 0))
        self.threshold_entry.insert(0, str(self.cfg["low_balance_threshold"]))

        # ── API Key ──
        api_frame = ctk.CTkFrame(self, fg_color=card_bg)
        api_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(api_frame, text="API Key",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))

        self.api_entry = ctk.CTkEntry(api_frame, width=340, show="*",
                                       placeholder_text="sk-xxxxxxxx")
        self.api_entry.pack(padx=12, pady=(0, 4))
        if self.cfg["api_key"]:
            self.api_entry.insert(0, self.cfg["api_key"])

        self.show_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(api_frame, text="显示 Key", variable=self.show_var,
                         command=self._toggle_show).pack(anchor="w", padx=12, pady=(0, 8))

        # ── 按钮 ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(12, 15))
        ctk.CTkButton(btn_frame, text="确认", width=140, height=36,
                       font=ctk.CTkFont(size=14),
                       command=self._confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", width=140, height=36,
                       font=ctk.CTkFont(size=14),
                       fg_color="#555", hover_color="#666",
                       command=self._cancel).pack(side="left", padx=10)

    def _toggle_show(self):
        self.api_entry.configure(show="" if self.show_var.get() else "*")

    def _confirm(self):
        """确认：应用所有设置并保存"""
        self.cfg["api_key"] = self.api_entry.get().strip()
        self.cfg["auto_start"] = self.autostart_var.get()
        self.cfg["low_balance_alert"] = self.alert_var.get()
        self.cfg["topmost"] = self.topmost_var.get()
        self.cfg["theme"] = self.theme_var.get()
        try:
            self.cfg["low_balance_threshold"] = float(self.threshold_entry.get())
        except ValueError:
            pass
        save_config(self.cfg)
        set_auto_start(self.cfg["auto_start"])
        self.on_save(self.cfg)
        self.destroy()

    def _cancel(self):
        """取消：恢复原始设置"""
        self.on_save(self.original_cfg)
        self.destroy()


# ═══════════════════════════════════════════════════════════
#  系统托盘
# ═══════════════════════════════════════════════════════════
def create_tray_icon(app):
    """创建系统托盘图标"""
    import pystray
    from PIL import Image, ImageDraw

    def make_icon():
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill="#2196F3", outline="#FFFFFF", width=2)
        draw.text((20, 14), "D", fill="#FFFFFF")
        return img

    def on_show(icon, item):
        app.after(0, app._on_show)

    def on_check_update(icon, item):
        app.after(0, lambda: _do_update_check(app))

    def on_settings(icon, item):
        app.after(0, lambda: SettingsWindow(app, app.cfg, app._on_settings_save))

    def on_quit(icon, item):
        app.running = False
        app.after(0, app.destroy)
        icon.stop()

    icon = pystray.Icon(
        APP_NAME,
        make_icon(),
        APP_NAME,
        menu=pystray.Menu(
            pystray.MenuItem("显示", on_show, default=True),
            pystray.MenuItem("设置", on_settings),
            pystray.MenuItem("检查更新", on_check_update),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", on_quit),
        )
    )
    return icon


# ═══════════════════════════════════════════════════════════
#  更新对话框
# ═══════════════════════════════════════════════════════════
def _do_update_check(app, silent=False):
    """检查更新，弹出提示或自动下载"""
    def _worker():
        result = check_update()
        app.after(0, lambda: _show_update_result(app, result, silent))

    threading.Thread(target=_worker, daemon=True).start()


def _show_update_result(app, result, silent):
    """显示更新检查结果"""
    if result is None:
        if not silent:
            messagebox.showinfo("检查更新", f"当前已是最新版本 ({APP_VERSION})")
        return

    latest_tag, exe_url, body = result
    # 截取 changelog 前几行
    lines = [l for l in body.strip().splitlines() if l.strip()]
    summary = "\n".join(lines[:10])
    if len(lines) > 10:
        summary += "\n..."

    msg = f"发现新版本 {latest_tag}（当前 {APP_VERSION}）\n\n{summary}\n\n是否立即下载更新？"
    if messagebox.askyesno("发现更新", msg):
        _show_download_progress(app, exe_url, latest_tag)


def _show_download_progress(app, exe_url, version):
    """显示下载进度条窗口"""
    win = ctk.CTkToplevel(app)
    win.title("正在更新")
    win.geometry("360x150")
    win.resizable(False, False)
    win.transient(app)
    win.grab_set()

    theme = resolve_theme(app.cfg["theme"])
    bg = THEMES[theme]["bg"]
    win.configure(fg_color=bg)

    ctk.CTkLabel(win, text=f"正在下载 {version}...",
                  font=ctk.CTkFont(size=14)).pack(pady=(20, 10))

    progress = ctk.CTkProgressBar(win, width=300)
    progress.pack(pady=5)
    progress.set(0)

    status_label = ctk.CTkLabel(win, text="准备下载...",
                                 font=ctk.CTkFont(size=11))
    status_label.pack(pady=5)

    def _download():
        try:
            def _on_progress(downloaded, total):
                pct = downloaded / total if total > 0 else 0
                mb_dl = downloaded / 1048576
                mb_total = total / 1048576
                app.after(0, lambda: progress.set(pct))
                app.after(0, lambda: status_label.configure(
                    text=f"{mb_dl:.1f} / {mb_total:.1f} MB"))

            download_and_install(exe_url, _on_progress)
        except Exception as e:
            app.after(0, lambda: messagebox.showerror("更新失败", str(e)))
            app.after(0, win.destroy)

    threading.Thread(target=_download, daemon=True).start()


# ═══════════════════════════════════════════════════════════
#  启动
# ═══════════════════════════════════════════════════════════
def main():
    app = DeepSeekMeter()

    def on_settings_save(new_cfg):
        app.cfg = new_cfg
        # 应用置顶
        app.attributes("-topmost", new_cfg["topmost"])
        # 同步图钉状态
        app.pin_state = new_cfg["topmost"]
        app._update_pin_style()
        # 应用主题
        app._refresh_theme()

    app._on_settings_save = on_settings_save

    # 托盘线程
    icon = create_tray_icon(app)
    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    # 首次启动引导
    if not app.cfg["api_key"]:
        app.after(1000, lambda: SettingsWindow(app, app.cfg, on_settings_save))

    # 启动后静默检查更新
    app.after(3000, lambda: _do_update_check(app, silent=True))

    app.mainloop()


if __name__ == "__main__":
    main()
