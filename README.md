# 🌟 DeepSeek-Meter

一个精美的 Rainmeter 桌面挂件，实时监控 DeepSeek API 余额，支持峰谷电价时段显示。

![DeepSeek-Meter](https://img.shields.io/badge/DeepSeek-Meter-v1.0.1-blue) ![Rainmeter](https://img.shields.io/badge/Rainmeter-4.5+-purple) ![Python](https://img.shields.io/badge/Python-3.10+-green)

## ✨ 功能特点

- ⏰ **实时时钟** - 精确到秒的时间显示
- 💰 **余额监控** - 每分钟自动查询 DeepSeek API 余额
- 🌙 **峰谷时段** - 自动识别电价峰谷时段
  - 峰段 (9:00-12:00, 14:00-18:00): 显示"梁文峰"
  - 谷段 (其余时间): 显示"梁文谷"
- 🎨 **精美皮肤** - 蓝天白云渐变背景，中文完美支持
- 🚀 **开机自启** - 后台静默运行，无需手动干预
- 🪶 **轻量级** - 仅需 Python 运行时，无额外依赖

## 📦 安装

### 前置要求

- Windows 10/11
- [Rainmeter](https://www.rainmeter.net/) 4.5+
- Python 3.10+（推荐安装到默认路径）

### 安装步骤

1. **下载**
   前往 [Releases](https://github.com/xjzmStar/DeepSeekMonitor/releases) 页面，下载最新版本的 zip 压缩包。

2. **解压到 Rainmeter 皮肤目录**
   将 zip 中的 `DeepSeek-Meter` 文件夹解压到：
   ```
   %USERPROFILE%\Documents\Rainmeter\Skins\
   ```

3. **配置 API Key**
   打开 `@Resources\config.example.json`，将其另存为 `config.json`，并填入你的 DeepSeek API Key：
   ```json
   {
     "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   }
   ```

4. **启动服务**
   双击 `启动服务.vbs`（服务会随开机自动启动）。

5. **加载皮肤**
   右键点击 Rainmeter 托盘图标 -> 刷新全部 -> 在 "DeepSeek-Meter" 中勾选皮肤。

## 📖 使用方法

### 日常使用

- 服务会随开机自动启动，无需手动干预
- 余额每分钟自动更新一次
- 时间每秒更新

### 手动控制

| 脚本 | 功能 |
|------|------|
| `启动服务.vbs` | 启动后台服务（无窗口） |
| `重启服务.vbs` | 重启服务 |
| `停止服务.bat` | 停止服务 |

### 卸载

1. 停止服务：双击 `停止服务.bat`
2. 删除开机自启动：
   ```bash
   del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DeepSeek-Meter.vbs"
   ```
3. 删除皮肤目录：
   ```bash
   rmdir /s /q "%USERPROFILE%\Documents\Rainmeter\Skins\DeepSeek-Meter"
   ```

## 🔧 技术栈

- **前端**: Rainmeter (Lua 脚本)
- **后端**: Python 3.10+ (纯标准库，无第三方依赖)
- **编码**: GBK (Windows 中文完美支持)
- **启动**: VBScript (无窗口后台运行)

## 📁 项目结构

```
DeepSeek-Meter/
├── DeepSeek-Meter.ini    # Rainmeter 皮肤配置
├── @Resources/           # 资源目录
│   ├── time.lua         # 时间显示脚本
│   ├── update_state.py  # 状态更新脚本（核心）
│   ├── launcher.py      # 无窗口启动器
│   ├── fetch_balance.py # 余额查询（备用）
│   ├── config.example.json  # 配置模板
│   └── README.md        # 资源说明
├── 启动服务.vbs          # 启动脚本
├── 重启服务.vbs          # 重启脚本
├── 停止服务.bat          # 停止脚本
├── .gitignore           # Git 忽略配置
└── README.md            # 项目说明
```

## ❓ 常见问题

### Q: 余额显示 NO_KEY / YERR

A: 需要配置 API Key，参考 [配置 API Key](#配置-api-key) 步骤。

### Q: 中文乱码

A: 项目已使用 GBK 编码，确保系统区域设置支持中文。

### Q: 服务没有自动启动

A: 检查启动文件夹是否存在 `DeepSeek-Meter.vbs`：
```bash
dir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DeepSeek-Meter.vbs"
```

### Q: 如何查看余额查询日志

A: 运行以下命令查看实时输出：
```bash
cd %USERPROFILE%\Documents\Rainmeter\Skins\DeepSeek-Meter\@Resources
py update_state.py
```

## 📋 更新日志

### v1.0.1 (2026-08-20)
- 📝 修复 README 安装步骤：`git clone` 改为从 Releases 页面下载 zip
- 📝 更新仓库地址链接

### v1.0 (2026-08-20)
- 🎉 初始版本发布
- ⏰ 实时时钟显示
- 💰 DeepSeek 余额监控
- 🌙 峰谷时段识别
- 🚀 开机自启动
- 🪶 无窗口后台运行

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [Rainmeter](https://www.rainmeter.net/) - 桌面定制平台
- [DeepSeek](https://www.deepseek.com/) - AI API 服务

---

**Made with ❤️ by 星际织梦**
