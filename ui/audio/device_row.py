#!/usr/bin/env python3
"""Unified device row (output or input)"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from .widgets import DeviceCard, ClickSlider
from ..logger import Logger


class DeviceRow(QWidget):
    """Unified device row with volume and info"""
    volume_changed = pyqtSignal(int, float)
    
    def __init__(self, device, pw, is_input=False):
        super().__init__()
        self.device = device
        self.pw = pw
        self.is_input = is_input
        self.logger = Logger.instance()
        self._init_ui()
        
        # Load initial volume
        self._load_initial_volume()
    
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
        self.slider.setValue(0)  # Initial value 0, will be updated
        self.slider.setMinimumWidth(100)
        self.slider.setMaximumWidth(800)
        self.slider.valueChanged.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_release)
        vol_top.addWidget(self.slider, 1)
        
        self.vol_label = QLabel("0%")
        self.vol_label.setFont(QFont("Monospace", 9))
        self.vol_label.setFixedWidth(40)
        self.vol_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vol_top.addWidget(self.vol_label)
        
        vol_layout.addLayout(vol_top)
        
        info_layout = QHBoxLayout()
        info_layout.setSpacing(0)
        info_layout.setContentsMargins(30, 0, 0, 0)
        self.info_lbl = QLabel("")
        self.info_lbl.setFont(QFont("Monospace", 8))
        info_layout.addWidget(self.info_lbl)
        info_layout.addStretch()
        vol_layout.addLayout(info_layout)
        
        if not self.is_input:
            boost_layout = QHBoxLayout()
            boost_layout.addStretch()
            self.boost_cb = QCheckBox(self.tr("Boost 150%"))
            self.boost_cb.setFont(QFont("Monospace", 7))
            self.boost_cb.toggled.connect(self._on_boost)
            boost_layout.addWidget(self.boost_cb)
            vol_layout.addLayout(boost_layout)
        else:
            boost_spacer = QWidget()
            boost_spacer.setFixedHeight(20)
            vol_layout.addWidget(boost_spacer)
        
        layout.addLayout(vol_layout, 1)
        self.setLayout(layout)
    
    def _load_initial_volume(self):
        """Load the device's initial volume"""
        try:
            vol = self.pw.get_volume(self.device['id'])
            if vol is not None:
                self.update_volume(vol)
        except Exception:
            pass
    
    def set_theme_colors(self, colors):
        """Apply theme colors"""
        self.card.set_theme_colors(colors)
        self.vol_label.setStyleSheet(f"color: {colors.get('btn_text_checked', '#ffffff')};")
        self.info_lbl.setStyleSheet(f"color: {colors.get('btn_text', '#aaaaaa')};")
        if hasattr(self, 'boost_cb'):
            self.boost_cb.setStyleSheet(f"color: {colors.get('btn_text', '#888888')};")
    
    def _on_card_clicked(self, device):
        self.logger.info(f"Click on {'input' if self.is_input else 'output'} device card: {device.get('name', 'unknown')}")
        if self.pw.set_default_device(device['id']):
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                if self.is_input:
                    msg = self.tr("Default input set to {description}").format(description=device.get('description', ''))
                else:
                    msg = self.tr("Default output set to {description}").format(description=device.get('description', ''))
                main_window.statusBar().showMessage(msg, 3000)
    
    def _on_slider_moved(self, value):
        self.vol_label.setText(f"{value}%")
        if self.slider.is_dragging():
            self.volume_changed.emit(self.device['id'], value / 100.0)
    
    def _on_release(self):
        self.logger.debug(f"Slider released: {self.device['name']} -> {self.slider.value()}%")
        self.volume_changed.emit(self.device['id'], self.slider.value() / 100.0)
        main_window = self.window()
        if main_window and hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(
                self.tr("Volume of {name} set to {value}%").format(
                    name=self.device.get('description', self.device.get('name', '')),
                    value=self.slider.value()
                ),
                2000
            )
    
    def _on_boost(self, checked):
        self.logger.debug(f"Boost {self.device['name']}: {'enabled' if checked else 'disabled'}")
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