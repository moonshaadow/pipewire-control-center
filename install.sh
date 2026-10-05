#!/bin/bash
# PipeWire Control Center - Local installation script
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== PipeWire Control Center - Installation ===${NC}"

# Distribution detection
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="$ID"
else
    DISTRO="unknown"
fi

echo "Detected distribution: $DISTRO"

# System dependencies check
echo -e "\n${GREEN}Checking dependencies...${NC}"

MISSING=""
for cmd in pw-dump pw-metadata wpctl pipewire rsync; do
    if ! command -v $cmd &>/dev/null; then
        MISSING="$MISSING $cmd"
    fi
done

if [ -n "$MISSING" ]; then
    echo -e "${RED}Missing tools:$MISSING${NC}"
    echo "Install the required packages:"
    case "$DISTRO" in
        linuxmint|ubuntu|debian)
            echo "  sudo apt install pipewire wireplumber rsync"
            ;;
        fedora)
            echo "  sudo dnf install pipewire wireplumber rsync"
            ;;
        arch|manjaro)
            echo "  sudo pacman -S pipewire wireplumber rsync"
            ;;
        *)
            echo "  Install pipewire, wireplumber and rsync with your package manager"
            ;;
    esac
    exit 1
fi

# PyQt6 check
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo -e "${RED}PyQt6 not found.${NC}"
    echo "Installing PyQt6..."
    case "$DISTRO" in
        linuxmint|ubuntu|debian)
            sudo apt install -y python3-pyqt6
            ;;
        fedora)
            sudo dnf install -y python3-pyqt6
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm python-pyqt6
            ;;
        *)
            echo "  pip install --user PyQt6"
            pip install --user PyQt6
            ;;
    esac
fi

# Directories
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/share/pipewire-control-center"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

# File copy
echo -e "\n${GREEN}Installing files...${NC}"
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='install.sh' --exclude='uninstall.sh' "$SCRIPT_DIR/" "$INSTALL_DIR/"

# Compile translation files
if command -v lrelease &>/dev/null; then
    echo -e "\n${GREEN}Compiling translations...${NC}"
    for ts in "$INSTALL_DIR"/i18n/*.ts; do
        if [ -f "$ts" ]; then
            lrelease "$ts" 2>/dev/null || true
        fi
    done
fi

# Executable in PATH
cat > "$BIN_DIR/pipewire-control-center" << 'EOF'
#!/bin/bash
cd "$HOME/.local/share/pipewire-control-center"
python3 main.py
EOF
chmod +x "$BIN_DIR/pipewire-control-center"

# Icon
if [ -f "$SCRIPT_DIR/icons/pcc-color.svg" ]; then
    cp "$SCRIPT_DIR/icons/pcc-color.svg" "$ICON_DIR/pipewire-control-center.svg"
    ICON_NAME="pipewire-control-center"
elif [ -f "$SCRIPT_DIR/icons/pcc.svg" ]; then
    cp "$SCRIPT_DIR/icons/pcc.svg" "$ICON_DIR/pipewire-control-center.svg"
    ICON_NAME="pipewire-control-center"
else
    ICON_NAME="audio-card"
    echo -e "${GREEN}Icon not found, using system 'audio-card'.${NC}"
fi

# .desktop file
cat > "$DESKTOP_DIR/pipewire-control-center.desktop" << EOF
[Desktop Entry]
Name=PipeWire Control Center
Comment=Advanced PipeWire configuration
Exec=$BIN_DIR/pipewire-control-center
Icon=$ICON_NAME
Terminal=false
Type=Application
Categories=Audio;Settings;
StartupNotify=true
EOF

# Icon cache update
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

# PATH check
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo -e "\n${GREEN}Add this to your ~/.bashrc:${NC}"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

echo -e "\n${GREEN}=== Installation complete ===${NC}"
echo "Launch 'pipewire-control-center' from the terminal or the Applications menu."