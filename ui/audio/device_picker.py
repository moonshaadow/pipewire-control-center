#!/usr/bin/env python3
"""Dialog de sélection de périphérique pour un flux"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .widgets import StreamDeviceBadge
from ..i18n import I18n


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
                    border: none;
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: #388E3C;
                    border: none;
                }
                QFrame QLabel {
                    color: white;
                    background: transparent;
                }
            """)
        else:
            default_badge.setStyleSheet("""
                QFrame {
                    background-color: #2a2a2a;
                    border: none;
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: #333333;
                    border: none;
                }
                QFrame QLabel {
                    color: #cccccc;
                    background: transparent;
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
                        border: none;
                        border-radius: 8px;
                    }
                    QFrame:hover {
                        background-color: #1976D2;
                        border: none;
                    }
                    QFrame QLabel {
                        color: white;
                        background: transparent;
                    }
                """)
            else:
                badge.setStyleSheet("""
                    QFrame {
                        background-color: #2a2a2a;
                        border: none;
                        border-radius: 8px;
                    }
                    QFrame:hover {
                        background-color: #333333;
                        border: none;
                    }
                    QFrame QLabel {
                        color: #cccccc;
                        background: transparent;
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
