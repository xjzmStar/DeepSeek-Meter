#!/usr/bin/env bash
set -e

# ═══════════════════════════════════════════════════════════
#  DeepSeek-Meter Linux 安装器打包脚本
#  用法: ./build_installer.sh
#  输出: dist/DeepSeek-Meter-Linux-Installer.sh
# ═══════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
INSTALLER="$DIST_DIR/DeepSeek-Meter-Linux-Installer.sh"

echo "🔨 开始打包 DeepSeek-Meter Linux 安装器..."

# 创建 dist 目录
mkdir -p "$DIST_DIR"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# 复制需要打包的文件
echo "📦 收集文件..."
cp -r "$SCRIPT_DIR/src" "$TEMP_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$TEMP_DIR/"
cp "$SCRIPT_DIR/app_logo.png" "$TEMP_DIR/" 2>/dev/null || true

# 创建 ZIP 包
echo "🗜️  创建 ZIP 包..."
cd "$TEMP_DIR"
zip -q -r payload.zip .

# 合并 install.sh + ZIP 数据
echo "🔗 合并安装脚本和 ZIP 数据..."
cat "$SCRIPT_DIR/install.sh" > "$INSTALLER"
cat payload.zip >> "$INSTALLER"

# 设置可执行权限
chmod +x "$INSTALLER"

# 显示结果
SIZE=$(du -h "$INSTALLER" | cut -f1)
echo ""
echo "✅ 打包完成！"
echo "   输出文件: $INSTALLER"
echo "   文件大小: $SIZE"
echo ""
echo "使用方法:"
echo "   sudo ./DeepSeek-Meter-Linux-Installer.sh"
echo ""
