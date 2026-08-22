#!/usr/bin/env python3
# ui/profiles_tab.py
"""Onglet de gestion des profils"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QInputDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

class ProfilesTab(QWidget):
    profile_loaded = pyqtSignal()
    
    def __init__(self, pw, config_mgr):
        super().__init__()
        self.pw = pw
        self.config_mgr = config_mgr
        self._init_ui()
        self._refresh_list()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Sauvegarder l'état actuel")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        load_btn = QPushButton("📂 Charger")
        load_btn.clicked.connect(self._load)
        btn_layout.addWidget(load_btn)
        
        delete_btn = QPushButton("🗑 Supprimer")
        delete_btn.clicked.connect(self._delete)
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _refresh_list(self):
        self.list_widget.clear()
        self.list_widget.addItems(self.config_mgr.list_profiles())
    
    def _save(self):
        name, ok = QInputDialog.getText(self, "Sauvegarder", "Nom du profil :")
        if ok and name:
            config = {
                'rate': self.pw.get_rate(),
                'quantum': self.pw.get_quantum(),
                'min_quantum': self.pw.get_min_quantum(),
                'max_quantum': self.pw.get_max_quantum()
            }
            if self.config_mgr.save(name, config):
                self._refresh_list()
                QMessageBox.information(self, "Succès", f"Profil '{name}' sauvegardé")
            else:
                QMessageBox.warning(self, "Erreur", "Impossible de sauvegarder")
    
    def _load(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un profil")
            return
        
        config = self.config_mgr.load(item.text())
        if config:
            self.pw.set_rate(config.get('rate', 48000))
            self.pw.set_quantum(config.get('quantum', 1024))
            self.pw.set_min_quantum(config.get('min_quantum', 32))
            self.pw.set_max_quantum(config.get('max_quantum', 8192))
            self.profile_loaded.emit()
        else:
            QMessageBox.warning(self, "Erreur", "Impossible de charger le profil")
    
    def _delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        
        reply = QMessageBox.question(
            self, "Confirmation",
            f"Supprimer le profil '{item.text()}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config_mgr.delete(item.text())
            self._refresh_list()
