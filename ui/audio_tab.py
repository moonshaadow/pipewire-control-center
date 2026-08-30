#!/usr/bin/env python3
"""Onglet Audio Devices : sorties, entrées et périphériques"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QStackedWidget, QButtonGroup,
    QPushButton, QLabel, QMessageBox, QFrame, QScrollArea,
    QSlider, QCheckBox, QStyle, QTreeWidget, QTreeWidgetItem, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction
from .icon_utils import get_device_icon_path
from .i18n import I18n
from .logger import Logger

# --- Sliders ---
class ClickSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._click_dragging = False
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_dragging = True
            self.setValue(QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                int(event.position().x()) if hasattr(event, 'position') else event.x(),
                self.width()
            ))
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._click_dragging = False
        super().mouseReleaseEvent(event)
    
    def is_dragging(self):
        return self._click_dragging or self.isSliderDown()


# --- Cartes device ---
class DeviceCard(QFrame):
    clicked = pyqtSignal(dict)
    
    def __init__(self, device, is_selected=False):
        super().__init__()
        self.device = device
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self.setProperty("selected", is_selected)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(150, 85)
        self.setMaximumSize(200, 95)
        
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)
        
        icon_path = get_device_icon_path(device)
        self.icon_lbl = QLabel()
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_lbl.setPixmap(pixmap)
        else:
            self.icon_lbl.setText("🔊")
            self.icon_lbl.setFont(QFont("Monospace", 20))
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        self.name_lbl = QLabel(device.get('description', 'Inconnu')[:40])
        self.name_lbl.setFont(QFont("Monospace", 7))
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setMaximumWidth(180)
        layout.addWidget(self.name_lbl)
        
        if device.get('state') == 'running':
            badge = QLabel("● " + self.i18n.tr('active'))
            badge.setFont(QFont("Monospace", 6))
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet("color: #4CAF50;")
            layout.addWidget(badge)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            DeviceCard[selected="true"] {
                background-color: #1565C0;
                border: 2px solid #1E88E5;
                border-radius: 8px;
            }
            DeviceCard[selected="true"] QLabel {
                color: white;
            }
            DeviceCard[selected="false"] {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 8px;
            }
            DeviceCard[selected="false"] QLabel {
                color: #cccccc;
            }
            DeviceCard[selected="false"]:hover {
                background-color: #333333;
                border: 1px solid #666666;
            }
        """)
    
    def set_selected(self, selected):
        self.is_selected = selected
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.device)


