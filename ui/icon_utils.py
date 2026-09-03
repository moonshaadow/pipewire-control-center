#!/usr/bin/env python3
"""Utilitaires d'icônes partagés"""
import os

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
ICON_DIR_LIGHT = os.path.join(ICON_DIR, "light")
ICON_DIR_DARK = os.path.join(ICON_DIR, "dark")


def _is_dark_theme(theme_colors):
    """Détermine si le thème est sombre à partir de la couleur de fond"""
    if not theme_colors:
        return True  # Par défaut, thème sombre
    
    bg = theme_colors.get('window_bg', '#2a2a2a')
    if bg.startswith('#'):
        try:
            r = int(bg[1:3], 16)
            g = int(bg[3:5], 16)
            b = int(bg[5:7], 16)
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return luminance < 128
        except Exception:
            pass
    
    return True


def get_device_icon_path(device: dict, theme_colors=None) -> str:
    """Retourne le chemin de l'icône appropriée pour un périphérique"""
    name = (device.get('description', '') + ' ' + device.get('name', '')).lower()
    
    # Déterminer le nom de l'icône
    if any(w in name for w in ['aes67', 'rtp', 'network', 'stream', 'remote']):
        icon_name = "network"
    elif any(w in name for w in ['hdmi', 'displayport', 'dp', 'nvidia']):
        icon_name = "hdmi"
    elif any(w in name for w in ['usb', 'scarlett', 'focusrite', 'rme', 'motu', 'presonus',
                                 'behringer', 'm-audio', 'steinberg', 'roland', 'yamaha',
                                 'komplete', 'apollo', 'fireface', 'babyface']):
        icon_name = "usb"
    elif any(w in name for w in ['headphone', 'headset', 'casque', 'line-out', 'lineout',
                                 'jack', 'front', 'green']):
        icon_name = "headphone"
    elif device.get('type') == 'entrée':
        icon_name = "microphone"
    else:
        icon_name = "speaker"
    
    # Choisir le bon dossier selon le thème
    icon_dir = ICON_DIR_DARK if _is_dark_theme(theme_colors) else ICON_DIR_LIGHT
    
    # Chercher l'icône dans le dossier approprié
    icon_path = os.path.join(icon_dir, f"{icon_name}.svg")
    
    # Fallback : utiliser le dossier principal
    if not os.path.exists(icon_path):
        icon_path = os.path.join(ICON_DIR, f"{icon_name}.svg")
    
    return icon_path
