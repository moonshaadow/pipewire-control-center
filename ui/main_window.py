#!/usr/bin/env python3
"""Fenêtre principale avec navigation par boutons"""
import os, re, locale, json
from PyQt6.QtWidgets import (
    QMainWindow, QStatusBar, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QButtonGroup, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox, QCheckBox,
    QLabel, QToolButton, QApplication
)
from PyQt6.QtGui import (
    QPalette, QIcon, QAction, QKeySequence, QShortcut, QFont, QColor,
    QPainterPath, QRegion
)
from PyQt6.QtCore import Qt, QSettings, QTimer, QRectF

from pipewire_manager import PipeWireManager
from config_manager import ConfigManager
from .audio.audio_tab import AudioTab
from .settings_tab import SettingsTab
from .routing_tab import RoutingTab
from .profiles_tab import ProfilesTab
from .status_tab import StatusTab
from .aes67_tab import Aes67Tab
from .fx_tab import FXTab
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
                'output': True, 'settings': True,
                'routing': False,
                'profiles': True, 'aes67': True, 'status': True,
                'fx': False
            },
            'language': 'auto',
            'close_behavior': 'tray',
            'experimental_features': False,
            'theme': 'auto'
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
                    if 'experimental_features' in loaded:
                        config['experimental_features'] = loaded['experimental_features']
                    if 'theme' in loaded:
                        config['theme'] = loaded['theme']
                    return config
            except Exception:
                pass
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
    
    def get_theme(self):
        theme = self.config.get('theme', 'auto')
        if theme == 'auto':
            bg = _get_gtk_bg()
            if bg and _is_dark(bg):
                return 'gtk_dark'
            return 'gtk_light'
        return theme
    
    def is_tab_visible(self, tab_key):
        if tab_key == 'output':
            return True
        if tab_key in ('routing', 'fx'):
            return self.config.get('experimental_features', False) and self.config['visible_tabs'].get(tab_key, False)
        return self.config['visible_tabs'].get(tab_key, True)

