# DeepSeek-Meter 开发流程

## 目录结构

```
DeepSeekMonitor/
├── app/          # 测试版（snapshots）— 日常开发在这里
├── stable/       # 正式版 — 只有发布时才从 app/ 复制过来
├── rainmeter/    # Rainmeter 版（旧版，维护模式）
└── .github/      # CI/CD
```

## 开发规则

### 1. 日常开发（测试版）
- 所有新功能、bug 修复、实验性改动 → **只改 `app/`**
- `stable/` 里的代码 **绝对不动**，除非收到明确的「发布正式版」指令
- 版本号格式：`v3.0.0-snapshots-N`（预览版，CI 自动标为 Pre-release）

### 2. 发布正式版
- 用户说「发布正式版」时：
  1. 将 `app/` 的代码复制到 `stable/`
  2. 更新 `stable/` 中的版本号
  3. 提交、打 tag（如 `v2.1.3`），CI 自动标为 Latest
  4. tag 不能包含空格、不能含 snapshots/alpha/beta/rc 等关键词

### 3. 自用版本
- 本地运行的 exe **永远保持最新版**（测试版或正式版）
- 每次构建后杀进程重启，确保用户用的是最新代码

### 4. Tag 规范
- `vX.Y.Z` → Latest（正式版）
- `vX.Y.Z-snapshots-N` → Pre-release（测试版）
- CI 自动根据 tag 名判断是否为 Pre-release

### 5. CHANGELOG 规范
- 每个版本都要在 `CHANGELOG.md` 中添加条目
- 格式：`## vX.Y.Z (YYYY-MM-DD)` + 分类（新增/变更/修复）
- CHANGELOG 版本号必须与 tag 一致（短横线连接）
