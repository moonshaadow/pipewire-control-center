#!/usr/bin/env python3
"""Fenêtre principale avec navigation par boutons"""
import os, re, locale, json
from PyQt6.QtWidgets import (
    QMainWindow, QStatusBar, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QButtonGroup, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox, QCheckBox,
    QLabel, QToolButton, QApplication
)
from PyQt6.QtGui import QPalette, QIcon, QAction, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QSettings

from pipewire_manager import PipeWireManager
from config_manager import ConfigManager
from .audio_tab import AudioTab
from .buffer_tab import BufferTab
from .devices_tab import DevicesTab
from .profiles_tab import ProfilesTab
from .status_tab import StatusTab
from .frequency_tab import FrequencyTab
from .aes67_tab import Aes67Tab
from .i18n import I18n, get_system_lang
from .logger import Logger

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

# --- Configuration UI ---
class UIConfig:
    def __init__(self):
        self.config_file = os.path.expanduser('~/.config/pipewire-control-center/ui-config.json')
        self.default_config = {
            'visible_tabs': {
                'output': True, 'frequencies': True, 'buffer': True,
                'devices': True, 'profiles': True, 'aes67': True, 'status': True
            },
            'language': 'auto',
            'close_behavior': 'tray'
        }
        self.config = self._load()
    
    def _load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    config = self.default_config.copy()
                    if 'visible_tabs' in loaded:
                        config['visible_tabs'].update(loaded['visible_tabs'])
                    if 'language' in loaded:
                        config['language'] = loaded['language']
                    if 'close_behavior' in loaded:
                        config['close_behavior'] = loaded['close_behavior']
                    return config
            except Exception as e:
                self.logger.error(f"Erreur: {e}")
        return self.default_config.copy()
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception:
            return False
    
    def reset(self):
        self.config = self.default_config.copy()
        return self.save()
    
    def get_lang(self):
        if self.config['language'] == 'auto':
            return get_system_lang()
        return self.config['language']
    
    def is_tab_visible(self, tab_key):
        if tab_key == 'output':
            return True
        return self.config['visible_tabs'].get(tab_key, True)