# --- Ligne device sortie + volume + infos ---
class DeviceVolumeRow(QWidget):
    volume_changed = pyqtSignal(int, float)
    
    def __init__(self, device, pw):
        super().__init__()
        self.device = device
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(30)
        
        self.card = DeviceCard(self.device, self.device.get('is_default', False))
        self.card.clicked.connect(self._on_card_clicked)
        layout.addWidget(self.card)
        
        vol_layout = QVBoxLayout()
        vol_layout.setSpacing(2)
        
        vol_top = QHBoxLayout()
        vol_top.setSpacing(30)
        
        self.slider = ClickSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.setMinimumWidth(100)
        self.slider.setMaximumWidth(800)
        self.slider.valueChanged.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_release)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px; background: #444; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px; height: 10px; margin: -3px 0;
                background: #fff; border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50; border-radius: 2px;
            }
        """)
        vol_top.addWidget(self.slider, 1)
        
        self.vol_label = QLabel("100%")
        self.vol_label.setFont(QFont("Monospace", 9))
        self.vol_label.setStyleSheet("color: white;")
        self.vol_label.setFixedWidth(40)
        self.vol_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vol_top.addWidget(self.vol_label)
        
        vol_layout.addLayout(vol_top)
        
        info_layout = QHBoxLayout()
        info_layout.setSpacing(0)
        info_layout.setContentsMargins(30, 0, 0, 0)
        self.info_lbl = QLabel("48000 Hz / S32LE")
        self.info_lbl.setFont(QFont("Monospace", 8))
        self.info_lbl.setStyleSheet("color: #aaa;")
        info_layout.addWidget(self.info_lbl)
        info_layout.addStretch()
        vol_layout.addLayout(info_layout)
        
        boost_layout = QHBoxLayout()
        boost_layout.addStretch()
        self.boost_cb = QCheckBox(self.i18n.tr('boost_150'))
        self.boost_cb.setFont(QFont("Monospace", 7))
        self.boost_cb.setStyleSheet("color: #888;")
        self.boost_cb.toggled.connect(self._on_boost)
        boost_layout.addWidget(self.boost_cb)
        vol_layout.addLayout(boost_layout)
        
        layout.addLayout(vol_layout, 1)
        self.setLayout(layout)
    
    def _on_card_clicked(self, device):
        self.logger.info(f"Clic sur carte périphérique: {device.get('name', 'inconnu')}")
        self.pw.set_default_device(device['id'])
    
    def _on_slider_moved(self, value):
        self.vol_label.setText(f"{value}%")
        if self.slider.is_dragging():
            self.volume_changed.emit(self.device['id'], value / 100.0)
    
    def _on_release(self):
        self.logger.debug(f"Slider relâché: {self.device['name']} -> {self.slider.value()}%")
        self.volume_changed.emit(self.device['id'], self.slider.value() / 100.0)
    
    def _on_boost(self, checked):
        self.logger.debug(f"Boost {self.device['name']}: {'activé' if checked else 'désactivé'}")
        if checked:
            self.slider.setRange(0, 150)
        else:
            self.slider.setRange(0, 100)
            if self.slider.value() > 100:
                self.slider.setValue(100)
    
    def update_volume(self, volume):
        if not self.slider.is_dragging():
            self.slider.blockSignals(True)
            self.slider.setValue(int(volume * 100))
            self.vol_label.setText(f"{int(volume * 100)}%")
            self.slider.blockSignals(False)
    
    def update_info(self, rate, fmt, bits):
        if rate != '?':
            text = f"{rate} Hz / {fmt}"
            if bits:
                text += f" / {bits} bits"
            self.info_lbl.setText(text)
    
    def set_selected(self, selected):
        self.card.set_selected(selected)


# --- Ligne device entrée + volume + infos ---
class DeviceInputRow(QWidget):
    volume_changed = pyqtSignal(int, float)
    
    def __init__(self, device, pw):
        super().__init__()
        self.device = device
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(30)
        
        self.card = DeviceCard(self.device, self.device.get('is_default', False))
        self.card.clicked.connect(self._on_card_clicked)
        layout.addWidget(self.card)
        
        vol_layout = QVBoxLayout()
        vol_layout.setSpacing(2)
        
        vol_top = QHBoxLayout()
        vol_top.setSpacing(30)
        
        self.slider = ClickSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.setMinimumWidth(100)
        self.slider.setMaximumWidth(800)
        self.slider.valueChanged.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_release)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px; background: #444; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px; height: 10px; margin: -3px 0;
                background: #fff; border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50; border-radius: 2px;
            }
        """)
        vol_top.addWidget(self.slider, 1)
        
        self.vol_label = QLabel("100%")
        self.vol_label.setFont(QFont("Monospace", 9))
        self.vol_label.setStyleSheet("color: white;")
        self.vol_label.setFixedWidth(40)
        self.vol_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vol_top.addWidget(self.vol_label)
        
        vol_layout.addLayout(vol_top)
        
        info_layout = QHBoxLayout()
        info_layout.setSpacing(0)
        info_layout.setContentsMargins(30, 0, 0, 0)
        self.info_lbl = QLabel("48000 Hz / S32LE")
        self.info_lbl.setFont(QFont("Monospace", 8))
        self.info_lbl.setStyleSheet("color: #aaa;")
        info_layout.addWidget(self.info_lbl)
        info_layout.addStretch()
        vol_layout.addLayout(info_layout)
        
        boost_spacer = QWidget()
        boost_spacer.setFixedHeight(20)
        vol_layout.addWidget(boost_spacer)
        
        layout.addLayout(vol_layout, 1)
        self.setLayout(layout)
    
    def _on_card_clicked(self, device):
        self.logger.info(f"Clic sur carte périphérique entrée: {device.get('name', 'inconnu')}")
        self.pw.set_default_device(device['id'])
    
    def _on_slider_moved(self, value):
        self.vol_label.setText(f"{value}%")
        if self.slider.is_dragging():
            self.volume_changed.emit(self.device['id'], value / 100.0)
    
    def _on_release(self):
        self.logger.debug(f"Slider relâché: {self.device['name']} -> {self.slider.value()}%")
        self.volume_changed.emit(self.device['id'], self.slider.value() / 100.0)
    
    def update_volume(self, volume):
        if not self.slider.is_dragging():
            self.slider.blockSignals(True)
            self.slider.setValue(int(volume * 100))
            self.vol_label.setText(f"{int(volume * 100)}%")
            self.slider.blockSignals(False)
    
    def update_info(self, rate, fmt, bits):
        if rate != '?':
            text = f"{rate} Hz / {fmt}"
            if bits:
                text += f" / {bits} bits"
            self.info_lbl.setText(text)
    
    def set_selected(self, selected):
        self.card.set_selected(selected)