# --- Dialog de configuration ---
class SettingsDialog(QDialog):
    def __init__(self, ui_config, parent=None):
        super().__init__(parent)
        self.ui_config = ui_config
        self.i18n = I18n.instance()
        self.lang = self.i18n.get_lang()
        self.setWindowTitle(self.i18n.tr('settings'))
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(self.i18n.tr('lang_auto'), 'auto')
        self.lang_combo.addItem(self.i18n.tr('lang_fr'), 'fr')
        self.lang_combo.addItem(self.i18n.tr('lang_en'), 'en')
        current_lang = ui_config.config['language']
        idx = self.lang_combo.findData(current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        form_layout.addRow(self.i18n.tr('language') + ':', self.lang_combo)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.i18n.tr('theme_auto'), 'auto')
        self.theme_combo.addItem(self.i18n.tr('theme_gtk_dark'), 'gtk_dark')
        self.theme_combo.addItem(self.i18n.tr('theme_gtk_light'), 'gtk_light')
        self.theme_combo.addItem(self.i18n.tr('theme_dark_alt'), 'dark_alt')
        current_theme = ui_config.config.get('theme', 'auto')
        idx = self.theme_combo.findData(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        form_layout.addRow(self.i18n.tr('theme') + ':', self.theme_combo)
        
        self.close_combo = QComboBox()
        self.close_combo.addItem(self.i18n.tr('close_tray'), 'tray')
        self.close_combo.addItem(self.i18n.tr('close_quit'), 'quit')
        current_close = ui_config.config.get('close_behavior', 'tray')
        idx = self.close_combo.findData(current_close)
        if idx >= 0:
            self.close_combo.setCurrentIndex(idx)
        form_layout.addRow(self.i18n.tr('close_behavior') + ':', self.close_combo)
        
        self.experimental_cb = QCheckBox(self.i18n.tr('enable_experimental'))
        self.experimental_cb.setChecked(ui_config.config.get('experimental_features', False))
        self.experimental_cb.toggled.connect(self._on_experimental_toggled)
        form_layout.addRow('', self.experimental_cb)
        
        self.experimental_warning = QLabel(self.i18n.tr('experimental_warning'))
        self.experimental_warning.setFont(QFont("Monospace", 8))
        self.experimental_warning.setStyleSheet("color: #ff9800;")
        self.experimental_warning.setWordWrap(True)
        self.experimental_warning.setVisible(ui_config.config.get('experimental_features', False))
        form_layout.addRow('', self.experimental_warning)
        
        tab_keys = [
            ('settings', 'Réglages / Settings'),
            ('routing', 'Routing (expérimental)'),
            ('profiles', 'Profils / Profiles'),
            ('aes67', 'AES67'),
            ('status', 'État / Status'),
            ('fx', 'FX (expérimental)')
        ]
        
        self.tab_checkboxes = {}
        tab_group_label = QLabel(self.i18n.tr('show_tabs') + ':')
        form_layout.addRow(tab_group_label)
        
        experimental_enabled = ui_config.config.get('experimental_features', False)
        
        for key, label in tab_keys:
            cb = QCheckBox(label)
            is_experimental = key in ('routing', 'fx')
            if is_experimental:
                cb.setChecked(ui_config.config['visible_tabs'].get(key, False))
                cb.setEnabled(experimental_enabled)
                cb.setStyleSheet("color: #ff9800;")
            else:
                cb.setChecked(ui_config.config['visible_tabs'].get(key, True))
                cb.setEnabled(True)
            self.tab_checkboxes[key] = cb
            form_layout.addRow('', cb)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox()
        save_btn = button_box.addButton(self.i18n.tr('save'), QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = button_box.addButton(self.i18n.tr('cancel'), QDialogButtonBox.ButtonRole.RejectRole)
        reset_btn = button_box.addButton(self.i18n.tr('reset_config'), QDialogButtonBox.ButtonRole.ResetRole)
        
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)
        reset_btn.clicked.connect(self._on_reset)
        
        layout.addWidget(button_box)
    
    def _on_experimental_toggled(self, checked):
        self.experimental_warning.setVisible(checked)
        for key in ('routing', 'fx'):
            if key in self.tab_checkboxes:
                self.tab_checkboxes[key].setEnabled(checked)
                if checked:
                    self.tab_checkboxes[key].setChecked(True)
                else:
                    self.tab_checkboxes[key].setChecked(False)
    
    def _on_save(self):
        self.ui_config.config['language'] = self.lang_combo.currentData()
        self.ui_config.config['theme'] = self.theme_combo.currentData()
        self.ui_config.config['close_behavior'] = self.close_combo.currentData()
        self.ui_config.config['experimental_features'] = self.experimental_cb.isChecked()
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
                self.theme_combo.setCurrentIndex(self.theme_combo.findData('auto'))
                self.close_combo.setCurrentIndex(self.close_combo.findData('tray'))
                self.experimental_cb.setChecked(False)
                self.experimental_warning.setVisible(False)
                for key, cb in self.tab_checkboxes.items():
                    if key in ('routing', 'fx'):
                        cb.setChecked(False)
                        cb.setEnabled(False)
                    else:
                        cb.setChecked(True)
                        cb.setEnabled(True)
                QMessageBox.information(self, 'OK', self.i18n.tr('config_reset'))

# --- Fenêtre principale ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pw = PipeWireManager()
        self.config_mgr = ConfigManager()
        self.ui_config = UIConfig()
        self.i18n = I18n.instance()
        self.i18n.set_ui_config(self.ui_config)
        self.lang = self.i18n.get_lang()
        self.logger = Logger.instance()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(self.i18n.tr('title'))
        self.setMinimumSize(700, 500)
        
        self._drag_pos = None
        
        central = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._create_navigation_bar(layout)
        
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout()
        wrapper_layout.setContentsMargins(16, 4, 16, 16)
        
        self.stack = QStackedWidget()
        wrapper_layout.addWidget(self.stack)
        wrapper.setLayout(wrapper_layout)
        layout.addWidget(wrapper, 1)
        
        central.setLayout(layout)
        self.setCentralWidget(central)
        
        # Création immédiate des onglets légers et essentiels
        self.audio_tab = AudioTab(self.pw)
        self.profiles_tab = ProfilesTab(self.pw, self.config_mgr)
        
        # Les autres onglets sont créés à la demande (lazy loading)
        self.all_tabs = {
            'output': self.audio_tab,
            'settings': None,
            'routing': None,
            'profiles': self.profiles_tab,
            'aes67': None,
            'status': None,
            'fx': None
        }
        
        self._rebuild_stack()
        
        if self.buttons:
            self.buttons[0].setChecked(True)
        self.btn_group.idClicked.connect(self._on_nav)
        self.profiles_tab.profile_loaded.connect(lambda: (
            self.audio_tab.load_current(),
            self.all_tabs['settings'].load_current() if self.all_tabs['settings'] else None,
            self.statusBar().showMessage(self.i18n.tr('profile_loaded'), 5000)
        ))
        self.statusBar().showMessage(self.i18n.tr('ready').format(self.pw.get_version()), 5000)
        
        self._restore_geometry()
        self._install_shortcuts()
        
        # Appliquer le thème après création des onglets
        self._apply_theme()
        
        # Arrondir les angles
        self._apply_rounded_corners(12)
    
    def _apply_rounded_corners(self, radius=12):
        rectf = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rectf, radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'windowHandle') and self.windowHandle():
            self._apply_rounded_corners(12)
    
    def _get_theme_colors(self):
        """Retourne les couleurs selon le thème"""
        from .themes import THEMES
        
        theme = self.ui_config.get_theme()
        
        if theme == 'gtk_dark':
            bg = _get_gtk_bg() or '#2a2a2a'
            colors = THEMES['gtk_dark'].copy()
            colors['titlebar_bg'] = _darken(bg, 0.75)
            colors['btn_bg'] = bg
            colors['btn_checked'] = _darken(bg, 0.55)
            colors['btn_hover'] = _lighten(bg, 1.15)
            colors['window_bg'] = bg
            return colors
        
        if theme in THEMES:
            return THEMES[theme].copy()
        
        return THEMES['dark_alt'].copy()
    
    def _apply_theme(self):
        """Applique le thème à tous les widgets"""
        colors = self._get_theme_colors()
        
        tooltip_bg = colors.get('tooltip_bg', '#2a2a2a')
        tooltip_text = colors.get('tooltip_text', '#ffffff')
        tooltip_border = colors.get('tooltip_border', '#555555')
        
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {colors['window_bg']}; color: {colors['window_text']}; }}
            QToolTip {{
                background-color: {tooltip_bg};
                color: {tooltip_text};
                border: 1px solid {tooltip_border};
                padding: 4px 8px;
                font-size: 12px;
            }}
        """)
        
        self._apply_theme_to_tabs()
        for tab in self.all_tabs.values():
            if tab is not None and hasattr(tab, 'refresh_language'):
                try:
                    tab.refresh_language()
                except Exception:
                    pass
    
    def _apply_theme_to_tabs(self):
        colors = self._get_theme_colors()
        for tab in self.all_tabs.values():
            if tab is not None and hasattr(tab, 'set_theme_colors'):
                try:
                    tab.set_theme_colors(colors)
                except Exception:
                    pass
    
    def _create_navigation_bar(self, layout):
        colors = self._get_theme_colors()
        
        nav = QWidget()
        nav.setStyleSheet(f"background-color: {colors['titlebar_bg']};")
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(4, 12, 4, 12)
        nav_layout.setSpacing(2)
        
        self.title_lbl = QLabel("PipeWire\nControl\nCenter")
        self.title_lbl.setStyleSheet(f"""
            color: {colors['btn_text_checked']};
            font-size: 11px;
            font-weight: bold;
            padding: 0 4px;
        """)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        nav_layout.addWidget(self.title_lbl)
        
        nav_layout.addStretch(1)
        
        self.btn_group = QButtonGroup()
        self.btn_group.setExclusive(True)
        self.buttons = []
        self.button_map = {}
        
        all_tab_keys = ['output', 'settings', 'routing', 'profiles', 'aes67', 'status', 'fx']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        
        btn_style = f"""
            QPushButton {{
                background-color: {colors['btn_bg']};
                color: {colors['btn_text']};
                border: 1px solid {colors['titlebar_bg']};
                border-radius: 4px;
                padding: 10px 18px;
                min-height: 16px;
                font-size: 13px;
            }}
            QPushButton:checked {{
                background-color: {colors['btn_checked']};
                color: {colors['btn_text_checked']};
                border-color: {colors['btn_checked']};
            }}
            QPushButton:hover:!checked {{
                background-color: {colors['btn_hover']};
                color: {colors['btn_text_hover']};
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
                color: {colors['btn_text']};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 4px 0px;
            }}
            QToolButton:hover {{
                color: {colors['btn_text_hover']};
            }}
        """)
        settings_btn.clicked.connect(self._open_settings)
        nav_layout.addWidget(settings_btn)
        
        min_btn = QToolButton()
        min_btn.setText("─")
        min_btn.setToolTip("Minimiser")
        min_btn.setFixedSize(28, 28)
        min_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {colors['btn_text']};
                border: none;
                font-size: 14px;
            }}
            QToolButton:hover {{
                background-color: {colors['btn_hover']};
                color: {colors['btn_text_hover']};
            }}
        """)
        min_btn.clicked.connect(self.showMinimized)
        nav_layout.addWidget(min_btn)
        
        close_btn = QToolButton()
        close_btn.setText("✕")
        close_btn.setToolTip("Fermer")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #aaa;
                border: none;
                font-size: 14px;
            }
            QToolButton:hover {
                background-color: #e81123;
                color: white;
            }
        """)
        close_btn.clicked.connect(self.close)
        nav_layout.addWidget(close_btn)
        
        nav.setLayout(nav_layout)
        layout.addWidget(nav)
        self.nav_widget = nav
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 40:
                self.windowHandle().startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)
    
    def _restore_geometry(self):
        settings = QSettings('PipeWireControlCenter', 'MainWindow')
        geometry = settings.value('geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)
        else:
            self.resize(900, 600)
    
    def _save_geometry(self):
        settings = QSettings('PipeWireControlCenter', 'MainWindow')
        settings.setValue('geometry', self.saveGeometry())
    
    def _install_shortcuts(self):
        for i in range(1, 8):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda idx=i-1: self._goto_tab(idx))
        refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_shortcut.activated.connect(self._refresh_current_tab)
        f5_shortcut = QShortcut(QKeySequence("F5"), self)
        f5_shortcut.activated.connect(self._refresh_all)
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self._quit_app)
    
    def _goto_tab(self, idx):
        all_tab_keys = ['output', 'settings', 'routing', 'profiles', 'aes67', 'status', 'fx']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        if idx < len(visible_keys):
            self.stack.setCurrentIndex(idx)
            if idx < len(self.buttons):
                self.buttons[idx].setChecked(True)
    
    def _refresh_current_tab(self):
        current_idx = self.stack.currentIndex()
        all_tab_keys = ['output', 'settings', 'routing', 'profiles', 'aes67', 'status', 'fx']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        if current_idx < len(visible_keys):
            key = visible_keys[current_idx]
            if key == 'status':
                if self.all_tabs['status']:
                    self.all_tabs['status'].refresh()
            elif key == 'output':
                self.audio_tab.refresh_devices()
            elif key == 'settings':
                if self.all_tabs['settings']:
                    self.all_tabs['settings'].load_current()
            elif key == 'routing':
                if self.all_tabs['routing']:
                    self.all_tabs['routing'].refresh()
            elif key == 'fx':
                if self.all_tabs['fx']:
                    self.all_tabs['fx'].refresh_language()
            self.statusBar().showMessage(self.i18n.tr('refreshed'), 2000)
    
    def _refresh_all(self):
        self.audio_tab.refresh_devices()
        if self.all_tabs['status']:
            self.all_tabs['status'].refresh()
        self.statusBar().showMessage(self.i18n.tr('full_refresh'), 2000)
    
    def _quit_app(self):
        self._save_geometry()
        self.audio_tab.shutdown()
        for key in ['settings', 'routing', 'profiles', 'aes67', 'status', 'fx']:
            tab = self.all_tabs.get(key)
            if tab is not None and hasattr(tab, 'shutdown'):
                try:
                    tab.shutdown()
                except Exception:
                    pass
        QApplication.quit()
    
    def _rebuild_stack(self):
        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
        
        self.stack_tab_indices = {}
        self.tab_map = {}
        
        all_tab_keys = ['output', 'settings', 'routing', 'profiles', 'aes67', 'status', 'fx']
        visible_keys = [k for k in all_tab_keys if self.ui_config.is_tab_visible(k)]
        
        for key in visible_keys:
            if self.all_tabs[key] is None:
                self.all_tabs[key] = self._create_tab(key)
            
            idx = self.stack.addWidget(self.all_tabs[key])
            self.stack_tab_indices[key] = idx
            self.tab_map[key] = self.all_tabs[key]
    
    def _create_tab(self, key):
        """Crée un onglet à la demande"""
        if key == 'settings':
            return SettingsTab(self.pw)
        elif key == 'routing':
            return RoutingTab(self.pw)
        elif key == 'profiles':
            return ProfilesTab(self.pw, self.config_mgr)
        elif key == 'aes67':
            return Aes67Tab(self.pw)
        elif key == 'status':
            return StatusTab(self.pw)
        elif key == 'fx':
            return FXTab(self.pw)
        return None
    
    def _on_nav(self, idx):
        self.stack.setCurrentIndex(idx)
    
    def _open_settings(self):
        dialog = SettingsDialog(self.ui_config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.i18n.set_lang(self.ui_config.config['language'])
            self.lang = self.i18n.get_lang()
            self.setWindowTitle(self.i18n.tr('title'))
            self.statusBar().showMessage(self.i18n.tr('ui_config_saved'), 3000)
            self._apply_theme()
            self._rebuild_navigation()
            self._rebuild_stack()
            self._install_shortcuts()
            self._apply_rounded_corners(12)
    
    def _rebuild_navigation(self):
        if hasattr(self, 'nav_widget') and self.nav_widget:
            self.nav_widget.deleteLater()
        layout = self.centralWidget().layout()
        self._create_navigation_bar(layout)
        layout.insertWidget(0, self.nav_widget)
        if self.buttons:
            self.buttons[0].setChecked(True)
        self.btn_group.idClicked.connect(self._on_nav)
    
    def closeEvent(self, event):
        self._save_geometry()
        behavior = self.ui_config.config.get('close_behavior', 'tray')
        if behavior == 'quit':
            self.audio_tab.shutdown()
            for key in ['settings', 'routing', 'profiles', 'aes67', 'status', 'fx']:
                tab = self.all_tabs.get(key)
                if tab is not None and hasattr(tab, 'shutdown'):
                    try:
                        tab.shutdown()
                    except Exception:
                        pass
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
            self.hide()
