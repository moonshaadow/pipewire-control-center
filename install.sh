#!/bin/bash
# PipeWire Control Center - Script d'installation locale
set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== PipeWire Control Center - Installation ===${NC}"

# Détection de la distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="$ID"
else
    DISTRO="unknown"
fi

echo "Distribution détectée : $DISTRO"

# Vérification des dépendances système
echo -e "\n${GREEN}Vérification des dépendances...${NC}"

MISSING=""
for cmd in pw-dump pw-metadata wpctl pipewire rsync; do
    if ! command -v $cmd &>/dev/null; then
        MISSING="$MISSING $cmd"
    fi
done

if [ -n "$MISSING" ]; then
    echo -e "${RED}Outils manquants :$MISSING${NC}"
    echo "Installez les paquets nécessaires :"
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
            echo "  Installez pipewire, wireplumber et rsync avec votre gestionnaire de paquets"
            ;;
    esac
    exit 1
fi

# Vérification PyQt6
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo -e "${RED}PyQt6 non trouvé.${NC}"
    echo "Installation de PyQt6..."
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

# Répertoires
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/share/pipewire-control-center"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

# Copie des fichiers
echo -e "\n${GREEN}Installation des fichiers...${NC}"
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='install.sh' --exclude='uninstall.sh' "$SCRIPT_DIR/" "$INSTALL_DIR/"

# Exécutable dans le PATH
cat > "$BIN_DIR/pipewire-control-center" << 'EOF'
#!/bin/bash
cd "$HOME/.local/share/pipewire-control-center"
python3 main.py
EOF
chmod +x "$BIN_DIR/pipewire-control-center"

# Icône
if [ -f "$SCRIPT_DIR/icons/pcc-color.svg" ]; then
    cp "$SCRIPT_DIR/icons/pcc-color.svg" "$ICON_DIR/pipewire-control-center.svg"
    ICON_NAME="pipewire-control-center"
elif [ -f "$SCRIPT_DIR/icons/pcc.svg" ]; then
    cp "$SCRIPT_DIR/icons/pcc.svg" "$ICON_DIR/pipewire-control-center.svg"
    ICON_NAME="pipewire-control-center"
else
    ICON_NAME="audio-card"
    echo -e "${GREEN}Icône non trouvée, utilisation de 'audio-card' du système.${NC}"
fi

# Fichier .desktop
cat > "$DESKTOP_DIR/pipewire-control-center.desktop" << EOF
[Desktop Entry]
Name=PipeWire Control Center
Comment=Configuration avancée de PipeWire
Exec=$BIN_DIR/pipewire-control-center
Icon=$ICON_NAME
Terminal=false
Type=Application
Categories=Audio;Settings;
StartupNotify=true
EOF

# Mise à jour du cache d'icônes
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

# Vérification du PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo -e "\n${GREEN}Ajoutez ceci à votre ~/.bashrc :${NC}"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

echo -e "\n${GREEN}=== Installation terminée ===${NC}"
echo "Lancez 'pipewire-control-center' depuis le terminal ou via le menu Applications."