# --- Ligne flux ---
class StreamRow(QFrame):
    volume_changed = pyqtSignal(int, float)
    
    def __init__(self, stream):
        super().__init__()
        self.stream = stream
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: #2a2a2a; border-radius: 4px; margin: 1px 0;")
        self.setFixedHeight(36)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(10)
        
        self.name_lbl = QLabel(stream.get('name', '')[:22])
        self.name_lbl.setFont(QFont("Monospace", 8))
        self.name_lbl.setStyleSheet("color: #aaaaaa;")
        self.name_lbl.setFixedWidth(140)
        layout.addWidget(self.name_lbl)
        
        rate = stream.get('rate', '?')
        rate_text = "?"
        if rate != '?' and rate is not None:
            r = int(rate)
            rate_text = f"{r/1000:.1f}k" if r >= 1000 else f"{r} Hz"
        self.rate_lbl = QLabel(rate_text)
        self.rate_lbl.setFont(QFont("Monospace", 7))
        self.rate_lbl.setStyleSheet("color: #888888;")
        self.rate_lbl.setFixedWidth(55)
        layout.addWidget(self.rate_lbl)
        
        self.slider = ClickSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.setMinimumWidth(100)
        self.slider.setMaximumWidth(800)
        self.slider.valueChanged.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_release)
        layout.addWidget(self.slider, 1)
        
        self.vol_lbl = QLabel("100%")
        self.vol_lbl.setFont(QFont("Monospace", 7))
        self.vol_lbl.setStyleSheet("color: #888888;")
        self.vol_lbl.setFixedWidth(35)
        self.vol_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.vol_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        self.setLayout(layout)
    
    def _on_slider_moved(self, value):
        self.vol_lbl.setText(f"{value}%")
        if self.slider.is_dragging():
            self.volume_changed.emit(self.stream.get('id', 0), value / 100.0)
    
    def _on_release(self):
        self.logger.debug(f"Slider flux relâché: {self.stream.get('name', 'inconnu')} -> {self.slider.value()}%")
        self.volume_changed.emit(self.stream.get('id', 0), self.slider.value() / 100.0)
    
    def update_volume(self, volume):
        if not self.slider.is_dragging():
            self.slider.blockSignals(True)
            self.slider.setValue(int(volume * 100))
            self.vol_lbl.setText(f"{int(volume * 100)}%")
            self.slider.blockSignals(False)


