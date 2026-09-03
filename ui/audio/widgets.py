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
        self._colors = None
        self.is_selected = is_selected
        self._style_cache = None
        self._loaded_icon_path = None
        self.setProperty("selected", is_selected)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(150, 85)
        self.setMaximumSize(200, 95)
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10, 8, 10, 8)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.icon_lbl)
        
        self.name_lbl = QLabel(device.get('description', 'Inconnu')[:40])
        self.name_lbl.setFont(QFont("Monospace", 7))
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setMaximumWidth(180)
        self.name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.name_lbl)
        
        if device.get('state') == 'running':
            badge = QLabel("● " + self.i18n.tr('active'))
            badge.setFont(QFont("Monospace", 6))
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet("color: #4CAF50; background: transparent;")
            badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(badge)
        
        self.setLayout(layout)
        self._load_icon()
        self._apply_style()
    
    def _load_icon(self):
        """Charge l'icône selon le thème actuel (avec cache)"""
        icon_path = get_device_icon_path(self.device, self._colors)
        if self._loaded_icon_path == icon_path:
            return
        self._loaded_icon_path = icon_path
        
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_lbl.setPixmap(pixmap)
        else:
            self.icon_lbl.setText("🔊")
            self.icon_lbl.setFont(QFont("Monospace", 20))
    
    def _apply_style(self):
        """Applique le style selon l'état sélectionné (avec cache)"""
        c = self._colors if self._colors else {}
        cache_key = (self.is_selected, str(c))
        if self._style_cache == cache_key:
            return
        self._style_cache = cache_key
        
        if self.is_selected:
            bg = c.get('device_card_selected_bg', c.get('btn_checked', '#1565C0'))
            border = c.get('device_card_selected_border', c.get('btn_hover', '#1E88E5'))
            text = c.get('device_card_selected_text', c.get('btn_text_checked', '#ffffff'))
            border_width = '2px'
        else:
            bg = c.get('device_card_normal_bg', c.get('btn_bg', '#2a2a2a'))
            border = c.get('device_card_normal_border', c.get('border', '#444444'))
            text = c.get('device_card_normal_text', c.get('btn_text', '#cccccc'))
            border_width = '1px'
        
        # Pas de changement au survol pour la carte sélectionnée
        if self.is_selected:
            hover_style = ""
        else:
            hover_style = f"""
            DeviceCard:hover {{
                background-color: {c.get('btn_hover', '#333333')};
                border: 1px solid {c.get('btn_text_hover', '#666666')};
            }}
            """
        
        self.setStyleSheet(f"""
            DeviceCard {{
                background-color: {bg};
                border: {border_width} solid {border};
                border-radius: 8px;
            }}
            {hover_style}
            DeviceCard QLabel {{
                color: {text};
                background: transparent;
                border: none;
            }}
        """)
    
    def set_theme_colors(self, colors):
        """Applique les couleurs du thème et recharge l'icône"""
        self._colors = colors
        self._load_icon()
        self._apply_style()
    
    def set_selected(self, selected):
        """Change l'état sélectionné et réapplique le style"""
        self.is_selected = selected
        self.setProperty("selected", selected)
        self._apply_style()
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
        self._colors = None
        self._style_cache = None
        self._loaded_icon_path = None
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(56, 56)
        
        self.setToolTip(device.get('description', ''))
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(3, 3, 3, 3)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.icon_lbl)
        
        self.name_lbl = QLabel(device.get('description', '')[:12])
        self.name_lbl.setFont(QFont("Sans", 6, QFont.Weight.Medium))
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.name_lbl)
        
        self.setLayout(layout)
        self._load_icon()
    
    def _load_icon(self):
        """Charge l'icône selon le thème actuel (avec cache)"""
        icon_path = get_device_icon_path(self.device, self._colors)
        if self._loaded_icon_path == icon_path:
            return
        self._loaded_icon_path = icon_path
        
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_lbl.setPixmap(pixmap)
        else:
            self.icon_lbl.setText("🔊")
            self.icon_lbl.setFont(QFont("Monospace", 10))
    
    def set_theme_colors(self, colors):
        """Applique les couleurs du thème et recharge l'icône (avec cache)"""
        cache_key = str(colors)
        if self._style_cache == cache_key:
            return
        self._style_cache = cache_key
        
        self._colors = colors
        c = colors
        self.setStyleSheet(f"""
            StreamDeviceBadge {{
                background-color: {c.get('device_card_normal_bg', '#2a2a2a')};
                border: 1px solid {c.get('device_card_normal_border', '#444444')};
                border-radius: 8px;
            }}
            StreamDeviceBadge:hover {{
                background-color: {c.get('btn_hover', '#333333')};
                border: 1px solid {c.get('btn_text_hover', '#666666')};
            }}
            StreamDeviceBadge QLabel {{
                color: {c.get('device_card_normal_text', '#cccccc')};
                background: transparent;
                border: none;
            }}
        """)
        self._load_icon()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
