# DeepSeek-Meter

实时监控 DeepSeek API 余额的桌面工具，支持 **Rainmeter 挂件版** 和 **独立应用版** 两种方案。

## 两种方案对比

| | Rainmeter 版 | 独立应用版 |
|---|---|---|
| 依赖 | Rainmeter + Python | 无需额外依赖（单 exe） |
| 大小 | ~50KB | ~17MB |
| 界面 | Rainmeter 皮肤嵌入桌面 | CustomTkinter 桌面悬浮窗 |
| 托盘 | 无 | 系统托盘图标 + 右键菜单 |
| 跨平台 | 仅 Windows | Windows / Linux |
| 自动更新 | 否 | ✅ 检测 GitHub 新版本自动更新 |

## 方案一：Rainmeter 版（`rainmeter/`）

基于 Rainmeter 的桌面挂件，显示实时时钟 + DeepSeek 余额 + 峰谷电价时段。

### 安装

1. 安装 [Rainmeter](https://www.rainmeter.net/) 4.5+ 和 Python 3.10+
2. 将 `rainmeter/` 文件夹复制到 `%USERPROFILE%\Documents\Rainmeter\Skins\`
3. 复制 `@Resources\config.example.json` 为 `config.json`，填入你的 DeepSeek API Key
4. 双击 `启动服务.vbs`
5. 右键 Rainmeter 托盘图标 → 刷新全部 → 勾选 DeepSeek-Meter

### 文件说明

| 文件 | 说明 |
|---|---|
| `启动服务.vbs` | 启动后台服务（无窗口） |
| `重启服务.vbs` | 重启服务 |
| `停止服务.bat` | 停止服务 |
| `@Resources/config.json` | API Key 配置 |
| `@Resources/update_state.py` | 核心：时间 + 余额 + 峰谷判断 |

### 常见问题

- **余额显示 NO_KEY** → 检查 `config.json` 是否配置
- **中文乱码** → 项目使用 GBK 编码，确保系统支持中文
- **服务没启动** → 检查启动文件夹是否有 `DeepSeek-Meter.vbs`

## 方案二：独立应用版（`app/`）

基于 CustomTkinter 的独立桌面应用，打包为单个 .exe，无需 Rainmeter。

### 功能

- 桌面悬浮窗：实时时钟 + DeepSeek 余额 + 峰谷时段
- 系统托盘图标：右键菜单（显示/设置/检查更新/退出）
- 明暗主题切换（dark / light / 跟随系统）
- 窗口置顶可选
- 低余额提醒
- 开机自启动
- 拖拽调窗口大小
- **自动更新**：启动时静默检查 GitHub 新版本，发现新版自动下载替换

### 安装（直接运行）

1. 安装 Python 3.10+
2. `cd app && pip install -r requirements.txt`
3. `python src/app.py`

### 安装（打包 exe / binary）

```bash
# Windows
build\build_windows.bat

# Linux
bash build/build_linux.sh
```

生成的文件：
- Windows: `app/dist/DeepSeek-Meter.exe`
- Linux: `app/dist/DeepSeek-Meter`

或直接从 [Releases](https://github.com/xjzmStar/DeepSeek-Meter/releases) 页面下载预编译版本。

### 文件说明

| 文件 | 说明 |
|---|---|
| `src/app.py` | 主程序（UI + 托盘 + API 查询 + 自动更新） |
| `requirements.txt` | Python 依赖 |
| `build/build_windows.bat` | Windows 打包脚本 |
| `build/build_linux.sh` | Linux 打包脚本 |

## 自动构建

每次推送 `v*` tag 时，GitHub Actions 自动构建并发布：

- **Windows**: `DeepSeek-Meter.exe`
- **Linux**: `DeepSeek-Meter`
- **Rainmeter**: `DeepSeek-Meter-Rainmeter.zip`

构建产物自动附加到 GitHub Release，无需手动打包。

## 项目结构

```
DeepSeek-Meter/
├── rainmeter/              # Rainmeter 版
│   ├── DeepSeek-Meter.ini
│   ├── @Resources/
│   │   ├── time.lua
│   │   ├── update_state.py
│   │   ├── launcher.py
│   │   └── config.example.json
│   ├── 启动服务.vbs
│   ├── 重启服务.vbs
│   └── 停止服务.bat
├── app/                    # 独立应用版
│   ├── src/
│   │   └── app.py
│   ├── build/
│   │   ├── build_windows.bat
│   │   └── build_linux.sh
│   └── requirements.txt
├── .github/workflows/      # CI 自动构建
│   └── build.yml
├── README.md
└── LICENSE
```

## 技术栈

- **前端 UI**: Rainmeter (Lua) / CustomTkinter (Python)
- **后端**: Python 3.10+
- **打包**: PyInstaller
- **启动**: VBScript (Rainmeter 版)
- **CI**: GitHub Actions

## 更新日志

### v2.0.0 (2026-08-20)
- 新增独立应用版（CustomTkinter + PyInstaller）
- 桌面悬浮窗 + 系统托盘 + 明暗主题 + 窗口置顶
- 低余额提醒 + 开机自启动 + 拖拽调大小
- 自动更新：启动时静默检查 GitHub 新版本，自动下载替换
- 新增 Linux 版构建支持（GitHub Actions 自动打包）
- GitHub Actions CI：tag 推送时自动构建 Windows / Linux / Rainmeter 三个版本

### v1.0.0 (2026-08-20)
- 初始发布：Rainmeter 版
- 实时时钟 + DeepSeek 余额监控 + 峰谷电价时段
- 后台静默运行 + 开机自启动

## 许可证

MIT License
