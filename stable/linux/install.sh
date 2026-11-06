#!/usr/bin/env bash
set -e

# ═══════════════════════════════════════════════════════════
#  DeepSeek-Meter Linux 安装脚本
#  用法: sudo ./install.sh [--uninstall]
# ═══════════════════════════════════════════════════════════

APP_NAME="DeepSeek-Meter"
INSTALL_DIR="/opt/$APP_NAME"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/icons/hicolor/256x256/apps"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检测语言
if [ -z "${LANG##zh_*}" ]; then
    USE_CHINESE=true
else
    USE_CHINESE=false
fi

# 消息函数
msg_info() {
    if [ "$USE_CHINESE" = true ]; then
        echo -e "${BLUE}[信息]${NC} $1"
    else
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

msg_success() {
    if [ "$USE_CHINESE" = true ]; then
        echo -e "${GREEN}[成功]${NC} $1"
    else
        echo -e "${GREEN}[OK]${NC} $1"
    fi
}

msg_warn() {
    if [ "$USE_CHINESE" = true ]; then
        echo -e "${YELLOW}[警告]${NC} $1" >&2
    else
        echo -e "${YELLOW}[WARN]${NC} $1" >&2
    fi
}

msg_error() {
    if [ "$USE_CHINESE" = true ]; then
        echo -e "${RED}[错误]${NC} $1" >&2
    else
        echo -e "${RED}[ERROR]${NC} $1" >&2
    fi
}

# 检查 root 权限
check_root() {
    if [ "$EUID" -ne 0 ]; then
        if [ "$USE_CHINESE" = true ]; then
            msg_error "请使用 sudo 运行此脚本: sudo ./install.sh"
        else
            msg_error "Please run with sudo: sudo ./install.sh"
        fi
        exit 1
    fi
}

# 检测包管理器
detect_package_manager() {
    if command -v apt-get &> /dev/null; then
        PKG_MGR="apt"
    elif command -v dnf &> /dev/null; then
        PKG_MGR="dnf"
    elif command -v yum &> /dev/null; then
        PKG_MGR="yum"
    elif command -v pacman &> /dev/null; then
        PKG_MGR="pacman"
    elif command -v zypper &> /dev/null; then
        PKG_MGR="zypper"
    else
        PKG_MGR="unknown"
    fi
}

# 安装系统依赖
install_dependencies() {
    msg_info "正在安装系统依赖..."
    
    case "$PKG_MGR" in
        apt)
            apt-get update -qq
            apt-get install -y -qq python3 python3-venv python3-tk xdotool x11-utils
            ;;
        dnf)
            dnf install -y python3 python3-tkinter xdotool xorg-x11-utils
            ;;
        yum)
            yum install -y python3 python3-tkinter xdotool xorg-x11-utils
            ;;
        pacman)
            pacman -S --noconfirm python tk xdotool xorg-xprop
            ;;
        zypper)
            zypper install -y python3 python3-tk xdotool xorg-x11-utils
            ;;
        *)
            msg_warn "无法自动安装依赖，请手动安装: python3, python3-tk, xdotool, x11-utils"
            ;;
    esac
    
    msg_success "系统依赖安装完成"
}

# 解压源码
extract_source() {
    msg_info "正在解压源码到 $INSTALL_DIR ..."
    
    mkdir -p "$INSTALL_DIR"
    
    # 获取脚本自身路径
    SCRIPT_PATH="${BASH_SOURCE[0]}"
    
    # 找到 ZIP 数据的起始位置（PK 标记）
    ZIP_START=$(grep -aobm1 "PK" "$SCRIPT_PATH" | cut -d: -f1)
    
    if [ -z "$ZIP_START" ]; then
        msg_error "找不到嵌入的 ZIP 数据"
        exit 1
    fi
    
    # 解压 ZIP 数据
    tail -c +$((ZIP_START + 1)) "$SCRIPT_PATH" > /tmp/deepseek-meter-payload.zip
    unzip -q -o /tmp/deepseek-meter-payload.zip -d "$INSTALL_DIR"
    rm -f /tmp/deepseek-meter-payload.zip
    
    msg_success "源码解压完成"
}

# 创建虚拟环境并安装 Python 依赖
setup_venv() {
    msg_info "正在创建虚拟环境..."
    
    cd "$INSTALL_DIR"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    
    msg_success "Python 依赖安装完成"
}

# 创建启动脚本
create_launcher() {
    msg_info "正在创建启动脚本..."
    
    cat > "$BIN_DIR/deepseek-meter" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source .venv/bin/activate
python3 src/app_linux_stable.py "\$@"
EOF
    
    chmod +x "$BIN_DIR/deepseek-meter"
    
    msg_success "启动脚本创建完成: $BIN_DIR/deepseek-meter"
}

# 创建桌面快捷方式
create_desktop_entry() {
    msg_info "正在创建桌面快捷方式..."
    
    # 复制图标
    if [ -f "$INSTALL_DIR/app_logo.png" ]; then
        mkdir -p "$ICON_DIR"
        cp "$INSTALL_DIR/app_logo.png" "$ICON_DIR/deepseek-meter.png"
    fi
    
    # 创建 .desktop 文件
    cat > "$DESKTOP_DIR/deepseek-meter.desktop" << EOF
[Desktop Entry]
Type=Application
Name=DeepSeek-Meter
Name[zh_CN]=DeepSeek 余额监控
Comment=Monitor DeepSeek API balance
Comment[zh_CN]=监控 DeepSeek API 余额
Exec=$BIN_DIR/deepseek-meter
Icon=deepseek-meter
Terminal=false
Categories=Utility;Monitor;
Keywords=deepseek;balance;monitor;api;
EOF
    
    chmod +x "$DESKTOP_DIR/deepseek-meter.desktop"
    
    # 更新桌面数据库
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi
    
    msg_success "桌面快捷方式创建完成"
}

# 卸载
uninstall() {
    check_root
    
    msg_info "正在卸载 $APP_NAME ..."
    
    rm -rf "$INSTALL_DIR"
    rm -f "$BIN_DIR/deepseek-meter"
    rm -f "$DESKTOP_DIR/deepseek-meter.desktop"
    rm -f "$ICON_DIR/deepseek-meter.png"
    
    # 更新桌面数据库
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi
    
    msg_success "卸载完成"
    exit 0
}

# 安装
install() {
    check_root
    detect_package_manager
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  DeepSeek-Meter Linux 安装程序"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    install_dependencies
    extract_source
    setup_venv
    create_launcher
    create_desktop_entry
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    msg_success "安装完成！"
    echo ""
    echo "  启动方式："
    echo "    1. 终端运行: deepseek-meter"
    echo "    2. 应用菜单搜索: DeepSeek-Meter"
    echo ""
    echo "  卸载方式："
    echo "    sudo $0 --uninstall"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
}

# 主入口
case "$1" in
    --uninstall|-u)
        uninstall
        ;;
    --help|-h)
        echo "用法: sudo $0 [选项]"
        echo ""
        echo "选项:"
        echo "  (无)          安装 DeepSeek-Meter"
        echo "  --uninstall   卸载 DeepSeek-Meter"
        echo "  --help        显示此帮助信息"
        ;;
    *)
        install
        ;;
esac

# ═══════════════════════════════════════════════════════════
#  以下是嵌入的 ZIP 数据（源码包）
# ═══════════════════════════════════════════════════════════
