#!/bin/bash
# DeepSeek-Meter Linux 启动脚本
# 用法: ./run.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 DeepSeek-Meter Linux 版启动中...${NC}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到 python3，请先安装 Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Python 版本: ${PYTHON_VERSION}"

# 检查/创建虚拟环境
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}📦 首次运行，创建虚拟环境...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 检查/安装依赖
if [ ! -f "$VENV_DIR/.deps_installed" ]; then
    echo -e "${YELLOW}📦 安装依赖...${NC}"
    pip install -q --upgrade pip
    pip install -q -r "$SCRIPT_DIR/requirements.txt"
    
    # 检查并安装 python3-tk（系统级依赖）
    if ! python3 -c "import tkinter" 2>/dev/null; then
        echo -e "${YELLOW}📦 安装 tkinter 支持...${NC}"
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y -qq python3-tk
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3-tkinter
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-tkinter
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm tk
        else
            echo -e "${RED}⚠️  无法自动安装 tkinter，请手动安装 python3-tk${NC}"
        fi
    fi
    
    # 检查并安装 xdotool 和 x11-utils（用于窗口置顶）
    if ! command -v xdotool &> /dev/null || ! command -v xprop &> /dev/null; then
        echo -e "${YELLOW}📦 安装窗口管理工具...${NC}"
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y -qq xdotool x11-utils
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y xdotool xorg-x11-utils
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm xdotool xorg-xprop
        fi
    fi
    
    touch "$VENV_DIR/.deps_installed"
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
fi

# 创建配置目录
CONFIG_DIR="$HOME/.config/DeepSeek-Meter"
mkdir -p "$CONFIG_DIR"

# 启动应用
echo -e "${GREEN}▶️  启动 DeepSeek-Meter...${NC}"
cd "$SRC_DIR"
python3 app_linux_stable.py
