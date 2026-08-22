#!/bin/bash
# PipeWire Control Center - Script de désinstallation locale
set -e

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== PipeWire Control Center - Désinstallation ===${NC}"

# Fichiers à supprimer
rm -f "$HOME/.local/bin/pipewire-control-center"
rm -f "$HOME/.local/share/applications/pipewire-control-center.desktop"
rm -rf "$HOME/.local/share/pipewire-control-center"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/pipewire-control-center.png"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/pipewire-control-center.svg"

# Mise à jour du cache d'icônes
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo -e "${GREEN}=== Désinstallation terminée ===${NC}"
