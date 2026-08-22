#!/usr/bin/env python3
"""Fenêtre principale avec navigation par boutons"""
import os, re, locale
from PyQt6.QtWidgets import (
    QMainWindow, QStatusBar, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QButtonGroup
)
from PyQt6.QtGui import QPalette, QIcon

from pipewire_manager import PipeWireManager
from config_manager import ConfigManager
from .audio_tab import AudioTab
from .buffer_tab import BufferTab
from .devices_tab import DevicesTab
from .profiles_tab import ProfilesTab
from .status_tab import StatusTab
from .frequency_tab import FrequencyTab
from .aes67_tab import Aes67Tab

# --- Couleurs ---
def _hex_to_rgb(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) if len(h.lstrip('#')) == 6 else None
def _darken(h, f=0.85): return f"#{''.join(f'{min(255, int(c*f)):02x}' for c in _hex_to_rgb(h))}" if _hex_to_rgb(h) else h
def _lighten(h, f=1.15): return f"#{''.join(f'{min(255, int(c*f)):02x}' for c in _hex_to_rgb(h))}" if _hex_to_rgb(h) else h
def _is_dark(h): return (lambda r, g, b: 0.299*r + 0.587*g + 0.114*b < 128)(*_hex_to_rgb(h)) if _hex_to_rgb(h) else True

def _get_gtk_bg():
    for path in [os.path.expanduser('~/.config/gtk-3.0/gtk.css')]:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    m = re.search(r'@define-color\s+theme_bg_color\s+(#[0-9a-fA-F]{6})', line)
                    if m: return m.group(1)
    try:
        theme = os.popen('gsettings get org.cinnamon.desktop.interface gtk-theme 2>/dev/null').read().strip().strip("'")
        for prefix in ['/usr/share/themes', os.path.expanduser('~/.themes')]:
            css = os.path.join(prefix, theme, 'gtk-3.0', 'gtk.css')
            if os.path.exists(css):
                with open(css) as f:
                    for line in f:
                        m = re.search(r'@define-color\s+theme_bg_color\s+(#[0-9a-fA-F]{6})', line)
                        if m: return m.group(1)
    except: pass
    return None

# --- i18n ---
def get_lang():
    lang = os.environ.get('LANG', '') or locale.getdefaultlocale()[0] or 'en'
    return lang.split('_')[0] if '_' in lang else lang

T = {
    'fr': {'output': 'Audio', 'frequencies': 'Fréquences', 'buffer': 'Buffer',
           'devices': 'Périphériques', 'profiles': 'Profils', 'status': 'État',
           'aes67': 'AES67', 'title': 'PipeWire Control Center',
           'ready': 'PipeWire {} - Prêt', 'profile_loaded': 'Profil chargé avec succès'},
    'en': {'output': 'Audio', 'frequencies': 'Frequencies', 'buffer': 'Buffer',
           'devices': 'Devices', 'profiles': 'Profiles', 'status': 'Status',
           'aes67': 'AES67', 'title': 'PipeWire Control Center',
           'ready': 'PipeWire {} - Ready', 'profile_loaded': 'Profile loaded successfully'}
}
def tr(key, lang=None): return T.get(lang or get_lang(), T['en']).get(key, key)

# --- Fenêtre ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pw = PipeWireManager()
        self.config_mgr = ConfigManager()
        self.lang = get_lang()
        
        self.setWindowTitle(tr('title', self.lang))
        self.setMinimumSize(700, 500)
        
        bg = _get_gtk_bg() or self.palette().color(QPalette.ColorRole.Window).name()
        dark = _is_dark(bg)
        
        if dark:
            titlebar_bg, btn_bg, btn_checked, btn_hover = _darken(bg, 0.75), bg, _darken(bg, 0.55), _lighten(bg, 1.15)
            btn_text, btn_text_checked, btn_text_hover = "#999", "#fff", "#ddd"
        else:
            titlebar_bg, btn_bg, btn_checked, btn_hover = _darken(bg, 0.85), bg, _darken(bg, 0.7), _lighten(bg, 1.05)
            btn_text, btn_text_checked, btn_text_hover = "#666", "#000", "#333"
        
        central = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        nav = QWidget()
        nav.setStyleSheet(f"background-color: {titlebar_bg};")
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 4, 0, 4)
        nav_layout.setSpacing(1)
        nav_layout.addStretch()
        
        self.btn_group = QButtonGroup()
        self.btn_group.setExclusive(True)
        self.buttons = []
        
        keys = ['output', 'frequencies', 'buffer', 'devices', 'profiles', 'aes67', 'status']
        pages = [(tr(k, self.lang), i) for i, k in enumerate(keys)]
        btn_style = f"QPushButton {{ background-color: {btn_bg}; color: {btn_text}; border: 1px solid {titlebar_bg}; border-radius: 4px; padding: 8px 18px; font-size: 13px; }} QPushButton:checked {{ background-color: {btn_checked}; color: {btn_text_checked}; border-color: {btn_checked}; }} QPushButton:hover:!checked {{ background-color: {btn_hover}; color: {btn_text_hover}; }}"
        
        for text, idx in pages:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(btn_style)
            self.btn_group.addButton(btn, idx)
            nav_layout.addWidget(btn)
            self.buttons.append(btn)
        
        nav_layout.addStretch()
        nav.setLayout(nav_layout)
        layout.addWidget(nav)
        
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout()
        wrapper_layout.setContentsMargins(16, 16, 16, 16)
        
        self.stack = QStackedWidget()
        wrapper_layout.addWidget(self.stack)
        wrapper.setLayout(wrapper_layout)
        layout.addWidget(wrapper, 1)
        
        central.setLayout(layout)
        self.setCentralWidget(central)
        
        self.audio_tab = AudioTab(self.pw)
        self.frequency_tab = FrequencyTab(self.pw)
        self.buffer_tab = BufferTab(self.pw)
        self.devices_tab = DevicesTab(self.pw)
        self.profiles_tab = ProfilesTab(self.pw, self.config_mgr)
        self.aes67_tab = Aes67Tab(self.pw)
        self.status_tab = StatusTab(self.pw)
        
        for tab in [self.audio_tab, self.frequency_tab, self.buffer_tab,
                    self.devices_tab, self.profiles_tab, self.aes67_tab, self.status_tab]:
            self.stack.addWidget(tab)
        
        self.buttons[0].setChecked(True)
        self.btn_group.idClicked.connect(self._on_nav)
        self.profiles_tab.profile_loaded.connect(lambda: (
            self.audio_tab.load_current(), self.buffer_tab.load_current(),
            self.devices_tab.refresh(), self.statusBar().showMessage(tr('profile_loaded', self.lang), 5000)
        ))
        self.statusBar().showMessage(tr('ready', self.lang).format(self.pw.get_version()), 5000)
    
    def _on_nav(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 6: self.status_tab.refresh()
        elif idx == 3: self.devices_tab.refresh()
    
    def closeEvent(self, event):
        self.audio_tab.shutdown()
        self.status_tab.shutdown()
        self.aes67_tab.shutdown()
        event.accept()
