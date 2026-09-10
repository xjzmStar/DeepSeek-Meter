# DeepSeek-Meter

实时监控 DeepSeek API 余额的桌面工具，支持 **Rainmeter 挂件版** 和 **独立应用版** 两种方案。

![platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20%7C%20Linux-blue) ![license](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-orange) ![©](https://img.shields.io/badge/%C2%A9-2026%20%E6%98%9F%E9%99%85%E7%BB%87%E6%A2%A6-green)

## 功能特点

- ⏰ **实时时钟** - 精确到秒的时间显示
- 💰 **余额监控** - 自动查询 DeepSeek API 余额
- 🌙 **峰谷时段** - 自动识别电价峰谷时段
  - 峰段 (9:00-12:00, 14:00-18:00): 显示"梁文峰"
  - 谷段 (其余时间): 显示"梁文谷"
- 🎨 **精美界面** - Rainmeter 皮肤或独立悬浮窗
- 🚀 **开机自启** - 后台静默运行
- 🔄 **自动更新** - 检测 GitHub 新版本自动替换

## 方案选择

| | Rainmeter 版 | 独立应用版 |
|---|---|---|
| 依赖 | Rainmeter + Python | 无需额外依赖（单 exe） |
| 大小 | ~50KB | ~17MB |
| 界面 | Rainmeter 皮肤嵌入桌面 | CustomTkinter 桌面悬浮窗 |
| 托盘 | 无 | 系统托盘图标 + 右键菜单 |
| 跨平台 | 仅 Windows | Windows / Linux |

## 安装

### 方案一：Rainmeter 版

1. 安装 [Rainmeter](https://www.rainmeter.net/) 4.5+ 和 Python 3.10+
2. 将 `rainmeter/` 文件夹复制到 `%USERPROFILE%\Documents\Rainmeter\Skins\`
3. 复制 `@Resources\config.example.json` 为 `config.json`，填入你的 DeepSeek API Key
4. 双击 `启动服务.vbs`
5. 右键 Rainmeter 托盘图标 → 刷新全部 → 勾选 DeepSeek-Meter

### 方案二：独立应用版

#### 方式一：直接运行

1. 安装 Python 3.10+
2. `cd app && pip install -r requirements.txt`
3. `python src/app.py`

#### 方式二：下载 exe

从 [Releases](https://github.com/xjzmStar/DeepSeek-Meter/releases) 页面下载预编译版本，解压即用。

## 常见问题

**Q: 余额显示 NO_KEY**
A: 需要配置 API Key，参考安装步骤中的第 3 步。

**Q: 中文乱码**
A: 项目使用 GBK 编码，确保系统区域设置支持中文。

**Q: Rainmeter 版服务没启动**
A: 检查启动文件夹是否有 `DeepSeek-Meter.vbs`。

## 更新日志

### v2.0.0
- 新增独立应用版（CustomTkinter + PyInstaller）
- 桌面悬浮窗 + 系统托盘 + 明暗主题 + 窗口置顶
- 低余额提醒 + 开机自启动 + 拖拽调大小
- 自动更新 + Linux 版支持

### v1.0.0
- 初始发布：Rainmeter 版
- 实时时钟 + DeepSeek 余额监控 + 峰谷电价时段

## 📄 许可证

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

本项目采用 **CC BY-NC-SA 4.0** (署名-非商业性使用-相同方式共享) 许可证。

**您可以：**
- ✅ 自由查看、使用、修改和分发本项目
- ✅ 创建衍生作品

**但必须：**
- 📌 **署名**：在使用或分发时保留原作者署名（星际织梦）
- 📝 **相同方式共享**：修改后的衍生作品必须使用相同的 CC BY-NC-SA 4.0 许可证

**禁止：**
- ❌ **商业用途**：不得将本项目或其衍生作品用于商业盈利目的

详见 [LICENSE](LICENSE) | [CC BY-NC-SA 4.0 完整条款](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode)