# --- Dialog de configuration ---
class SettingsDialog(QDialog):
    def __init__(self, ui_config, parent=None):
        super().__init__(parent)
        self.ui_config = ui_config
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self.lang = self.i18n.get_lang()
        self.setWindowTitle(self.i18n.tr('settings'))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Langue
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(self.i18n.tr('lang_auto'), 'auto')
        self.lang_combo.addItem(self.i18n.tr('lang_fr'), 'fr')
        self.lang_combo.addItem(self.i18n.tr('lang_en'), 'en')
        current_lang = ui_config.config['language']
        idx = self.lang_combo.findData(current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        form_layout.addRow(self.i18n.tr('language') + ':', self.lang_combo)
        
        # Comportement à la fermeture
        self.close_combo = QComboBox()
        self.close_combo.addItem(self.i18n.tr('close_tray'), 'tray')
        self.close_combo.addItem(self.i18n.tr('close_quit'), 'quit')
        current_close = ui_config.config.get('close_behavior', 'tray')
        idx = self.close_combo.findData(current_close)
        if idx >= 0:
            self.close_combo.setCurrentIndex(idx)
        form_layout.addRow(self.i18n.tr('close_behavior') + ':', self.close_combo)
        
        # Onglets visibles
        tab_keys = [
            ('frequencies', 'Fréquences / Frequencies'),
            ('buffer', 'Buffer'),
            ('devices', 'Périphériques / Devices'),
            ('profiles', 'Profils / Profiles'),
            ('aes67', 'AES67'),
            ('status', 'État / Status')
        ]
        
        self.tab_checkboxes = {}
        tab_group_label = QLabel(self.i18n.tr('show_tabs') + ':')
        form_layout.addRow(tab_group_label)
        
        for key, label in tab_keys:
            cb = QCheckBox(label)
            cb.setChecked(ui_config.config['visible_tabs'].get(key, True))
            self.tab_checkboxes[key] = cb
            form_layout.addRow('', cb)
        
        layout.addLayout(form_layout)
        
        # Boutons
        button_box = QDialogButtonBox()
        save_btn = button_box.addButton(self.i18n.tr('save'), QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = button_box.addButton(self.i18n.tr('cancel'), QDialogButtonBox.ButtonRole.RejectRole)
        reset_btn = button_box.addButton(self.i18n.tr('reset_config'), QDialogButtonBox.ButtonRole.ResetRole)
        
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)
        reset_btn.clicked.connect(self._on_reset)
        
        layout.addWidget(button_box)
    
    def _on_save(self):
        self.ui_config.config['language'] = self.lang_combo.currentData()
        self.ui_config.config['close_behavior'] = self.close_combo.currentData()
        for key, cb in self.tab_checkboxes.items():
            self.ui_config.config['visible_tabs'][key] = cb.isChecked()
        if self.ui_config.save():
            self.accept()
        else:
            QMessageBox.warning(self, 'Erreur', 'Impossible de sauvegarder la configuration')
    
    def _on_reset(self):
        reply = QMessageBox.question(
            self, self.i18n.tr('reset_config'),
            'Voulez-vous vraiment réinitialiser la configuration ?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.ui_config.reset():
                self.lang_combo.setCurrentIndex(self.lang_combo.findData('auto'))
                self.close_combo.setCurrentIndex(self.close_combo.findData('tray'))
                for cb in self.tab_checkboxes.values():
                    cb.setChecked(True)
                QMessageBox.information(self, 'OK', self.i18n.tr('config_reset'))

# --- Fenêtre principale ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pw = PipeWireManager()
        self.config_mgr = ConfigManager()
        self.ui_config = UIConfig()
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self.i18n.set_ui_config(self.ui_config)
        self.lang = self.i18n.get_lang()
        
        self.setWindowTitle(self.i18n.tr('title'))
        self.setMinimumSize(700, 500)
        
        # Style global pour les tooltips
        self.setStyleSheet("""
            QToolTip {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555;
                padding: 4px 8px;
                font-size: 12px;
            }
        """)
        
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
        
        # Barre de navigation
        nav = QWidget()
        nav.setStyleSheet(f"background-color: {titlebar_bg};")
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 4, 0, 4)
        nav_layout.setSpacing(1)
        
        nav_layout.addStretch(1)
        
        self.btn_group = QButtonGroup()
        self.btn_group.setExclusive(True)
        self.buttons = []
        self.button_map = {}
        
        all_tab_keys = ['output', 'frequencies', 'buffer', 'devices', 'profiles', 'aes67', 'status']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        
        btn_style = f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {titlebar_bg};
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 13px;
            }}
            QPushButton:checked {{
                background-color: {btn_checked};
                color: {btn_text_checked};
                border-color: {btn_checked};
            }}
            QPushButton:hover:!checked {{
                background-color: {btn_hover};
                color: {btn_text_hover};
            }}
        """
        
        for idx, key in enumerate(visible_keys):
            btn = QPushButton(self.i18n.tr(key))
            btn.setCheckable(True)
            btn.setStyleSheet(btn_style)
            self.btn_group.addButton(btn, idx)
            nav_layout.addWidget(btn)
            self.buttons.append(btn)
            self.button_map[key] = btn
        
        nav_layout.addStretch(1)
        
        # Bouton de configuration
        settings_btn = QToolButton()
        settings_btn.setText('⋮')
        settings_btn.setToolTip(self.i18n.tr('settings_tooltip'))
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setFixedWidth(28)
        settings_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {btn_text};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 4px 0px;
                margin-right: 12px;
            }}
            QToolButton:hover {{
                color: {btn_text_hover};
            }}
        """)
        settings_btn.clicked.connect(self._open_settings)
        nav_layout.addWidget(settings_btn)
        
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
        
        self.all_tabs = {
            'output': self.audio_tab,
            'frequencies': self.frequency_tab,
            'buffer': self.buffer_tab,
            'devices': self.devices_tab,
            'profiles': self.profiles_tab,
            'aes67': self.aes67_tab,
            'status': self.status_tab
        }
        
        self._rebuild_stack()
        
        self.buttons[0].setChecked(True)
        self.btn_group.idClicked.connect(self._on_nav)
        self.profiles_tab.profile_loaded.connect(lambda: (
            self.audio_tab.load_current(), self.buffer_tab.load_current(),
            self.devices_tab.refresh(), self.statusBar().showMessage(self.i18n.tr('profile_loaded'), 5000)
        ))
        self.statusBar().showMessage(self.i18n.tr('ready').format(self.pw.get_version()), 5000)
        
        # Restaurer la géométrie de la fenêtre
        self._restore_geometry()
        
        # Installer les raccourcis clavier
        self._install_shortcuts()
    
    def _restore_geometry(self):
        """Restaure la taille et la position de la fenêtre"""
        settings = QSettings('PipeWireControlCenter', 'MainWindow')
        geometry = settings.value('geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)
        else:
            self.resize(900, 600)
    
    def _save_geometry(self):
        """Sauvegarde la taille et la position de la fenêtre"""
        settings = QSettings('PipeWireControlCenter', 'MainWindow')
        settings.setValue('geometry', self.saveGeometry())
    
    def _install_shortcuts(self):
        """Installe les raccourcis clavier"""
        # Ctrl+1 à Ctrl+7 : changer d'onglet
        for i in range(1, 8):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda idx=i-1: self._goto_tab(idx))
        
        # Ctrl+R : rafraîchir l'onglet actuel
        refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_shortcut.activated.connect(self._refresh_current_tab)
        
        # F5 : rafraîchir les périphériques
        f5_shortcut = QShortcut(QKeySequence("F5"), self)
        f5_shortcut.activated.connect(self._refresh_all)
        
        # Ctrl+Q : quitter
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self._quit_app)
    
    def _goto_tab(self, idx):
        """Va à l'onglet spécifié par l'index"""
        all_tab_keys = ['output', 'frequencies', 'buffer', 'devices', 'profiles', 'aes67', 'status']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        
        if idx < len(visible_keys):
            self.stack.setCurrentIndex(idx)
            if idx < len(self.buttons):
                self.buttons[idx].setChecked(True)
            key = visible_keys[idx]
            if key == 'status':
                self.status_tab.refresh()
            elif key == 'devices':
                self.devices_tab.refresh()
    
    def _refresh_current_tab(self):
        """Rafraîchit l'onglet actuellement affiché"""
        current_idx = self.stack.currentIndex()
        all_tab_keys = ['output', 'frequencies', 'buffer', 'devices', 'profiles', 'aes67', 'status']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        
        if current_idx < len(visible_keys):
            key = visible_keys[current_idx]
            if key == 'devices':
                self.devices_tab.refresh()
            elif key == 'status':
                self.status_tab.refresh()
            elif key == 'output':
                self.audio_tab.refresh_devices()
            elif key == 'buffer':
                self.buffer_tab.load_current()
            elif key == 'frequencies':
                self.frequency_tab._populate_rates_list()
    
    def _refresh_all(self):
        """Rafraîchit tout"""
        self.audio_tab.refresh_devices()
        self.devices_tab.refresh()
        self.status_tab.refresh()
        self.statusBar().showMessage(self.i18n.tr('rafraichir'), 2000)
    
    def _quit_app(self):
        """Quitte proprement l'application"""
        self._save_geometry()
        self.audio_tab.shutdown()
        self.status_tab.shutdown()
        self.aes67_tab.shutdown()
        QApplication.quit()
    
    def _rebuild_stack(self):
        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
        
        self.stack_tab_indices = {}
        self.tab_map = {}
        
        all_tab_keys = ['output', 'frequencies', 'buffer', 'devices', 'profiles', 'aes67', 'status']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        
        for key in visible_keys:
            idx = self.stack.addWidget(self.all_tabs[key])
            self.stack_tab_indices[key] = idx
            self.tab_map[key] = self.all_tabs[key]
    
    def _on_nav(self, idx):
        self.stack.setCurrentIndex(idx)
        all_tab_keys = ['output', 'frequencies', 'buffer', 'devices', 'profiles', 'aes67', 'status']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        if idx < len(visible_keys):
            key = visible_keys[idx]
            if key == 'status':
                self.status_tab.refresh()
            elif key == 'devices':
                self.devices_tab.refresh()
    
    def _open_settings(self):
        dialog = SettingsDialog(self.ui_config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.i18n.set_lang(self.ui_config.config['language'])
            self.lang = self.i18n.get_lang()
            self.setWindowTitle(self.i18n.tr('title'))
            self.statusBar().showMessage(self.i18n.tr('config_saved'), 3000)
            self._rebuild_navigation()
            self._rebuild_stack()
    
    def _rebuild_navigation(self):
        old_nav = self.centralWidget().layout().itemAt(0).widget()
        if old_nav:
            old_nav.deleteLater()
        
        bg = _get_gtk_bg() or self.palette().color(QPalette.ColorRole.Window).name()
        dark = _is_dark(bg)
        
        if dark:
            titlebar_bg, btn_bg, btn_checked, btn_hover = _darken(bg, 0.75), bg, _darken(bg, 0.55), _lighten(bg, 1.15)
            btn_text, btn_text_checked, btn_text_hover = "#999", "#fff", "#ddd"
        else:
            titlebar_bg, btn_bg, btn_checked, btn_hover = _darken(bg, 0.85), bg, _darken(bg, 0.7), _lighten(bg, 1.05)
            btn_text, btn_text_checked, btn_text_hover = "#666", "#000", "#333"
        
        nav = QWidget()
        nav.setStyleSheet(f"background-color: {titlebar_bg};")
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 4, 0, 4)
        nav_layout.setSpacing(1)
        
        nav_layout.addStretch(1)
        
        self.btn_group = QButtonGroup()
        self.btn_group.setExclusive(True)
        self.buttons = []
        self.button_map = {}
        
        all_tab_keys = ['output', 'frequencies', 'buffer', 'devices', 'profiles', 'aes67', 'status']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        
        btn_style = f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {titlebar_bg};
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 13px;
            }}
            QPushButton:checked {{
                background-color: {btn_checked};
                color: {btn_text_checked};
                border-color: {btn_checked};
            }}
            QPushButton:hover:!checked {{
                background-color: {btn_hover};
                color: {btn_text_hover};
            }}
        """
        
        for idx, key in enumerate(visible_keys):
            btn = QPushButton(self.i18n.tr(key))
            btn.setCheckable(True)
            btn.setStyleSheet(btn_style)
            self.btn_group.addButton(btn, idx)
            nav_layout.addWidget(btn)
            self.buttons.append(btn)
            self.button_map[key] = btn
        
        nav_layout.addStretch(1)
        
        settings_btn = QToolButton()
        settings_btn.setText('⋮')
        settings_btn.setToolTip(self.i18n.tr('settings_tooltip'))
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setFixedWidth(28)
        settings_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {btn_text};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 4px 0px;
                margin-right: 12px;
            }}
            QToolButton:hover {{
                color: {btn_text_hover};
            }}
        """)
        settings_btn.clicked.connect(self._open_settings)
        nav_layout.addWidget(settings_btn)
        
        nav.setLayout(nav_layout)
        
        main_layout = self.centralWidget().layout()
        main_layout.insertWidget(0, nav)
        
        if self.buttons:
            self.buttons[0].setChecked(True)
        self.btn_group.idClicked.connect(self._on_nav)
    
    def closeEvent(self, event):
        # Sauvegarder la géométrie avant de fermer
        self._save_geometry()
        
        behavior = self.ui_config.config.get('close_behavior', 'tray')
        
        if behavior == 'quit':
            self.audio_tab.shutdown()
            self.status_tab.shutdown()
            self.aes67_tab.shutdown()
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
            self.hide()
