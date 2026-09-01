#!/usr/bin/env python3
"""Ligne périphérique unifiée (sortie ou entrée)"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from .widgets import DeviceCard, ClickSlider
from ..i18n import I18n
from ..logger import Logger


class DeviceRow(QWidget):
    """Ligne périphérique unifiée avec volume et infos"""
    volume_changed = pyqtSignal(int, float)
    
    def __init__(self, device, pw, is_input=False):
        super().__init__()
        self.device = device
        self.pw = pw
        self.is_input = is_input
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
        
        if not self.is_input:
            boost_layout = QHBoxLayout()
            boost_layout.addStretch()
            self.boost_cb = QCheckBox(self.i18n.tr('boost_150'))
            self.boost_cb.setFont(QFont("Monospace", 7))
            self.boost_cb.setStyleSheet("color: #888;")
            self.boost_cb.toggled.connect(self._on_boost)
            boost_layout.addWidget(self.boost_cb)
            vol_layout.addLayout(boost_layout)
        else:
            boost_spacer = QWidget()
            boost_spacer.setFixedHeight(20)
            vol_layout.addWidget(boost_spacer)
        
        layout.addLayout(vol_layout, 1)
        self.setLayout(layout)
    
    def _on_card_clicked(self, device):
        self.logger.info(f"Clic sur carte périphérique {'entrée' if self.is_input else 'sortie'}: {device.get('name', 'inconnu')}")
        if self.pw.set_default_device(device['id']):
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                if self.is_input:
                    msg = self.i18n.tr('default_input_changed').format(description=device.get('description', ''))
                else:
                    msg = self.i18n.tr('default_output_changed').format(description=device.get('description', ''))
                main_window.statusBar().showMessage(msg, 3000)
    
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
