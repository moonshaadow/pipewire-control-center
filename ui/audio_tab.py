#!/usr/bin/env python3
"""Onglet Audio : sorties, entrées et périphériques"""
import os
import subprocess
import re
import time
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QStackedWidget, QButtonGroup,
    QPushButton, QLabel, QMessageBox, QFrame, QScrollArea,
    QSlider, QCheckBox, QStyle, QTreeWidget, QTreeWidgetItem, QMenu,
    QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings, QPoint
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction, QColor
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


# --- Vignette périphérique pour flux (petite) ---
class StreamDeviceBadge(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(56, 56)
        
        self.setToolTip(device.get('description', ''))
        
        layout = QVBoxLayout()
        layout.setSpacing(1)
        layout.setContentsMargins(3, 3, 3, 3)
        
        icon_path = get_device_icon_path(device)
        self.icon_lbl = QLabel()
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_lbl.setPixmap(pixmap)
        else:
            self.icon_lbl.setText("🔊")
            self.icon_lbl.setFont(QFont("Monospace", 10))
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        self.name_lbl = QLabel(device.get('description', '')[:12])
        self.name_lbl.setFont(QFont("Sans", 6, QFont.Weight.Medium))
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setWordWrap(True)
        layout.addWidget(self.name_lbl)
        
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


# --- Dialog de sélection de périphérique ---
class DevicePickerDialog(QDialog):
    """Dialog pour choisir un périphérique de sortie pour un flux"""
    
    def __init__(self, stream_name, current_device, available_devices, parent=None):
        super().__init__(parent)
        self.i18n = I18n.instance()
        self.selected_device = None
        self.setWindowTitle(f"Router : {stream_name}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        title_lbl = QLabel(f"Choisir un périphérique de sortie pour :\n{stream_name}")
        title_lbl.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)
        
        layout.addSpacing(10)
        
        # Grille de vignettes
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(8)
        
        # Vignette "Défaut" en premier
        default_badge = StreamDeviceBadge({
            'name': '',
            'description': self.i18n.tr('default_device'),
            'type': 'sortie'
        })
        default_badge.setFixedSize(70, 70)
        default_badge.setToolTip(self.i18n.tr('default_device_tooltip'))
        
        # Le flux suit le défaut si current_device est vide ou None
        follows_default = (current_device == '' or current_device is None)
        
        # Style de la vignette "Défaut"
        if follows_default:
            default_badge.setStyleSheet("""
                QFrame {
                    background-color: #2E7D32;
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: #388E3C;
                    border: 2px solid #66BB6A;
                }
                QFrame QLabel {
                    color: white;
                }
            """)
        else:
            default_badge.setStyleSheet("""
                QFrame {
                    background-color: #2a2a2a;
                    border: 1px solid #444444;
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: #333333;
                    border: 1px solid #666666;
                }
                QFrame QLabel {
                    color: #cccccc;
                }
            """)
        default_badge.clicked.connect(self._on_default_selected)
        grid_layout.addWidget(default_badge)
        
        # Trait vertical séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("QFrame { color: #555; background-color: #555; }")
        separator.setFixedWidth(1)
        separator.setFixedHeight(70)
        grid_layout.addWidget(separator)
        
        # Vignettes des périphériques
        for device in available_devices:
            is_current = device['name'] == current_device
            
            badge = StreamDeviceBadge(device)
            badge.setFixedSize(70, 70)
            
            if is_current:
                badge.setStyleSheet("""
                    QFrame {
                        background-color: #1565C0;
                        border: 2px solid #1E88E5;
                        border-radius: 8px;
                    }
                    QFrame:hover {
                        background-color: #1976D2;
                        border: 2px solid #42A5F5;
                    }
                    QFrame QLabel {
                        color: white;
                    }
                """)
            else:
                badge.setStyleSheet("""
                    QFrame {
                        background-color: #2a2a2a;
                        border: 1px solid #444444;
                        border-radius: 8px;
                    }
                    QFrame:hover {
                        background-color: #333333;
                        border: 1px solid #666666;
                    }
                    QFrame QLabel {
                        color: #cccccc;
                    }
                """)
            
            badge.clicked.connect(lambda checked=False, d=device: self._on_device_selected(d))
            grid_layout.addWidget(badge)
        
        grid_layout.addStretch()
        layout.addLayout(grid_layout)
        
        layout.addSpacing(10)
        
        # Bouton annuler
        cancel_btn = QPushButton(self.i18n.tr('cancel'))
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
    
    def _on_device_selected(self, device):
        self.selected_device = device
        self.accept()
    
    def _on_default_selected(self):
        self.selected_device = {'name': '', 'description': self.i18n.tr('default_device')}
        self.accept()


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
        if self.pw.set_default_device(device['id']):
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.i18n.tr('default_output_changed').format(description=device.get('description', '')),
                    3000
                )
    
    def _on_slider_moved(self, value):
        self.vol_label.setText(f"{value}%")
        if self.slider.is_dragging():
            self.volume_changed.emit(self.device['id'], value / 100.0)
    
    def _on_release(self):
        self.logger.debug(f"Slider relâché: {self.device['name']} -> {self.slider.value()}%")
        self.volume_changed.emit(self.device['id'], self.slider.value() / 100.0)
        main_window = self.window()
        if main_window and hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(
                self.i18n.tr('volume_changed_status').format(
                    name=self.device.get('description', self.device.get('name', '')),
                    value=self.slider.value()
                ),
                2000
            )
    
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
        if self.pw.set_default_device(device['id']):
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.i18n.tr('default_input_changed').format(description=device.get('description', '')),
                    3000
                )
    
    def _on_slider_moved(self, value):
        self.vol_label.setText(f"{value}%")
        if self.slider.is_dragging():
            self.volume_changed.emit(self.device['id'], value / 100.0)
    
    def _on_release(self):
        self.logger.debug(f"Slider relâché: {self.device['name']} -> {self.slider.value()}%")
        self.volume_changed.emit(self.device['id'], self.slider.value() / 100.0)
        main_window = self.window()
        if main_window and hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(
                self.i18n.tr('volume_changed_status').format(
                    name=self.device.get('description', self.device.get('name', '')),
                    value=self.slider.value()
                ),
                2000
            )
    
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
    device_change_requested = pyqtSignal(dict)
    
    def __init__(self, stream, pw):
        super().__init__()
        self.stream = stream
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self.device_badge = None
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: #2a2a2a; border-radius: 4px; margin: 1px 0;")
        self.setMinimumHeight(64)
        self.setMaximumHeight(64)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(24, 24)
        self._update_icon()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        self.name_lbl = QLabel(stream.get('name', '')[:30])
        self.name_lbl.setFont(QFont("Monospace", 8))
        self.name_lbl.setStyleSheet("color: #aaaaaa;")
        text_layout.addWidget(self.name_lbl)
        
        self.meta_lbl = QLabel("")
        self.meta_lbl.setFont(QFont("Monospace", 7))
        self.meta_lbl.setStyleSheet("color: #666;")
        self.meta_lbl.setVisible(False)
        text_layout.addWidget(self.meta_lbl)
        
        layout.addLayout(text_layout, 1)
        
        self.rate_lbl = QLabel("?")
        self.rate_lbl.setFont(QFont("Monospace", 7))
        self.rate_lbl.setStyleSheet("color: #888888;")
        self.rate_lbl.setFixedWidth(55)
        self.rate_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rate_lbl)
        
        self.slider = ClickSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.setMinimumWidth(50)
        self.slider.setMaximumWidth(300)
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
        self._update_metadata()
    
    def _update_icon(self):
        icon_name = self.stream.get('icon_name', '')
        if icon_name:
            icon = QIcon.fromTheme(icon_name)
            if not icon.isNull():
                self.icon_lbl.setPixmap(icon.pixmap(24, 24))
                return
            icon = QIcon.fromTheme(icon_name.lower())
            if not icon.isNull():
                self.icon_lbl.setPixmap(icon.pixmap(24, 24))
                return
        self.icon_lbl.setText("🎵")
        self.icon_lbl.setFont(QFont("Monospace", 12))
    
    def _update_metadata(self):
        media_title = self.stream.get('media_title', '')
        media_name = self.stream.get('media_name', '')
        media_artist = self.stream.get('media_artist', '')
        
        meta_parts = []
        if media_title:
            meta_parts.append(media_title)
        elif media_name:
            meta_parts.append(media_name)
        if media_artist:
            meta_parts.append(media_artist)
        
        if meta_parts:
            self.meta_lbl.setText(" · ".join(meta_parts)[:60])
            self.meta_lbl.setVisible(True)
        else:
            self.meta_lbl.setVisible(False)
    
    def set_device_badge(self, device):
        """Ajoute ou met à jour la vignette du périphérique"""
        if self.device_badge is None:
            self.device_badge = StreamDeviceBadge(device)
            self.device_badge.setFixedSize(56, 56)
            self.device_badge.clicked.connect(lambda: self.device_change_requested.emit(self.stream))
            self.layout().addWidget(self.device_badge)
        else:
            self.device_badge.device = device
            self.device_badge.setToolTip(device.get('description', ''))
            self.device_badge.name_lbl.setText(device.get('description', '')[:12])
            icon_path = get_device_icon_path(device)
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                pixmap = pixmap.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.device_badge.icon_lbl.setPixmap(pixmap)
    
    def update_stream(self, stream):
        self.stream = stream
        self.name_lbl.setText(stream.get('name', '')[:30])
        self._update_icon()
        
        rate = stream.get('rate', '?')
        if rate != '?' and rate is not None:
            r = int(rate)
            self.rate_lbl.setText(f"{r/1000:.1f}k" if r >= 1000 else f"{r} Hz")
        
        self._update_metadata()
    
    def _on_slider_moved(self, value):
        self.vol_lbl.setText(f"{value}%")
        if self.slider.is_dragging():
            self.volume_changed.emit(self.stream.get('id', 0), value / 100.0)
    
    def _on_release(self):
        self.logger.debug(f"Slider flux relâché: {self.stream.get('name', 'inconnu')} -> {self.slider.value()}%")
        self.volume_changed.emit(self.stream.get('id', 0), self.slider.value() / 100.0)
        main_window = self.window()
        if main_window and hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(
                self.i18n.tr('volume_changed_status').format(
                    name=self.stream.get('name', ''),
                    value=self.slider.value()
                ),
                2000
            )
    
    def update_volume(self, volume):
        if not self.slider.is_dragging():
            self.slider.blockSignals(True)
            self.slider.setValue(int(volume * 100))
            self.vol_lbl.setText(f"{int(volume * 100)}%")
            self.slider.blockSignals(False)


