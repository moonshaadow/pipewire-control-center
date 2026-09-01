#!/usr/bin/env python3
"""Widgets réutilisables pour l'onglet Audio"""
import os
from PyQt6.QtWidgets import QSlider, QLabel, QFrame, QVBoxLayout, QStyle
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from ..icon_utils import get_device_icon_path
from ..i18n import I18n
from ..logger import Logger


class ClickSlider(QSlider):
    """Slider avec clic à la volée"""
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


class DeviceCard(QFrame):
    """Carte périphérique cliquable"""
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


class StreamDeviceBadge(QFrame):
    """Vignette périphérique pour flux (petite)"""
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