# --- Onglet Audio Devices principal ---
class AudioTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self.device_rows = {}
        self.input_rows = {}
        self.stream_rows = {}
        self.selected_output = None
        self.selected_input = None
        self._prev_device_names = set()
        self._init_ui()
        self.refresh_devices()
        self._refresh_devices_table()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(100)
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Boutons de sous-onglets
        sub_nav_layout = QHBoxLayout()
        sub_nav_layout.setContentsMargins(0, 4, 0, 4)
        sub_nav_layout.setSpacing(1)
        sub_nav_layout.addStretch()
        
        self.sub_btn_group = QButtonGroup()
        self.sub_btn_group.setExclusive(True)
        
        self.sub_buttons = []
        sub_pages = [
            (self.i18n.tr('sorties'), 0),
            (self.i18n.tr('entrees'), 1),
            (self.i18n.tr('devices'), 2)
        ]
        
        sub_btn_style = """
            QPushButton {
                background-color: palette(window);
                color: #999999;
                border: 1px solid #222226;
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 13px;
                margin: 0 1px;
            }
            QPushButton:checked {
                background-color: #1a1a1e;
                color: #ffffff;
            }
            QPushButton:hover:!checked {
                background-color: #3a3a3a;
                color: #dddddd;
            }
        """
        
        for text, idx in sub_pages:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(sub_btn_style)
            self.sub_btn_group.addButton(btn, idx)
            sub_nav_layout.addWidget(btn)
            self.sub_buttons.append(btn)
        
        sub_nav_layout.addStretch()
        layout.addLayout(sub_nav_layout)
        
        # Stack pour les pages
        self.sub_stack = QStackedWidget()
        
        # Page Sorties
        self.output_tab = QWidget()
        output_layout = QVBoxLayout()
        output_layout.setSpacing(2)
        output_layout.setContentsMargins(0, 0, 0, 0)
        
        self.output_gb = QGroupBox(self.i18n.tr('peripheriques_sortie'))
        output_gb_layout = QVBoxLayout()
        output_gb_layout.setSpacing(2)
        
        self.output_widget = QWidget()
        self.output_layout = QVBoxLayout()
        self.output_layout.setSpacing(2)
        self.output_layout.setContentsMargins(0, 0, 0, 0)
        self.output_widget.setLayout(self.output_layout)
        
        self.output_scroll = QScrollArea()
        self.output_scroll.setWidgetResizable(True)
        self.output_scroll.setWidget(self.output_widget)
        self.output_scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 0px; }")
        output_gb_layout.addWidget(self.output_scroll)
        self.output_gb.setLayout(output_gb_layout)
        output_layout.addWidget(self.output_gb)
        self.output_tab.setLayout(output_layout)
        self.sub_stack.addWidget(self.output_tab)
        
        # Page Entrées
        self.input_tab = QWidget()
        input_layout = QVBoxLayout()
        input_layout.setSpacing(2)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_gb = QGroupBox(self.i18n.tr('peripheriques_entree'))
        input_gb_layout = QVBoxLayout()
        input_gb_layout.setSpacing(2)
        
        self.input_widget = QWidget()
        self.input_layout = QVBoxLayout()
        self.input_layout.setSpacing(2)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        self.input_widget.setLayout(self.input_layout)
        
        self.input_scroll = QScrollArea()
        self.input_scroll.setWidgetResizable(True)
        self.input_scroll.setWidget(self.input_widget)
        self.input_scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 0px; }")
        input_gb_layout.addWidget(self.input_scroll)
        self.input_gb.setLayout(input_gb_layout)
        input_layout.addWidget(self.input_gb)
        self.input_tab.setLayout(input_layout)
        self.sub_stack.addWidget(self.input_tab)
        
        # Page Périphériques (déplacée depuis DevicesTab)
        self.devices_page = QWidget()
        devices_page_layout = QVBoxLayout()
        devices_page_layout.setSpacing(8)
        devices_page_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tableau des périphériques
        self.devices_gb = QGroupBox(self.i18n.tr('peripheriques_detectes'))
        devices_layout = QVBoxLayout()
        
        self.devices_tree = QTreeWidget()
        self.devices_tree.setHeaderLabels([
            self.i18n.tr('id'), self.i18n.tr('description'), self.i18n.tr('type'),
            self.i18n.tr('state'), self.i18n.tr('rate'), self.i18n.tr('format'),
            self.i18n.tr('range')
        ])
        self.devices_tree.setColumnWidth(0, 50)
        self.devices_tree.setColumnWidth(1, 220)
        self.devices_tree.setColumnWidth(6, 140)
        devices_layout.addWidget(self.devices_tree)
        
        # Boutons d'action
        devices_btn_layout = QHBoxLayout()
        self.set_default_btn = QPushButton(self.i18n.tr('definir_defaut'))
        self.set_default_btn.clicked.connect(self._set_default_device)
        devices_btn_layout.addWidget(self.set_default_btn)
        devices_btn_layout.addStretch()
        devices_layout.addLayout(devices_btn_layout)
        
        # Mode suppression
        self.destroy_cb = QCheckBox(self.i18n.tr('mode_suppression'))
        self.destroy_cb.setStyleSheet("color: #ef5350; font-weight: bold;")
        self.destroy_cb.stateChanged.connect(self._on_destroy_state_changed)
        devices_layout.addWidget(self.destroy_cb)
        
        self.destroy_btn = QPushButton(self.i18n.tr('supprimer_noeud'))
        self.destroy_btn.setStyleSheet("QPushButton { color: #ef5350; font-weight: bold; }")
        self.destroy_btn.clicked.connect(self._destroy_node)
        self.destroy_btn.setVisible(False)
        devices_layout.addWidget(self.destroy_btn)
        
        self.devices_gb.setLayout(devices_layout)
        devices_page_layout.addWidget(self.devices_gb)
        
        # Tableau des applications
        self.apps_gb = QGroupBox(self.i18n.tr('applications'))
        apps_layout = QVBoxLayout()
        
        self.apps_tree = QTreeWidget()
        self.apps_tree.setHeaderLabels([
            self.i18n.tr('id'), self.i18n.tr('application'), self.i18n.tr('type'),
            self.i18n.tr('state'), self.i18n.tr('rate'), self.i18n.tr('format'),
            self.i18n.tr('linked_device')
        ])
        self.apps_tree.setColumnWidth(0, 50)
        self.apps_tree.setColumnWidth(1, 180)
        self.apps_tree.setColumnWidth(6, 200)
        self.apps_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.apps_tree.customContextMenuRequested.connect(self._show_app_context_menu)
        apps_layout.addWidget(self.apps_tree)
        
        self.apps_gb.setLayout(apps_layout)
        devices_page_layout.addWidget(self.apps_gb)
        
        self.devices_page.setLayout(devices_page_layout)
        self.sub_stack.addWidget(self.devices_page)
        
        layout.addWidget(self.sub_stack)
        
        # Sélection par défaut
        self.sub_buttons[0].setChecked(True)
        self.sub_btn_group.idClicked.connect(self._on_sub_nav)
        
        # Flux actifs (visible seulement dans Sorties)
        self.flux_gb = QGroupBox(self.i18n.tr('flux_actifs'))
        flux_layout = QVBoxLayout()
        
        self.streams_widget = QWidget()
        self.streams_layout = QVBoxLayout()
        self.streams_layout.setSpacing(1)
        self.streams_layout.setContentsMargins(0, 0, 0, 0)
        self.streams_widget.setLayout(self.streams_layout)
        
        self.streams_scroll = QScrollArea()
        self.streams_scroll.setWidgetResizable(True)
        self.streams_scroll.setWidget(self.streams_widget)
        self.streams_scroll.setMaximumHeight(180)
        self.streams_scroll.setStyleSheet("QScrollArea { border: none; }")
        flux_layout.addWidget(self.streams_scroll)
        
        self.empty_lbl = QLabel(self.i18n.tr('aucun_flux'))
        self.empty_lbl.setFont(QFont("Monospace", 9))
        self.empty_lbl.setStyleSheet("color: #555;")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.hide()
        flux_layout.addWidget(self.empty_lbl)
        
        self.flux_gb.setLayout(flux_layout)
        self.output_tab.layout().addWidget(self.flux_gb)
        
        # Restaurer l'état des colonnes
        self._restore_header_state()
        
        self.setLayout(layout)
    
    def _on_sub_nav(self, idx):
        self.sub_stack.setCurrentIndex(idx)
        if idx == 2:  # Page Périphériques
            self._refresh_devices_table()
    
    def _restore_header_state(self):
        try:
            settings = QSettings('PipeWireControlCenter', 'DevicesTab')
            devices_state = settings.value('devices_header_state')
            if devices_state is not None:
                self.devices_tree.header().restoreState(devices_state)
            apps_state = settings.value('apps_header_state')
            if apps_state is not None:
                self.apps_tree.header().restoreState(apps_state)
        except Exception as e:
            self.logger.error(f"Erreur restauration colonnes: {e}")
    
    def _save_header_state(self):
        try:
            settings = QSettings('PipeWireControlCenter', 'DevicesTab')
            settings.setValue('devices_header_state', self.devices_tree.header().saveState())
            settings.setValue('apps_header_state', self.apps_tree.header().saveState())
            settings.sync()
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde colonnes: {e}")
    
    def _refresh_devices_table(self):
        """Rafraîchit les tableaux Périphériques et Applications"""
        # Sauvegarder la sélection
        selected_item = self.devices_tree.currentItem()
        selected_id = None
        if selected_item:
            selected_text = selected_item.text(0).replace(" ★", "")
            try:
                selected_id = int(selected_text)
            except ValueError:
                selected_id = None
        
        self.devices_tree.clear()
        devices = self.pw.get_devices()
        
        for dev in devices:
            rate_str = f"{dev['rate']} Hz" if dev['rate'] != '?' else '?'
            
            if dev['rates_min'] and dev['rates_max']:
                range_str = f"{dev['rates_min']}-{dev['rates_max']} Hz"
            elif dev['rates_default']:
                range_str = f"{dev['rates_default']} Hz (fixe)"
            else:
                range_str = "?"
            
            fmt_str = str(dev['format']) if dev['format'] != '?' else '?'
            if dev.get('bits'):
                fmt_str += f" / {dev['bits']} bits"
            
            item = QTreeWidgetItem([
                str(dev['id']),
                dev['description'],
                dev['type'],
                dev['state'],
                rate_str,
                fmt_str,
                range_str
            ])
            
            icon_path = get_device_icon_path(dev)
            if icon_path and os.path.exists(icon_path):
                item.setIcon(1, QIcon(icon_path))
            
            if dev['is_default']:
                font = item.font(0)
                font.setBold(True)
                for i in range(7):
                    item.setFont(i, font)
                item.setText(0, item.text(0) + " ★")
            
            if dev['state'] == 'running':
                item.setForeground(3, Qt.GlobalColor.green)
            elif dev['state'] == 'idle':
                item.setForeground(3, Qt.GlobalColor.gray)
            
            self.devices_tree.addTopLevelItem(item)
            
            if selected_id is not None and dev['id'] == selected_id:
                self.devices_tree.setCurrentItem(item)
        
        # Rafraîchir le tableau des applications
        self._refresh_apps_table()
    
    def _refresh_apps_table(self):
        """Rafraîchit le tableau des nœuds d'application"""
        selected_item = self.apps_tree.currentItem()
        selected_id = None
        if selected_item:
            selected_id = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        self.apps_tree.clear()
        
        data = self.pw._get_pw_dump()
        devices = {d['id']: d for d in self.pw.get_devices()}
        
        for item in data:
            if item.get('type') != 'PipeWire:Interface:Node':
                continue
            
            info = item.get('info', {})
            props = info.get('props', {})
            media_class = props.get('media.class', '')
            
            if media_class not in ('Stream/Output/Audio', 'Stream/Input/Audio'):
                continue
            
            node_name = props.get('node.name', '')
            if 'monitor' in node_name.lower() or node_name in ('pipewire', 'WirePlumber'):
                continue
            
            app_name = props.get('application.name') or props.get('node.name', 'Inconnu')
            node_id = item.get('id', 0)
            state = info.get('state', 'idle')
            
            params = info.get('params', {})
            fmt = (params.get('Format', [{}]) or [{}])[0]
            rate = fmt.get('rate', '?')
            fmt_str = fmt.get('format', '?')
            
            rate_str = f"{rate} Hz" if rate != '?' else '?'
            
            if 'Output' in media_class:
                type_str = self.i18n.tr('sortie')
            else:
                type_str = self.i18n.tr('entree')
            
            linked_device = ''
            if 'Output' in media_class:
                sink_id = props.get('node.target') or props.get('target.object')
                if sink_id:
                    try:
                        sink_id_int = int(sink_id)
                        if sink_id_int in devices:
                            linked_device = devices[sink_id_int].get('description', sink_id)
                    except (ValueError, TypeError):
                        pass
                if not linked_device:
                    for link in data:
                        if link.get('type') == 'PipeWire:Interface:Link':
                            link_info = link.get('info', {})
                            if link_info.get('output-node-id') == node_id:
                                sink_id = link_info.get('input-node-id')
                                if sink_id and sink_id in devices:
                                    linked_device = devices[sink_id].get('description', str(sink_id))
                                    break
            else:
                source_id = props.get('node.target') or props.get('target.object')
                if source_id:
                    try:
                        source_id_int = int(source_id)
                        if source_id_int in devices:
                            linked_device = devices[source_id_int].get('description', source_id)
                    except (ValueError, TypeError):
                        pass
                if not linked_device:
                    for link in data:
                        if link.get('type') == 'PipeWire:Interface:Link':
                            link_info = link.get('info', {})
                            if link_info.get('input-node-id') == node_id:
                                source_id = link_info.get('output-node-id')
                                if source_id and source_id in devices:
                                    linked_device = devices[source_id].get('description', str(source_id))
                                    break
            
            app_item = QTreeWidgetItem([
                str(node_id),
                app_name,
                type_str,
                state,
                rate_str,
                str(fmt_str) if fmt_str != '?' else '?',
                linked_device if linked_device else '?'
            ])
            
            app_item.setData(0, Qt.ItemDataRole.UserRole, node_id)
            app_item.setData(1, Qt.ItemDataRole.UserRole, app_name)
            
            if state == 'running':
                app_item.setForeground(3, Qt.GlobalColor.green)
            elif state == 'idle':
                app_item.setForeground(3, Qt.GlobalColor.gray)
            else:
                app_item.setForeground(3, Qt.GlobalColor.orange)
            
            self.apps_tree.addTopLevelItem(app_item)
            
            if selected_id is not None and node_id == selected_id:
                self.apps_tree.setCurrentItem(app_item)
    
    def _show_app_context_menu(self, pos):
        item = self.apps_tree.itemAt(pos)
        if not item:
            return
        
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        app_name = item.data(1, Qt.ItemDataRole.UserRole)
        
        if not node_id:
            return
        
        menu = QMenu(self)
        kill_action = QAction(f"🗑 {self.i18n.tr('supprimer_noeud')} : {app_name}", self)
        kill_action.triggered.connect(lambda: self._kill_app_node(node_id, app_name))
        menu.addAction(kill_action)
        menu.exec(self.apps_tree.viewport().mapToGlobal(pos))
    
    def _kill_app_node(self, node_id, app_name):
        reply = QMessageBox.warning(
            self,
            self.i18n.tr('confirmation'),
            f"Supprimer le flux de « {app_name} » (ID {node_id}) ?\n\n"
            "Cette action détruira le nœud PipeWire de l'application.\n"
            "L'application devra peut-être être redémarrée pour recréer son flux.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            ok, err = self.pw.destroy_node(node_id)
            if ok:
                self.pw.invalidate_cache()
                self._refresh_devices_table()
                QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('node_destroyed'))
            else:
                QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('node_destroy_error') + f"\n{err}")
    
    def _set_default_device(self):
        item = self.devices_tree.currentItem()
        if not item:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('select_device'))
            return
        
        dev_id = int(item.text(0).replace(" ★", ""))
        if self.pw.set_default_device(dev_id):
            self._refresh_devices_table()
            QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('device_default_changed'))
        else:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('device_default_error'))
    
    def _on_destroy_state_changed(self, state):
        checked = state == 2
        if checked:
            reply = QMessageBox.warning(
                self,
                "⚠️ " + self.i18n.tr('mode_suppression'),
                self.i18n.tr('destroy_warning'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.destroy_cb.blockSignals(True)
                self.destroy_cb.setChecked(False)
                self.destroy_cb.blockSignals(False)
                return
        self.destroy_btn.setVisible(checked)
    
    def _destroy_node(self):
        item = self.devices_tree.currentItem()
        if not item:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('select_device'))
            return
        
        dev_id = int(item.text(0).replace(" ★", ""))
        dev_name = item.text(1)
        
        reply = QMessageBox.question(
            self,
            self.i18n.tr('confirmation'),
            self.i18n.tr('node_destroy_warning') + f"\n\n{dev_name} (ID {dev_id})"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            ok, err = self.pw.destroy_node(dev_id)
            if ok:
                self.pw.invalidate_cache()
                self._refresh_devices_table()
                QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('node_destroyed'))
            else:
                QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('node_destroy_error') + f"\n{err}")
    
    def _sort_devices(self, devices):
        return sorted(
            devices,
            key=lambda d: (
                0 if 'pci' in d.get('name', '') else 1,
                2 if 'aes67' in d.get('name', '').lower() or 'rtp' in d.get('name', '').lower() else 1,
                d.get('description', '')
            )
        )
    
    def _sync_device_layout(self, devices, direction):
        layout = self.output_layout if direction == 'sortie' else self.input_layout
        rows = self.device_rows if direction == 'sortie' else self.input_rows
        
        old_rows = dict(rows)
        
        while layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        rows.clear()
        
        for device in devices:
            name = device['name']
            if name in old_rows:
                row = old_rows[name]
                row.device = device
                row.card.device = device
            else:
                row = DeviceVolumeRow(device, self.pw) if direction == 'sortie' else DeviceInputRow(device, self.pw)
                row.volume_changed.connect(lambda did, vol: self.pw.set_volume(did, vol))
                self.logger.debug(f"Nouveau périphérique ajouté: {name}")
            rows[name] = row
            layout.addWidget(row)
        
        layout.addStretch()
    
    def refresh_devices(self):
        sinks = self._sort_devices(
            [d for d in self.pw.get_devices() if d['type'] == 'sortie']
        )
        self._sync_device_layout(sinks, 'sortie')
        
        if sinks:
            active = self._find_active_sink(sinks)
            self.selected_output = active
            for device in sinks:
                self.device_rows[device['name']].set_selected(device.get('id') == active.get('id'))
        
        sources = self._sort_devices(
            [d for d in self.pw.get_devices() if d['type'] == 'entrée']
        )
        self._sync_device_layout(sources, 'entrée')
        
        if sources:
            active = self._find_active_source(sources)
            self.selected_input = active
            for device in sources:
                self.input_rows[device['name']].set_selected(device.get('id') == active.get('id'))
        
        current_names = set(self.device_rows.keys()) | set(self.input_rows.keys())
        if current_names != self._prev_device_names:
            self.logger.info(f"Périphériques changés: {len(self._prev_device_names)} -> {len(current_names)}")
            self._prev_device_names = current_names
    
    def _find_active_sink(self, sinks):
        active = next((d for d in sinks if d.get('is_default')), None)
        if active:
            return active
        real_sinks = [d for d in sinks if 'aes67' not in d.get('name', '').lower()]
        aes67_sinks = [d for d in sinks if 'aes67' in d.get('name', '').lower()]
        active = next((d for d in real_sinks if d.get('state') == 'running'), None)
        if active:
            return active
        if aes67_sinks:
            active = next((d for d in aes67_sinks if d.get('state') == 'running'), None)
            if active:
                return active
            return aes67_sinks[0]
        return real_sinks[0] if real_sinks else None
    
    def _find_active_source(self, sources):
        active = next((d for d in sources if d.get('is_default')), None)
        if active:
            return active
        active = next((d for d in sources if d.get('state') == 'running'), None)
        if active:
            return active
        return sources[0] if sources else None
    
    def _update(self):
        if any(row.slider.is_dragging() for row in self.device_rows.values()):
            return
        if any(row.slider.is_dragging() for row in self.input_rows.values()):
            return
        if any(row.slider.is_dragging() for row in self.stream_rows.values()):
            return
        
        self.pw.invalidate_cache()
        data = self.pw._get_pw_dump()
        
        devices = self.pw.get_devices()
        current_names = {d['name'] for d in devices}
        
        if current_names != self._prev_device_names:
            self.refresh_devices()
        else:
            self._refresh_devices_silent(data)
        
        self._update_streams(data)
        
        # Si la page Périphériques est visible, rafraîchir les tableaux
        if self.sub_stack.currentIndex() == 2:
            self._refresh_devices_table()
    
    def _refresh_devices_silent(self, data):
        sinks = self._sort_devices(
            [d for d in self.pw.get_devices() if d['type'] == 'sortie']
        )
        if sinks:
            active = self._find_active_sink(sinks)
            current = len(self.device_rows)
            if current != len(sinks):
                self._sync_device_layout(sinks, 'sortie')
            if active and active.get('is_default'):
                if not self.selected_output or active.get('id') != self.selected_output.get('id'):
                    self.selected_output = active
            for device in sinks:
                name = device['name']
                if name in self.device_rows:
                    row = self.device_rows[name]
                    row.device = device
                    row.card.device = device
                    row.set_selected(device.get('id') == self.selected_output.get('id'))
                    row.card.name_lbl.setText(device.get('description', '')[:40])
                    vol = self.pw.get_volume(device['id'])
                    if vol is not None:
                        row.update_volume(vol)
                    for item in data:
                        props = item.get('info', {}).get('props', {})
                        if props.get('node.name') == device['name']:
                            params = item.get('info', {}).get('params', {})
                            fmt = (params.get('Format', [{}]) or [{}])[0]
                            rate = fmt.get('rate', '?')
                            fmt_str = fmt.get('format', '?')
                            bits = props.get('alsa.resolution_bits')
                            row.update_info(rate, fmt_str, bits)
                            break
        
        sources = self._sort_devices(
            [d for d in self.pw.get_devices() if d['type'] == 'entrée']
        )
        if sources:
            active = self._find_active_source(sources)
            current = len(self.input_rows)
            if current != len(sources):
                self._sync_device_layout(sources, 'entrée')
            if active and active.get('is_default'):
                if not self.selected_input or active.get('id') != self.selected_input.get('id'):
                    self.selected_input = active
            for device in sources:
                name = device['name']
                if name in self.input_rows:
                    row = self.input_rows[name]
                    row.device = device
                    row.card.device = device
                    row.set_selected(device.get('id') == self.selected_input.get('id'))
                    row.card.name_lbl.setText(device.get('description', '')[:40])
                    vol = self.pw.get_volume(device['id'])
                    if vol is not None:
                        row.update_volume(vol)
                    for item in data:
                        props = item.get('info', {}).get('props', {})
                        if props.get('node.name') == device['name']:
                            params = item.get('info', {}).get('params', {})
                            fmt = (params.get('Format', [{}]) or [{}])[0]
                            rate = fmt.get('rate', '?')
                            fmt_str = fmt.get('format', '?')
                            bits = props.get('alsa.resolution_bits')
                            row.update_info(rate, fmt_str, bits)
                            break
    
    def _update_streams(self, data):
        current_ids = set()
        for item in data:
            info = item.get('info', {})
            props = info.get('props', {})
            if props.get('media.class') != 'Stream/Output/Audio' or info.get('state') != 'running':
                continue
            app = props.get('application.name') or props.get('node.name', '')
            if app in ('pipewire', 'WirePlumber', 'pw-dump'):
                continue
            
            sid = str(item.get('id', 0))
            current_ids.add(sid)
            enum = (info.get('params', {}).get('EnumFormat', [{}]) or [{}])[0]
            rate = enum.get('rate', '?')
            
            if sid in self.stream_rows:
                row = self.stream_rows[sid]
                row.stream = {'id': int(sid), 'name': app, 'rate': str(rate) if rate != '?' else '?'}
                row.name_lbl.setText(app[:22])
                rate_text = "?"
                if rate != '?' and rate is not None:
                    r = int(rate)
                    rate_text = f"{r/1000:.1f}k" if r >= 1000 else f"{r} Hz"
                row.rate_lbl.setText(rate_text)
            else:
                row = StreamRow({'id': int(sid), 'name': app, 'rate': str(rate) if rate != '?' else '?'})
                row.volume_changed.connect(self._on_stream_volume)
                self.stream_rows[sid] = row
                self.streams_layout.addWidget(row)
                self.logger.debug(f"Nouveau flux audio: {app}")
        
        for sid in list(self.stream_rows):
            if sid not in current_ids:
                self.logger.debug(f"Flux audio supprimé: {self.stream_rows[sid].stream.get('name', 'inconnu')}")
                self.stream_rows[sid].deleteLater()
                del self.stream_rows[sid]
        
        for row in self.stream_rows.values():
            if not row.slider.is_dragging():
                vol = self.pw.get_stream_volume(int(row.stream.get('id', 0)))
                if vol is not None:
                    row.update_volume(vol)
        
        self.empty_lbl.setVisible(not self.stream_rows)
        self.streams_scroll.setVisible(bool(self.stream_rows))
    
    def _on_stream_volume(self, device_id, volume):
        self.pw.set_volume(device_id, volume)
    
    def load_current(self):
        self.refresh_devices()
        self._refresh_devices_table()
    
    def refresh_language(self):
        self.sub_buttons[0].setText(self.i18n.tr('sorties'))
        self.sub_buttons[1].setText(self.i18n.tr('entrees'))
        self.sub_buttons[2].setText(self.i18n.tr('devices'))
        self.output_gb.setTitle(self.i18n.tr('peripheriques_sortie'))
        self.input_gb.setTitle(self.i18n.tr('peripheriques_entree'))
        self.flux_gb.setTitle(self.i18n.tr('flux_actifs'))
        self.empty_lbl.setText(self.i18n.tr('aucun_flux'))
        self.devices_gb.setTitle(self.i18n.tr('peripheriques_detectes'))
        self.apps_gb.setTitle(self.i18n.tr('applications'))
        self.set_default_btn.setText(self.i18n.tr('definir_defaut'))
        self.destroy_cb.setText(self.i18n.tr('mode_suppression'))
        self.destroy_btn.setText(self.i18n.tr('supprimer_noeud'))
    
    def shutdown(self):
        self._save_header_state()
        self.timer.stop()
