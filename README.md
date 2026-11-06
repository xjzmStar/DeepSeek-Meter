# DeepSeek-Meter

实时监控 DeepSeek API 余额的桌面工具，支持 **Rainmeter 挂件版** 和 **独立应用版** 两种方案。

## 三个版本

| 版本 | 平台 | 目录 | 说明 |
|---|---|---|---|
| **Rainmeter 版** | Windows | `rainmeter/` | 基于 Rainmeter 的桌面挂件 |
| **独立应用版 (Windows)** | Windows | `app/win/` 或 `stable/win/` | CustomTkinter 桌面悬浮窗，打包为 exe |
| **独立应用版 (Linux)** | Linux | `app/linux/` 或 `stable/linux/` | CustomTkinter 桌面悬浮窗，Python 脚本运行 |

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

## 方案二：独立应用版 - Windows（`app/win/` 或 `stable/win/`）

基于 CustomTkinter 的独立桌面应用，打包为单个 .exe，无需 Rainmeter。

### 功能

- 桌面悬浮窗：实时时钟 + DeepSeek 余额 + 峰谷时段
- 系统托盘图标：右键菜单（显示/设置/检查更新/退出）
- 明暗主题切换（dark / light / 跟随系统）
- 窗口置顶可选
- 低余额提醒（弹窗 + 系统通知）
- 开机自启动
- 拖拽调窗口大小
- **自动更新**：启动时静默检查 GitHub 新版本，发现新版自动下载替换

### 安装

从 [Releases](https://github.com/xjzmStar/DeepSeek-Meter/releases) 页面下载 `DeepSeek-Meter.exe`，双击运行即可。

### 文件说明

| 文件 | 说明 |
|---|---|
| `src/app_dev.py` | 测试版主程序 |
| `src/app_stable.py` | 正式版主程序 |
| `requirements.txt` | Python 依赖 |

## 方案三：独立应用版 - Linux（`app/linux/` 或 `stable/linux/`）

基于 CustomTkinter 的独立桌面应用，使用 Python 脚本运行。

### 功能

- 桌面悬浮窗：实时时钟 + DeepSeek 余额 + 峰谷时段
- 系统托盘图标：右键菜单（显示/设置/检查更新/退出）
- 明暗主题切换（dark / light / 跟随系统）
- 窗口置顶可选（使用 xprop 强制设置）
- 低余额提醒（弹窗 + 系统通知）
- 开机自启动（.desktop 文件）
- 拖拽调窗口大小

### 安装

1. 从 [Releases](https://github.com/xjzmStar/DeepSeek-Meter/releases) 页面下载 `DeepSeek-Meter-Linux-Installer.sh`
2. 运行安装命令：
   ```bash
   sudo chmod +x DeepSeek-Meter-Linux-Installer.sh
   sudo ./DeepSeek-Meter-Linux-Installer.sh
   ```
3. 安装完成后，可以通过以下方式启动：
   - 终端运行：`deepseek-meter`
   - 应用菜单搜索：DeepSeek-Meter

### 卸载

```bash
sudo ./DeepSeek-Meter-Linux-Installer.sh --uninstall
```

### 安装器特性

- ✅ 自动检测包管理器（apt/dnf/yum/pacman/zypper）
- ✅ 自动安装系统依赖（python3-tk、xdotool、x11-utils）
- ✅ 自动创建虚拟环境并安装 Python 依赖
- ✅ 自动创建桌面快捷方式和启动命令
- ✅ 支持中英文界面
- ✅ 支持卸载

### 文件说明

| 文件 | 说明 |
|---|---|
| `install.sh` | 安装脚本（自包含，附带源码） |
| `build_installer.sh` | 打包脚本（开发用） |
| `src/app_linux_dev.py` | 测试版主程序 |
| `src/app_linux_stable.py` | 正式版主程序 |
| `requirements.txt` | Python 依赖 |

## 更新日志

### v3.0.0 (测试版)
> ⚠️ **目前该版本为测试状态，出现任何问题请立即关闭程序进程并在GitHub提交issue**

- **挂件模式**（核心功能）
  - 无标题栏、半透明显示（30%~100% 可调）
  - 四角定位（左上/右上/左下/右下）
  - 鼠标穿透（可选）
  - 双击挂件回到窗口模式
  - 挂件字体颜色自定义（时间/日期分别选色）

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
