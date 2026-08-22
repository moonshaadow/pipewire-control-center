#!/usr/bin/env python3
"""Utilitaires d'icônes partagés"""
import os

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")

def get_device_icon_path(device: dict) -> str:
    """Retourne le chemin de l'icône appropriée pour un périphérique"""
    name = (device.get('description', '') + ' ' + device.get('name', '')).lower()
    
    if any(w in name for w in ['aes67', 'rtp', 'network', 'stream', 'remote']):
        return os.path.join(ICON_DIR, "network.svg")
    if any(w in name for w in ['hdmi', 'displayport', 'dp', 'nvidia']):
        return os.path.join(ICON_DIR, "hdmi.svg")
    if any(w in name for w in ['usb', 'scarlett', 'focusrite', 'rme', 'motu', 'presonus',
                                 'behringer', 'm-audio', 'steinberg', 'roland', 'yamaha',
                                 'komplete', 'apollo', 'fireface', 'babyface']):
        return os.path.join(ICON_DIR, "usb.svg")
    if any(w in name for w in ['headphone', 'headset', 'casque', 'line-out', 'lineout',
                                 'jack', 'front', 'green']):
        return os.path.join(ICON_DIR, "headphone.svg")
    if device.get('type') == 'entrée':
        return os.path.join(ICON_DIR, "microphone.svg")
    return os.path.join(ICON_DIR, "speaker.svg")
