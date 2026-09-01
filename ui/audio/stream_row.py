#!/usr/bin/env python3
"""Ligne flux audio avec métadonnées"""
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap
import os
from .widgets import ClickSlider, StreamDeviceBadge
from ..icon_utils import get_device_icon_path
from ..i18n import I18n
from ..logger import Logger


class StreamRow(QFrame):
    """Ligne flux audio avec icône, nom, métadonnées, volume et vignette périphérique"""
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
