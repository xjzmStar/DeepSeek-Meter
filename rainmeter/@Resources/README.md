# @Resources

这个目录包含 DeepSeek-Meter 的核心资源文件。

## 文件说明

| 文件 | 说明 |
|------|------|
| `time.lua` | Rainmeter Lua 脚本，负责显示时间、日期、中文文本 |
| `update_state.py` | 核心状态更新脚本，每秒更新时间，每分钟查询余额 |
| `launcher.py` | 无窗口启动器，用于后台静默运行 |
| `fetch_balance.py` | 独立的余额查询脚本（备用） |
| `config.example.json` | 配置文件模板 |
| `config.json` | 实际配置文件（已加入 .gitignore） |

## 配置

复制 `config.example.json` 为 `config.json`，然后填入你的 DeepSeek API Key：

```json
{
    "api_key": "sk-your-api-key-here"
}
```

## 注意事项

- `config.json` 包含你的 API Key，已加入 .gitignore，不要提交到 Git
- `state.txt` 和 `balance.txt` 是运行时生成的文件，也不要提交