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
APP_VERSION = "2.2.0"
GITHUB_REPO = "xjzmStar/DeepSeek-Meter"


def get_data_path(filename):
    """获取数据文件路径，兼容PyInstaller onefile模式"""
    if getattr(sys, "frozen", False):
        # PyInstaller onefile: _MEIPASS 是临时解压目录
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)
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

# ─── 字体 ──────────────────────────────────────────────
FONT_PRESETS = ["默认", "微软雅黑", "思源黑体", "等线", "楷体", "宋体", "黑体", "Consolas", "Cascadia Code"]
FONT_SIZES = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "22", "24", "26", "28", "36", "48", "72"]

# 基准字号 12pt 时各元素的实际大小
FONT_BASE = {
    "time": 36,
    "balance": 22,
    "peak_valley": 18,
    "date": 11,
}
FONT_REF_SIZE = 12  # 基准字号


def get_font_family(preset_name):
    """根据字体名返回实际字体族名，空字符串=系统默认"""
    if not preset_name or preset_name == "默认":
        return None
    return preset_name


def make_font(preset_name, ref_pt, size_key):
    """创建按比例缩放的字体（ref_pt=基准字号，各元素按比例放大）"""
    family = get_font_family(preset_name)
    base = FONT_BASE.get(size_key, 14)
    size = max(8, round(base * ref_pt / FONT_REF_SIZE))
    if family:
        return ctk.CTkFont(family=family, size=size)
    return ctk.CTkFont(size=size)


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
    "font_family": "默认",
    "font_size": 14,  # 字号（pt）
    # ── 快捷键 ──
    "hotkeys": {
        "toggle_visibility": "ctrl+alt+d",
        "open_settings": "ctrl+alt+s",
        "toggle_mode": "ctrl+alt+m",
        "quit": "ctrl+alt+q",
    },
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
    """检查 GitHub Releases 是否有新版本，返回 (latest_tag, release_url, body) 或 None"""
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

        release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest")
        body = data.get("body", "") or ""
        return latest_tag, release_url, body
    except Exception:
        return None


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
    """返回当前时段的显示文本和颜色（2026-08-23起周末全天低谷）"""
    now = datetime.now()
    weekday = now.weekday()  # 0=周一 ... 6=周日
    hour = now.hour
    # 周末全天低谷（周六=5, 周日=6）
    if weekday >= 5:
        return "梁文谷", "#00A050"  # 绿
    # 工作日峰段: 9:00-12:00, 14:00-18:00
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
        # 窗口大小根据字号动态计算（12pt 为基准：280x160）
        base_size = self.cfg.get("font_size", 12)
        scale = max(0.6, base_size / 12)
        init_w = max(220, int(280 * scale))
        init_h = max(120, int(160 * scale))
        self.geometry(f"{init_w}x{init_h}")
        self.minsize(220, 120)
        self.attributes("-topmost", self.cfg["topmost"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._settings_win = None  # 跟踪设置窗口
        self._opening_settings = False  # 防止 _on_map 重复显示
        self.bind("<Map>", self._on_map)  # 任务栏恢复时触发

        # ── 窗口图标 ──
        try:
            self._set_window_icon()
        except Exception:
            pass

        # 恢复窗口位置和大小（多屏位置保存）
        if self.cfg["window_x"] is not None:
            w = self.cfg.get("window_w", init_w)
            h = self.cfg.get("window_h", init_h)
            self.geometry(f"{w}x{h}+{self.cfg['window_x']}+{self.cfg['window_y']}")

        # 记录窗口位置（拖拽 + 松手都保存，支持多屏坐标）
        self.bind("<ButtonPress-1>", self._on_drag_start)
        self.bind("<ButtonRelease-1>", self._save_position)
        self.bind("<B1-Motion>", self._on_drag)

        # ── UI ──
        self._build_ui()

        # ── 启动后台线程 ──
        self._clock_after_id = None
        self._update_clock()
        self._start_balance_thread()

        # ── 全局快捷键 ──
        self.setup_hotkeys()

    def _set_window_icon(self):
        """设置窗口图标（标题栏 + 任务栏）"""
        from PIL import Image
        import tkinter as _tk
        try:
            from PIL import ImageTk
        except ImportError:
            ImageTk = None

        # 优先用 ico 文件设置标题栏/任务栏图标
        ico_path = get_data_path("app.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
                return
            except Exception:
                pass

        # fallback: 用 PNG 缩放后 iconphoto
        logo_path = get_data_path("app_logo.png")
        if os.path.exists(logo_path) and ImageTk:
            img = Image.open(logo_path).resize((32, 32), Image.LANCZOS)
            self._window_icon_ref = ImageTk.PhotoImage(img)
            self.iconphoto(True, self._window_icon_ref)

    def _get_colors(self):
        """获取当前主题配色"""
        return THEMES.get(self.current_theme, THEMES["dark"])

    def _build_ui(self):
        """构建界面"""
        colors = self._get_colors()
        self.configure(fg_color=colors["bg"])

        font_preset = self.cfg.get("font_family", "默认")
        font_size = self.cfg.get("font_size", 1.0)

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
            font=make_font(font_preset, font_size, "time"),
            text_color=colors["time"]
        )
        self.time_label.pack(pady=(4, 0), expand=True)

        # 峰谷 + 金额 同一行
        self.info_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.info_frame.pack(pady=(4, 0), expand=True)

        pv_text, pv_color = get_peak_valley()
        self.pv_label = ctk.CTkLabel(
            self.info_frame, text=pv_text,
            font=make_font(font_preset, font_size, "peak_valley"),
            text_color=pv_color
        )
        self.pv_label.pack(side="left", padx=(0, 12))

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="¥--",
            font=make_font(font_preset, font_size, "balance"),
            text_color="#00C853"
        )
        self.balance_label.pack(side="left")

        # 日期
        self.date_label = ctk.CTkLabel(
            self.container, text="",
            font=make_font(font_preset, font_size, "date"),
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
        self._refresh_fonts()

    def _refresh_fonts(self):
        """刷新字体样式和大小"""
        font_preset = self.cfg.get("font_family", "默认")
        font_size = self.cfg.get("font_size", 14)
        self.time_label.configure(font=make_font(font_preset, font_size, "time"))
        self.balance_label.configure(font=make_font(font_preset, font_size, "balance"))
        self.pv_label.configure(font=make_font(font_preset, font_size, "peak_valley"))
        self.date_label.configure(font=make_font(font_preset, font_size, "date"))

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
    def _on_drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")

    def _save_position(self, event=None):
        self.cfg["window_x"] = self.winfo_x()
        self.cfg["window_y"] = self.winfo_y()
        self.cfg["window_w"] = self.winfo_width()
        self.cfg["window_h"] = self.winfo_height()
        save_config(self.cfg)

    def _on_map(self, event=None):
        """窗口从隐藏恢复时，同步显示设置窗口"""
        if self._opening_settings:
            return
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.deiconify()
            self._settings_win.lift()

    def _on_taskbar_click(self, event=None):
        """任务栏点击时显示主窗口+设置窗口"""
        self.deiconify()
        self.lift()
        self.focus_force()
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.deiconify()
            self._settings_win.lift()

    # ── 全局快捷键 ──
    def setup_hotkeys(self):
        """注册全局快捷键"""
        try:
            import keyboard
            hk = self.cfg.get("hotkeys", {})
            if hk.get("toggle_visibility"):
                keyboard.add_hotkey(hk["toggle_visibility"], self._hotkey_toggle_visibility, suppress=False)
            if hk.get("open_settings"):
                keyboard.add_hotkey(hk["open_settings"], self._hotkey_open_settings, suppress=False)
            if hk.get("toggle_mode"):
                keyboard.add_hotkey(hk["toggle_mode"], lambda: None, suppress=False)  # 暂不实现挂件模式
            if hk.get("quit"):
                keyboard.add_hotkey(hk["quit"], self._hotkey_quit, suppress=False)
        except ImportError:
            pass  # keyboard 库未安装则跳过
        except Exception:
            pass

    def _hotkey_toggle_visibility(self):
        """快捷键：显示/隐藏窗口"""
        if self.state() == "withdrawn":
            self.after(0, self._on_show)
        else:
            self.after(0, self.withdraw)

    def _hotkey_open_settings(self):
        """快捷键：打开设置"""
        self.after(0, self._open_settings_from_hotkey)

    def _open_settings_from_hotkey(self):
        if self._opening_settings:
            return
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return
        self._opening_settings = True
        self._settings_win = SettingsWindow(self, self.cfg, self._on_settings_save)
        self._opening_settings = False

    def _hotkey_quit(self):
        """快捷键：退出程序"""
        self.running = False
        self.after(0, self.destroy)

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
#  字体选择弹窗（虚拟滚动，按需渲染）
# ═══════════════════════════════════════════════════════════
class FontPickerWindow(ctk.CTkToplevel):
    def __init__(self, parent, current_font, on_select):
        super().__init__(parent)
        self.on_select = on_select
        self.current_font = current_font

        theme = resolve_theme(parent.cfg["theme"])
        bg = THEMES[theme]["bg"]
        card_bg = "#252540" if theme == "dark" else "#e0e0e0"
        btn_hover = "#3a3a5c" if theme == "dark" else "#b0b0b0"
        btn_fg = "#2a2a4a" if theme == "dark" else "#c8c8c8"
        self._card_bg = card_bg
        self._btn_hover = btn_hover
        self._btn_fg = btn_fg
        self._theme = theme

        self.title("选择字体")
        self.geometry("300x420")
        self.configure(fg_color=bg)
        self.transient(parent)
        self.grab_set()

        # 搜索框
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=12, pady=(12, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(search_frame, textvariable=self.search_var,
                      placeholder_text="搜索字体...", height=32).pack(fill="x")

        # 滚动容器
        list_frame = ctk.CTkFrame(self, fg_color=card_bg)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.font_list = ctk.CTkScrollableFrame(list_frame, fg_color="transparent",
                                                  scrollbar_fg_color=card_bg)
        self.font_list.pack(fill="both", expand=True)

        # 全量字体数据（9种预设）
        self.all_fonts = FONT_PRESETS
        self.filtered = self.all_fonts[:]
        self.buttons = {}
        self._selected_btn = None
        self._render_page()

    def _make_btn(self, fname):
        """创建一个字体按钮"""
        is_sel = (fname == self.current_font)
        text_color = "#fff" if is_sel else "#222"
        if self._theme == "dark":
            text_color = "#fff" if is_sel else "#e8e8e8"
        return ctk.CTkButton(
            self.font_list, text=fname, height=34, anchor="w",
            fg_color="#2196F3" if is_sel else self._btn_fg,
            hover_color=self._btn_hover,
            text_color=text_color,
            font=ctk.CTkFont(size=12),
            command=lambda f=fname: self._pick(f)
        )

    def _render_page(self, search=""):
        """渲染字体按钮列表"""
        for w in self.font_list.winfo_children():
            w.destroy()
        self.buttons.clear()
        self._selected_btn = None

        for fname in self.filtered:
            btn = self._make_btn(fname)
            btn.pack(fill="x", padx=4, pady=3)
            self.buttons[fname] = btn
            if fname == self.current_font:
                self._selected_btn = btn

    def _on_search(self, *args):
        keyword = self.search_var.get().lower()
        self.filtered = [f for f in self.all_fonts if keyword in f.lower()]
        self._render_page(keyword)

    def _pick(self, fname):
        self.on_select(fname)
        self.destroy()


# ═══════════════════════════════════════════════════════════
#  设置窗口
# ═══════════════════════════════════════════════════════════
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, cfg, on_save):
        super().__init__()
        self.withdraw()  # 先隐藏，布局完再显示，防止闪烁
        self.original_cfg = cfg.copy()  # 保存原始配置，用于取消时恢复
        self.cfg = cfg.copy()
        self.on_save = on_save
        self._parent = parent

        # 获取当前主题颜色
        theme = resolve_theme(self.cfg["theme"])
        bg = THEMES[theme]["bg"]
        card_bg = "#252540" if theme == "dark" else "#e0e0e0"
        time_color = THEMES[theme]["time"]
        self._card_bg = card_bg

        self.title("设置")
        self.geometry("380x520")
        self.resizable(False, False)
        self.configure(fg_color=bg)

        # 设置窗口图标
        try:
            ico_path = get_data_path("app.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            else:
                from PIL import Image, ImageTk
                logo_path = get_data_path("app_logo.png")
                if os.path.exists(logo_path):
                    img = Image.open(logo_path).resize((32, 32), Image.LANCZOS)
                    self._icon_ref = ImageTk.PhotoImage(img)
                    self.iconphoto(True, self._icon_ref)
        except Exception:
            pass

        # ── 滚动容器 ──
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                               scrollbar_fg_color=bg)
        self._scroll.pack(fill="both", expand=True, padx=2, pady=(2, 0))

        # ── 外观设置 ──
        appearance_frame = ctk.CTkFrame(self._scroll, fg_color=card_bg)
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

        # ── 字体设置 ──
        font_frame = ctk.CTkFrame(self._scroll, fg_color=card_bg)
        font_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(font_frame, text="字体",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))

        # 字体样式 - 点击打开字体选择弹窗
        style_row = ctk.CTkFrame(font_frame, fg_color="transparent")
        style_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(style_row, text="字体样式",
                      font=ctk.CTkFont(size=12)).pack(side="left")

        self.font_var = tk.StringVar(value=self.cfg.get("font_family", "默认"))
        self.font_btn = ctk.CTkButton(
            style_row, text=self.font_var.get(), width=160, height=32,
            anchor="w", font=ctk.CTkFont(size=12),
            command=self._open_font_picker
        )
        self.font_btn.pack(side="right")

        # 字体大小 - 下拉菜单
        size_row = ctk.CTkFrame(font_frame, fg_color="transparent")
        size_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(size_row, text="字体大小",
                      font=ctk.CTkFont(size=12)).pack(side="left")
        self.font_size_var = tk.StringVar(value=str(self.cfg.get("font_size", 14)))
        self.font_size_menu = ctk.CTkOptionMenu(
            size_row,
            variable=self.font_size_var,
            values=FONT_SIZES,
            width=80,
            command=lambda _: self._on_font_size_change()
        )
        self.font_size_menu.pack(side="right")

        # 字体预览
        self.font_preview = ctk.CTkLabel(
            font_frame, text="预览：11:59:59 ¥88.88",
            font=ctk.CTkFont(size=13),
            text_color=time_color
        )
        self.font_preview.pack(padx=12, pady=(0, 8))

        # ── 功能设置 ──
        func_frame = ctk.CTkFrame(self._scroll, fg_color=card_bg)
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
        api_frame = ctk.CTkFrame(self._scroll, fg_color=card_bg)
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
        btn_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        btn_frame.pack(pady=(12, 15))
        ctk.CTkButton(btn_frame, text="确认", width=140, height=36,
                       font=ctk.CTkFont(size=14),
                       command=self._confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", width=140, height=36,
                       font=ctk.CTkFont(size=14),
                       fg_color="#555", hover_color="#666",
                       command=self._cancel).pack(side="left", padx=10)

        # 布局完成后再显示，防止闪烁
        self.update_idletasks()
        self.deiconify()

    def _toggle_show(self):
        self.api_entry.configure(show="" if self.show_var.get() else "*")

    def _open_font_picker(self):
        """打开字体选择弹窗"""
        FontPickerWindow(self, self.font_var.get(), self._on_font_picked)

    def _on_font_picked(self, fname):
        """字体选择回调"""
        self.font_var.set(fname)
        self.font_btn.configure(text=fname)
        self._on_font_size_change()

    def _on_font_size_change(self, _=None):
        """字体大小下拉变化时更新预览"""
        ref_pt = int(self.font_size_var.get())
        preset = self.font_var.get()
        family = get_font_family(preset)
        size = max(8, round(13 * ref_pt / FONT_REF_SIZE))
        if family:
            self.font_preview.configure(font=ctk.CTkFont(family=family, size=size))
        else:
            self.font_preview.configure(font=ctk.CTkFont(size=size))

    def _confirm(self):
        """确认：应用所有设置并保存"""
        self.cfg["api_key"] = self.api_entry.get().strip()
        self.cfg["auto_start"] = self.autostart_var.get()
        self.cfg["low_balance_alert"] = self.alert_var.get()
        self.cfg["topmost"] = self.topmost_var.get()
        self.cfg["theme"] = self.theme_var.get()
        self.cfg["font_family"] = self.font_var.get()
        self.cfg["font_size"] = int(self.font_size_var.get())
        try:
            self.cfg["low_balance_threshold"] = float(self.threshold_entry.get())
        except ValueError:
            pass
        save_config(self.cfg)
        set_auto_start(self.cfg["auto_start"])
        self.on_save(self.cfg)
        self._clear_ref()
        self.destroy()

    def _cancel(self):
        """取消：恢复原始设置"""
        self.on_save(self.original_cfg)
        self._clear_ref()
        self.destroy()

    def _clear_ref(self):
        """清除父窗口中的设置窗口引用"""
        parent = getattr(self, '_parent', None)
        if parent and hasattr(parent, '_settings_win'):
            parent._settings_win = None


# ═══════════════════════════════════════════════════════════
#  系统托盘
# ═══════════════════════════════════════════════════════════
def create_tray_icon(app):
    """创建系统托盘图标"""
    import pystray
    from PIL import Image, ImageDraw

    def make_icon():
        # 优先加载app_logo.png，fallback到绘制
        logo_path = get_data_path("app_logo.png")
        if os.path.exists(logo_path):
            return Image.open(logo_path).resize((64, 64), Image.LANCZOS)
        # fallback: 绘制蓝色圆形+白色D
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
        def open_settings():
            if app._opening_settings:
                return
            if app._settings_win and app._settings_win.winfo_exists():
                app._settings_win.lift()
                app._settings_win.focus_force()
                return
            app._opening_settings = True
            app._settings_win = SettingsWindow(app, app.cfg, app._on_settings_save)
            app._opening_settings = False
        app.after(0, open_settings)

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
    """显示更新检查结果，确认后打开浏览器跳转到 Release 页面"""
    import webbrowser
    if result is None:
        if not silent:
            messagebox.showinfo("检查更新", f"当前已是最新版本 ({APP_VERSION})")
        return

    latest_tag, release_url, body = result
    # 截取 changelog 前几行
    lines = [l for l in body.strip().splitlines() if l.strip()]
    summary = "\n".join(lines[:10])
    if len(lines) > 10:
        summary += "\n..."

    msg = f"发现新版本 {latest_tag}（当前 {APP_VERSION}）\n\n{summary}\n\n是否打开下载页面？"
    if messagebox.askyesno("发现更新", msg):
        webbrowser.open(release_url)


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
        def open_first_settings():
            app._settings_win = SettingsWindow(app, app.cfg, on_settings_save)
        app.after(1000, open_first_settings)

    # 启动后静默检查更新
    app.after(3000, lambda: _do_update_check(app, silent=True))

    app.mainloop()


if __name__ == "__main__":
    main()
