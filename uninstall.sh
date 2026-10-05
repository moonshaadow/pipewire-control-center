#!/bin/bash
# PipeWire Control Center - Local uninstallation script
set -e

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== PipeWire Control Center - Uninstallation ===${NC}"

# Files to remove
rm -f "$HOME/.local/bin/pipewire-control-center"
rm -f "$HOME/.local/share/applications/pipewire-control-center.desktop"
rm -rf "$HOME/.local/share/pipewire-control-center"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/pipewire-control-center.png"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/pipewire-control-center.svg"

# Icon cache update
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo -e "${GREEN}=== Uninstallation complete ===${NC}"