# --- Onglet Audio principal ---
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
        self._mpris_cache = {}
        self._mpris_cache_time = 0
        self._desktop_names_cache = {}
        self._init_ui()
        self.refresh_devices()
        self._refresh_devices_table()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(200)
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
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
        
        # Page Périphériques
        self.devices_page = QWidget()
        devices_page_layout = QVBoxLayout()
        devices_page_layout.setSpacing(8)
        devices_page_layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        devices_btn_layout = QHBoxLayout()
        self.set_default_btn = QPushButton(self.i18n.tr('definir_defaut'))
        self.set_default_btn.clicked.connect(self._set_default_device)
        devices_btn_layout.addWidget(self.set_default_btn)
        devices_btn_layout.addStretch()
        devices_layout.addLayout(devices_btn_layout)
        
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
        
        # Flux actifs
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
        self.streams_scroll.setMaximumHeight(300)
        self.streams_scroll.setStyleSheet("QScrollArea { border: none; }")
        flux_layout.addWidget(self.streams_scroll)
        
        self.empty_lbl = QLabel(self.i18n.tr('aucun_flux'))
        self.empty_lbl.setFont(QFont("Monospace", 9))
        self.empty_lbl.setStyleSheet("color: #555;")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.hide()
        flux_layout.addWidget(self.empty_lbl)
        
        self.flux_gb.setLayout(flux_layout)
        layout.addWidget(self.flux_gb)
        
        self.sub_buttons[0].setChecked(True)
        self.sub_btn_group.idClicked.connect(self._on_sub_nav)
        
        self._restore_header_state()
        
        self.setLayout(layout)
    
    def _on_sub_nav(self, idx):
        self.sub_stack.setCurrentIndex(idx)
        if idx == 2:
            self._refresh_devices_table()
            self.flux_gb.setVisible(False)
        else:
            self.flux_gb.setVisible(True)
    
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
    
    def _get_stream_target(self, stream_id):
        """Récupère le target.object du flux via pw-metadata"""
        try:
            result = subprocess.run(
                ['pw-metadata', str(stream_id), 'target.object'],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                match = re.search(r"value:\s*'([^']*)'", result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            self.logger.error(f"Erreur lecture target.object: {e}")
        return ''
    
    def _get_mpris_players(self):
        now = time.time()
        if now - self._mpris_cache_time < 5:
            return list(self._mpris_cache.keys())
        
        try:
            result = subprocess.run(
                ['dbus-send', '--session', '--print-reply',
                 '--dest=org.freedesktop.DBus',
                 '/org/freedesktop/DBus',
                 'org.freedesktop.DBus.ListNames'],
                capture_output=True, text=True, timeout=3
            )
            players = []
            for line in result.stdout.split('\n'):
                if 'org.mpris.MediaPlayer2' in line:
                    match = re.search(r'org\.mpris\.MediaPlayer2\.([^"]+)"', line)
                    if match:
                        players.append(match.group(1).strip())
            
            self._mpris_cache = {p: True for p in players}
            self._mpris_cache_time = now
            return players
        except Exception:
            return list(self._mpris_cache.keys())
    
    def _get_mpris_metadata(self, player_name):
        try:
            result = subprocess.run(
                ['dbus-send', '--session', '--print-reply',
                 f'--dest=org.mpris.MediaPlayer2.{player_name}',
                 '/org/mpris/MediaPlayer2',
                 'org.freedesktop.DBus.Properties.Get',
                 'string:org.mpris.MediaPlayer2.Player',
                 'string:Metadata'],
                capture_output=True, text=True, timeout=3
            )
            
            metadata = {}
            title_match = re.search(r'xesam:title.*?string\s+"([^"]+)"', result.stdout, re.DOTALL)
            artist_match = re.search(r'xesam:artist.*?string\s+"([^"]+)"', result.stdout, re.DOTALL)
            album_match = re.search(r'xesam:album.*?string\s+"([^"]+)"', result.stdout, re.DOTALL)
            
            if title_match:
                metadata['media_title'] = title_match.group(1)
            if artist_match:
                metadata['media_artist'] = artist_match.group(1)
            if album_match:
                metadata['media_album'] = album_match.group(1)
            
            return metadata
        except Exception:
            return {}
    
    def _get_mpris_metadata_for_app(self, app_name):
        app_lower = app_name.lower()
        
        players = self._get_mpris_players()
        
        for player in players:
            player_lower = player.lower()
            if app_lower in player_lower or player_lower in app_lower:
                return self._get_mpris_metadata(player)
        
        if '.' in app_lower:
            binary_guess = app_lower.split('.')[-1]
            for player in players:
                player_lower = player.lower()
                if binary_guess in player_lower or player_lower in binary_guess:
                    return self._get_mpris_metadata(player)
        
        cleaned = re.sub(r'[\[\]]', ' ', app_lower)
        cleaned = re.sub(r'\bpipewire\b|\balsa\b|\bplayback\b|\bcapture\b', '', cleaned)
        cleaned = cleaned.strip()
        
        if cleaned and cleaned != app_lower:
            for player in players:
                if cleaned in player.lower():
                    return self._get_mpris_metadata(player)
        
        return {}
    
    def _get_desktop_name(self, binary):
        if binary in self._desktop_names_cache:
            return self._desktop_names_cache[binary]
        
        try:
            desktop_dirs = [
                '/usr/share/applications',
                os.path.expanduser('~/.local/share/applications'),
                '/var/lib/flatpak/exports/share/applications',
                os.path.expanduser('~/.local/share/flatpak/exports/share/applications')
            ]
            
            for d in desktop_dirs:
                if not os.path.exists(d):
                    continue
                for f in os.listdir(d):
                    if f.endswith('.desktop'):
                        filepath = os.path.join(d, f)
                        try:
                            with open(filepath, 'r') as fh:
                                content = fh.read()
                                if re.search(r'^Exec=.*\b' + re.escape(binary) + r'\b', content, re.MULTILINE):
                                    name_match = re.search(r'^Name=([^\n]+)', content, re.MULTILINE)
                                    if name_match:
                                        result = name_match.group(1).strip()
                                        self._desktop_names_cache[binary] = result
                                        return result
                        except Exception:
                            continue
        except Exception:
            pass
        
        self._desktop_names_cache[binary] = None
        return None
    
    def _refresh_devices_table(self):
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
        
        self._refresh_apps_table()
    
    def _refresh_apps_table(self):
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
            binary = props.get('application.process.binary', '')
            node_id = item.get('id', 0)
            state = info.get('state', 'idle')
            
            if binary:
                desktop_name = self._get_desktop_name(binary)
                if desktop_name:
                    app_name = desktop_name
            
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
                app_item.setForeground(3, QColor("#ff9800"))
            
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
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.i18n.tr('node_destroyed_status').format(id=node_id),
                        3000
                    )
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
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.i18n.tr('default_device_changed_status').format(description=item.text(1)),
                    3000
                )
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
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.i18n.tr('node_destroyed_status').format(id=dev_id),
                        3000
                    )
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
        output_devices = {d['name']: d for d in self.pw.get_devices() if d['type'] == 'sortie'}
        
        for item in data:
            info = item.get('info', {})
            props = info.get('props', {})
            media_class = props.get('media.class', '')
            
            if media_class not in ('Stream/Output/Audio', 'Stream/Input/Audio') or info.get('state') != 'running':
                continue
            
            app = props.get('application.name') or props.get('node.name', '')
            binary = props.get('application.process.binary', '')
            if app in ('pipewire', 'WirePlumber', 'pw-dump'):
                continue
            
            sid = str(item.get('id', 0))
            current_ids.add(sid)
            
            enum = (info.get('params', {}).get('EnumFormat', [{}]) or [{}])[0]
            rate = enum.get('rate', '?')
            
            display_name = app
            if binary:
                desktop_name = self._get_desktop_name(binary)
                if desktop_name:
                    display_name = desktop_name
                elif 'pipewire' in app.lower() or 'alsa' in app.lower():
                    display_name = binary.capitalize()
            
            stream_data = {
                'id': int(sid),
                'name': display_name,
                'rate': str(rate) if rate != '?' else '?',
                'icon_name': binary if binary else app,
                'media_title': props.get('media.title', ''),
                'media_name': props.get('media.name', ''),
                'media_artist': props.get('media.artist', ''),
                'binary': binary
            }
            
            if not stream_data['media_title'] and not stream_data['media_artist']:
                search_names = []
                if binary:
                    search_names.append(binary)
                search_names.append(app)
                
                for search_name in search_names:
                    mpris_meta = self._get_mpris_metadata_for_app(search_name)
                    if mpris_meta:
                        stream_data.update(mpris_meta)
                        break
            
            # Récupérer le target.object du flux
            linked_device_name = self._get_stream_target(sid)
            stream_data['follows_default'] = (not linked_device_name or linked_device_name == '')
            
            # Trouver le périphérique lié réel
            if linked_device_name:
                for dev in output_devices.values():
                    if dev['name'] == linked_device_name:
                        stream_data['device'] = dev
                        break
                else:
                    for dev in output_devices.values():
                        if dev['description'] == linked_device_name:
                            stream_data['device'] = dev
                            break
            
            if 'device' not in stream_data:
                default_sink = next((d for d in output_devices.values() if d.get('is_default')), None)
                if default_sink:
                    stream_data['device'] = default_sink
                else:
                    for link in data:
                        if link.get('type') == 'PipeWire:Interface:Link':
                            link_info = link.get('info', {})
                            if link_info.get('output-node-id') == int(sid):
                                sink_id = link_info.get('input-node-id')
                                for dev in output_devices.values():
                                    if dev['id'] == sink_id:
                                        stream_data['device'] = dev
                                        break
                                break
            
            if sid in self.stream_rows:
                row = self.stream_rows[sid]
                row.update_stream(stream_data)
                if 'device' in stream_data:
                    row.set_device_badge(stream_data['device'])
            else:
                row = StreamRow(stream_data, self.pw)
                row.volume_changed.connect(self._on_stream_volume)
                row.device_change_requested.connect(self._on_device_change_requested)
                self.stream_rows[sid] = row
                self.streams_layout.addWidget(row)
                if 'device' in stream_data:
                    row.set_device_badge(stream_data['device'])
                self.logger.debug(f"Nouveau flux audio: {display_name} (binaire: {binary})")
        
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
    
    def _on_device_change_requested(self, stream_data):
        """Affiche le dialog de sélection de périphérique"""
        available_devices = [d for d in self.pw.get_devices() if d['type'] == 'sortie']
        
        current_device = self._get_stream_target(stream_data['id'])
        
        dialog = DevicePickerDialog(
            stream_data.get('name', 'Flux'),
            current_device,
            available_devices,
            self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_device:
            if dialog.selected_device['name'] == '':
                self._route_stream_to_default(stream_data['id'])
            else:
                self._route_stream_now(stream_data['id'], dialog.selected_device['name'])
    
    def _route_stream_now(self, stream_id, device_name):
        """Route immédiatement un flux vers un périphérique"""
        try:
            result = subprocess.run(
                ['pw-metadata', str(stream_id), 'target.object', device_name],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                self.logger.info(f"Flux {stream_id} routé vers {device_name}")
                self.pw.invalidate_cache()
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    stream_name = self.stream_rows.get(str(stream_id), None)
                    stream_display = stream_name.stream.get('name', str(stream_id)) if stream_name else str(stream_id)
                    main_window.statusBar().showMessage(
                        self.i18n.tr('stream_routed').format(stream=stream_display, device=device_name),
                        3000
                    )
            else:
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    stream_name = self.stream_rows.get(str(stream_id), None)
                    stream_display = stream_name.stream.get('name', str(stream_id)) if stream_name else str(stream_id)
                    main_window.statusBar().showMessage(
                        self.i18n.tr('stream_route_error').format(stream=stream_display),
                        3000
                    )
        except Exception as e:
            self.logger.error(f"Erreur routing flux: {e}")
    
    def _route_stream_to_default(self, stream_id):
        """Retour au périphérique par défaut"""
        try:
            result = subprocess.run(
                ['pw-metadata', str(stream_id), 'target.object', ''],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                self.logger.info(f"Flux {stream_id} retour au défaut")
                self.pw.invalidate_cache()
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    stream_name = self.stream_rows.get(str(stream_id), None)
                    stream_display = stream_name.stream.get('name', str(stream_id)) if stream_name else str(stream_id)
                    main_window.statusBar().showMessage(
                        self.i18n.tr('stream_routed_default').format(stream=stream_display),
                        3000
                    )
        except Exception as e:
            self.logger.error(f"Erreur retour défaut: {e}")
    
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
