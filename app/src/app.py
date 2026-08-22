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
APP_VERSION = "3.0.0-snapshots 1"
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
    # ── 挂件模式 ──
    "display_mode": "window",  # "window" / "widget"
    "widget_opacity": 0.85,  # 挂件透明度 0.0~1.0
    "widget_position": "bottom_right",  # 左上/右上/右下/左下
    "mouse_passthrough": False,  # 鼠标穿透
    "widget_time_color": "#FFFFFF",  # 挂件时间颜色
    "widget_date_color": "#888888",  # 挂件日期颜色
    # ── 快捷键 ──
    "hotkeys": {
        "toggle_visibility": "ctrl+alt+d",
        "open_settings": "ctrl+alt+s",
        "toggle_mode": "ctrl+alt+m",
        "quit": "ctrl+alt+q",
    },
}

# 挂件模式下的透明色（Windows）
WIDGET_TRANSPARENT_COLOR = "#010101"


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
    """检查 GitHub Releases 是否有新版本，返回 (latest_ver, release_url, body) 或 None"""
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
        # 窗口大小根据字号动态计算（12pt 为基准：280×160）
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

        # 恢复窗口位置和大小
        if self.cfg["window_x"] is not None:
            w = self.cfg.get("window_w", 280)
            h = self.cfg.get("window_h", 160)
            self.geometry(f"{w}x{h}+{self.cfg['window_x']}+{self.cfg['window_y']}")

        # 记录窗口位置
        self.bind("<ButtonPress-1>", self._on_drag_start)
        self.bind("<ButtonRelease-1>", self._on_drag_end)
        self.bind("<B1-Motion>", self._on_drag)

        # ── UI ──
        self._build_ui()

        # ── 启动后台线程 ──
        self._clock_after_id = None
        self._update_clock()
        self._start_balance_thread()

        # ── 全局快捷键 ──
        self.setup_hotkeys()

        # ── 如果上次是挂件模式，启动时恢复 ──
        if self.cfg.get("display_mode") == "widget":
            self.after(100, self.switch_to_widget_mode)

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

    # ── 挂件模式 ──────────────────────────────────────────
    def _set_snap(self, enable):
        """启用/禁用 Windows 窗口吸附（Snap）"""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "SnapAssist", 0, winreg.REG_DWORD, 1 if enable else 0)
            # 通知系统设置已变更
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Advanced")
        except Exception:
            pass

    def switch_to_widget_mode(self):
        """切换到挂件模式：无标题栏、半透明、可穿透"""
        self.cfg["display_mode"] = "widget"
        self._save_position()
        # 保存窗口模式下的位置
        self._window_mode_x = self.winfo_x()
        self._window_mode_y = self.winfo_y()

        self.overrideredirect(True)  # 去掉标题栏
        self._set_tool_window()  # 阻止 Windows Snap 吸附
        self._set_snap(False)  # 临时禁用系统 Snap
        opacity = self.cfg.get("widget_opacity", 0.85)
        self.attributes("-alpha", opacity)
        self.attributes("-topmost", True)  # 挂件强制置顶
        # 设置透明背景（Windows）
        try:
            self.configure(fg_color=WIDGET_TRANSPARENT_COLOR)
            self.attributes("-transparentcolor", WIDGET_TRANSPARENT_COLOR)
        except Exception:
            pass
        # 鼠标穿透
        if self.cfg.get("mouse_passthrough", False):
            self._set_click_through(True)
        # 隐藏图钉按钮
        self.pin_btn.pack_forget()
        # 设置挂件位置
        self._place_widget()
        # 绑定双击回到窗口模式
        self.bind("<Double-Button-1>", lambda e: self.switch_to_window_mode())
        # 应用自定义字体颜色
        self._apply_widget_colors()
        # 延迟重新设置工具窗口样式（overrideredirect 后需要等窗口稳定）
        self.after(50, self._set_tool_window)
        save_config(self.cfg)

    def switch_to_window_mode(self):
        """切换回窗口模式"""
        self.cfg["display_mode"] = "window"
        # 恢复系统 Snap
        self._set_snap(True)
        # 取消鼠标穿透
        self._set_click_through(False)
        self.overrideredirect(False)  # 恢复标题栏
        self.attributes("-alpha", 1.0)  # 完全不透明
        try:
            self.attributes("-transparentcolor", "")
        except Exception:
            pass
        self.attributes("-topmost", self.cfg["topmost"])
        # 显式重置背景色（挂件模式的透明色不能留）
        colors = self._get_colors()
        self.configure(fg_color=colors["bg"])
        # 恢复图钉按钮
        self.pin_btn.pack(side="right", padx=4)
        # 恢复之前的位置
        x = getattr(self, '_window_mode_x', None)
        y = getattr(self, '_window_mode_y', None)
        if x is not None and y is not None:
            w = self.cfg.get("window_w", 280)
            h = self.cfg.get("window_h", 160)
            self.geometry(f"{w}x{h}+{x}+{y}")
        # 取消双击绑定
        self.unbind("<Double-Button-1>")
        # 刷新主题确保所有子组件颜色正确
        self._refresh_theme()
        save_config(self.cfg)

    def _place_widget(self):
        """将挂件放到屏幕指定角落"""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = self.winfo_width()
        h = self.winfo_height()
        pos = self.cfg.get("widget_position", "bottom_right")
        margin = 10
        positions = {
            "top_left": (margin, margin),
            "top_right": (sw - w - margin, margin),
            "bottom_left": (margin, sh - h - margin),
            "bottom_right": (sw - w - margin, sh - h - margin),
        }
        x, y = positions.get(pos, positions["bottom_right"])
        self.geometry(f"+{x}+{y}")

    def _set_click_through(self, enable):
        """Windows 设置鼠标穿透"""
        try:
            import ctypes
            hwnd = self.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            if enable:
                style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
            else:
                style &= ~WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        except Exception:
            pass

    def _set_tool_window(self):
        """设置扩展样式 + DWM属性，彻底阻止 Windows Snap 吸附"""
        try:
            import ctypes
            hwnd = self.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_NOINHERITLAYOUT = 0x00100000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_NOINHERITLAYOUT
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # DWM: 禁用非客户区渲染（阻止 Snap 检测边缘吸附）
            try:
                DWMWA_NCRENDERING_POLICY = 2
                DWMNCRP_DISABLED = 2
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_NCRENDERING_POLICY,
                    ctypes.byref(ctypes.c_int(DWMNCRP_DISABLED)),
                    ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass
            # 强制刷新窗口样式
            SWP_FRAMECHANGED = 0x0020
            SWP_NOACTIVATE = 0x0010
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                SWP_FRAMECHANGED | SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
        except Exception:
            pass

    def _apply_widget_colors(self):
        """应用挂件自定义字体颜色"""
        tc = self.cfg.get("widget_time_color", "#FFFFFF")
        dc = self.cfg.get("widget_date_color", "#888888")
        self.time_label.configure(text_color=tc)
        self.date_label.configure(text_color=dc)

    # ── 快捷键 ────────────────────────────────────────────
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
                keyboard.add_hotkey(hk["toggle_mode"], self._hotkey_toggle_mode, suppress=False)
            if hk.get("quit"):
                keyboard.add_hotkey(hk["quit"], self._hotkey_quit, suppress=False)
        except ImportError:
            pass  # keyboard 库未安装，跳过
        except Exception:
            pass  # 快捷键注册失败（可能权限不足），静默跳过

    def _hotkey_toggle_visibility(self):
        """快捷键：显示/隐藏"""
        if self.winfo_viewable():
            self.withdraw()
        else:
            self._on_show()

    def _hotkey_open_settings(self):
        """快捷键：打开设置"""
        self.after(0, self._open_settings)

    def _hotkey_toggle_mode(self):
        """快捷键：切换窗口/挂件模式"""
        self.after(0, self._toggle_display_mode)

    def _hotkey_quit(self):
        """快捷键：退出"""
        self.after(0, self._force_quit)

    def _toggle_display_mode(self):
        """切换显示模式"""
        if self.cfg.get("display_mode") == "window":
            self.switch_to_widget_mode()
        else:
            self.switch_to_window_mode()

    def _open_settings(self):
        """打开设置面板"""
        if self._opening_settings:
            return
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return
        self._opening_settings = True
        self._settings_win = SettingsWindow(self, self.cfg, self._on_settings_save)
        self._opening_settings = False

    def _force_quit(self):
        """强制退出程序"""
        self.running = False
        self._set_snap(True)  # 恢复系统 Snap
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        self.destroy()

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
            text_color=colors["time"],
            fg_color="transparent"
        )
        self.time_label.pack(pady=(4, 0), expand=True)

        # 峰谷 + 金额 同一行
        self.info_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.info_frame.pack(pady=(4, 0), expand=True)

        pv_text, pv_color = get_peak_valley()
        self.pv_label = ctk.CTkLabel(
            self.info_frame, text=pv_text,
            font=make_font(font_preset, font_size, "peak_valley"),
            text_color=pv_color,
            fg_color="transparent"
        )
        self.pv_label.pack(side="left", padx=(0, 12))

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="¥--",
            font=make_font(font_preset, font_size, "balance"),
            text_color="#00C853",
            fg_color="transparent"
        )
        self.balance_label.pack(side="left")

        # 日期
        self.date_label = ctk.CTkLabel(
            self.container, text="",
            font=make_font(font_preset, font_size, "date"),
            text_color=colors["date"],
            fg_color="transparent"
        )
        self.date_label.pack(pady=(6, 0), expand=True)

    def _refresh_theme(self):
        """刷新主题"""
        self.current_theme = resolve_theme(self.cfg["theme"])
        ctk.set_appearance_mode(self.current_theme)
        # 挂件模式下不要重置 fg_color，否则透明背景失效
        if self.cfg.get("display_mode") != "widget":
            colors = self._get_colors()
            self.configure(fg_color=colors["bg"])
        self.time_label.configure(text_color=THEMES[self.current_theme]["time"])
        self.date_label.configure(text_color=THEMES[self.current_theme]["date"])
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
        """拖拽开始"""
        self._dragging = True

    def _on_drag_end(self, event):
        """拖拽结束"""
        self._dragging = False
        self._save_position()

    def _on_drag(self, event):
        """拖拽移动窗口"""
        if not getattr(self, '_dragging', False):
            return
        x = self.winfo_x() + event.x
        y = self.winfo_y() + event.y
        self.geometry(f"+{x}+{y}")

    def _save_position(self, event=None):
        x = self.winfo_x()
        y = self.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        # 防护：窗口尺寸/位置明显异常时不保存（防止 Snap 吸附导致脏数据）
        # 使用虚拟屏幕尺寸（包含所有显示器）而非仅主屏
        try:
            import ctypes
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            vw = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            vh = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        except Exception:
            # fallback: 用主屏 + 余量
            vx, vy = -1920, -1080
            vw = self.winfo_screenwidth() + 3840
            vh = self.winfo_screenheight() + 2160
        if w > vw * 0.8 or h > vh * 0.8:
            return  # 尺寸异常
        if x < vx - 200 or y < vy - 200 or x > vx + vw + 200 or y > vy + vh + 200:
            return  # 位置完全超出虚拟屏幕范围
        self.cfg["window_x"] = x
        self.cfg["window_y"] = y
        self.cfg["window_w"] = w
        self.cfg["window_h"] = h
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
        self.geometry("380x680")
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

        # ── 显示模式 ──
        display_frame = ctk.CTkFrame(self._scroll, fg_color=card_bg)
        display_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(display_frame, text="显示模式",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))

        self.display_mode_var = tk.StringVar(value=self.cfg.get("display_mode", "window"))
        mode_frame = ctk.CTkFrame(display_frame, fg_color="transparent")
        mode_frame.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkRadioButton(mode_frame, text="窗口模式", variable=self.display_mode_var,
                            value="window").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(mode_frame, text="挂件模式", variable=self.display_mode_var,
                            value="widget").pack(side="left")

        # 挂件透明度
        opacity_frame = ctk.CTkFrame(display_frame, fg_color="transparent")
        opacity_frame.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(opacity_frame, text="挂件透明度",
                      font=ctk.CTkFont(size=12)).pack(side="left")
        self.opacity_var = tk.DoubleVar(value=self.cfg.get("widget_opacity", 0.85))
        self.opacity_slider = ctk.CTkSlider(
            opacity_frame, from_=0.3, to=1.0,
            variable=self.opacity_var, width=140,
            command=self._on_opacity_change
        )
        self.opacity_slider.pack(side="right")
        self.opacity_label = ctk.CTkLabel(opacity_frame, text=f"{self.opacity_var.get():.0%}",
                                           font=ctk.CTkFont(size=11), width=40)
        self.opacity_label.pack(side="right", padx=(0, 8))

        # 挂件位置
        pos_frame = ctk.CTkFrame(display_frame, fg_color="transparent")
        pos_frame.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(pos_frame, text="挂件位置",
                      font=ctk.CTkFont(size=12)).pack(side="left")
        self.pos_var = tk.StringVar(value=self.cfg.get("widget_position", "bottom_right"))
        self.pos_menu = ctk.CTkOptionMenu(
            pos_frame, variable=self.pos_var,
            values=["top_left", "top_right", "bottom_left", "bottom_right"],
            width=120
        )
        self.pos_menu.pack(side="right")

        # 鼠标穿透
        self.passthrough_var = tk.BooleanVar(value=self.cfg.get("mouse_passthrough", False))
        ctk.CTkCheckBox(display_frame, text="鼠标穿透（挂件模式下点击穿透到桌面）",
                         variable=self.passthrough_var).pack(anchor="w", padx=12, pady=(0, 8))

        # 挂件字体颜色
        ctk.CTkLabel(display_frame, text="挂件字体颜色",
                      font=ctk.CTkFont(size=12)).pack(anchor="w", padx=12, pady=(4, 2))

        color_row = ctk.CTkFrame(display_frame, fg_color="transparent")
        color_row.pack(fill="x", padx=12, pady=(0, 8))

        # 时间颜色
        ctk.CTkLabel(color_row, text="时间", font=ctk.CTkFont(size=12)).pack(side="left")
        self.time_color_var = tk.StringVar(value=self.cfg.get("widget_time_color", "#FFFFFF"))
        self.time_color_preview = ctk.CTkLabel(color_row, text="  ",
                                                fg_color=self.time_color_var.get(),
                                                width=30, height=20, corner_radius=4)
        self.time_color_preview.pack(side="left", padx=(6, 2))
        ctk.CTkButton(color_row, text="选色", width=50, height=24,
                       font=ctk.CTkFont(size=11),
                       command=lambda: self._pick_color("time")).pack(side="left", padx=(0, 16))

        # 日期颜色
        ctk.CTkLabel(color_row, text="日期", font=ctk.CTkFont(size=12)).pack(side="left")
        self.date_color_var = tk.StringVar(value=self.cfg.get("widget_date_color", "#888888"))
        self.date_color_preview = ctk.CTkLabel(color_row, text="  ",
                                                fg_color=self.date_color_var.get(),
                                                width=30, height=20, corner_radius=4)
        self.date_color_preview.pack(side="left", padx=(6, 2))
        ctk.CTkButton(color_row, text="选色", width=50, height=24,
                       font=ctk.CTkFont(size=11),
                       command=lambda: self._pick_color("date")).pack(side="left")

        # ── 快捷键 ──
        hotkey_frame = ctk.CTkFrame(self._scroll, fg_color=card_bg)
        hotkey_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(hotkey_frame, text="快捷键（全局，后台生效）",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))

        hk = self.cfg.get("hotkeys", {})
        self.hk_entries = {}
        hk_labels = [
            ("toggle_visibility", "显示/隐藏"),
            ("open_settings", "打开设置"),
            ("toggle_mode", "切换窗口/挂件"),
            ("quit", "退出程序"),
        ]
        for key, label in hk_labels:
            row = ctk.CTkFrame(hotkey_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12), width=120, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=140, font=ctk.CTkFont(size=11))
            entry.pack(side="right")
            entry.insert(0, hk.get(key, ""))
            self.hk_entries[key] = entry

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

    def _on_opacity_change(self, value):
        """透明度滑块变化时更新标签"""
        self.opacity_label.configure(text=f"{value:.0%}")

    def _pick_color(self, target):
        """打开颜色选择器"""
        from tkinter import colorchooser
        if target == "time":
            current = self.time_color_var.get()
        else:
            current = self.date_color_var.get()
        color = colorchooser.askcolor(initialcolor=current, title="选择颜色")
        if color and color[1]:
            hex_color = color[1]
            if target == "time":
                self.time_color_var.set(hex_color)
                self.time_color_preview.configure(fg_color=hex_color)
            else:
                self.date_color_var.set(hex_color)
                self.date_color_preview.configure(fg_color=hex_color)

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
        # 显示模式
        self.cfg["display_mode"] = self.display_mode_var.get()
        self.cfg["widget_opacity"] = round(self.opacity_var.get(), 2)
        self.cfg["widget_position"] = self.pos_var.get()
        self.cfg["mouse_passthrough"] = self.passthrough_var.get()
        # 挂件字体颜色
        self.cfg["widget_time_color"] = self.time_color_var.get()
        self.cfg["widget_date_color"] = self.date_color_var.get()
        # 快捷键
        hotkeys = {}
        for key, entry in self.hk_entries.items():
            val = entry.get().strip()
            if val:
                hotkeys[key] = val
        if hotkeys:
            self.cfg["hotkeys"] = hotkeys
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

    def on_toggle_mode(icon, item):
        app.after(0, app._toggle_display_mode)

    icon = pystray.Icon(
        APP_NAME,
        make_icon(),
        APP_NAME,
        menu=pystray.Menu(
            pystray.MenuItem("显示", on_show, default=True),
            pystray.MenuItem("设置", on_settings),
            pystray.MenuItem("切换模式", on_toggle_mode),
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

    latest_tag, release_url, body = result
    # 截取 changelog 前几行
    lines = [l for l in body.strip().splitlines() if l.strip()]
    summary = "\n".join(lines[:10])
    if len(lines) > 10:
        summary += "\n..."

    msg = f"发现新版本 {latest_tag}（当前 {APP_VERSION}）\n\n{summary}\n\n是否打开浏览器前往下载？"
    if messagebox.askyesno("发现更新", msg):
        import webbrowser
        webbrowser.open(release_url)




# ═══════════════════════════════════════════════════════════
#  启动
# ═══════════════════════════════════════════════════════════
def main():
    app = DeepSeekMeter()

    def on_settings_save(new_cfg):
        old_font_size = app.cfg.get("font_size", 12)
        app.cfg = new_cfg
        # 应用置顶（窗口模式下）
        if new_cfg.get("display_mode") == "window":
            app.attributes("-topmost", new_cfg["topmost"])
        # 同步图钉状态
        app.pin_state = new_cfg["topmost"]
        app._update_pin_style()
        # 应用主题（挂件模式下不会碰 fg_color）
        app._refresh_theme()
        # 字号变化时自动调整窗口大小
        new_font_size = new_cfg.get("font_size", 12)
        if new_font_size != old_font_size and new_cfg.get("display_mode") == "window":
            scale = max(0.6, new_font_size / 12)
            new_w = max(220, int(280 * scale))
            new_h = max(120, int(160 * scale))
            x = app.winfo_x()
            y = app.winfo_y()
            app.geometry(f"{new_w}x{new_h}+{x}+{y}")
        # 应用显示模式
        if new_cfg.get("display_mode") == "widget":
            app.switch_to_widget_mode()
        else:
            app.switch_to_window_mode()
        # 重新注册快捷键
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        app.setup_hotkeys()

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
