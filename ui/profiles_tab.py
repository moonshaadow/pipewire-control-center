#!/usr/bin/env python3
# ui/profiles_tab.py
"""Onglet de gestion des profils"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QInputDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from .i18n import I18n
from .logger import Logger

class ProfilesTab(QWidget):
    profile_loaded = pyqtSignal()
    
    def __init__(self, pw, config_mgr):
        super().__init__()
        self.pw = pw
        self.config_mgr = config_mgr
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self._init_ui()
        self._refresh_list()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton(self.i18n.tr('sauvegarder_etat'))
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)
        
        self.load_btn = QPushButton(self.i18n.tr('charger'))
        self.load_btn.clicked.connect(self._load)
        btn_layout.addWidget(self.load_btn)
        
        self.delete_btn = QPushButton(self.i18n.tr('delete'))
        self.delete_btn.clicked.connect(self._delete)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _refresh_list(self):
        self.list_widget.clear()
        self.list_widget.addItems(self.config_mgr.list_profiles())
    
    def _save(self):
        name, ok = QInputDialog.getText(self, self.i18n.tr('save_profile'), self.i18n.tr('profile_name'))
        if ok and name:
            existing = self.config_mgr.load(name)
            if existing is not None:
                reply = QMessageBox.question(
                    self, self.i18n.tr('confirmation'),
                    f"Le profil '{name}' existe déjà.\nVoulez-vous l'écraser ?"
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            config = {
                'rate': self.pw.get_rate(),
                'quantum': self.pw.get_quantum(),
                'min_quantum': self.pw.get_min_quantum(),
                'max_quantum': self.pw.get_max_quantum()
            }
            if self.config_mgr.save(name, config):
                self._refresh_list()
                QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('profile_saved').format(name=name))
            else:
                QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('config_error'))
    
    def _load(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('select_profile'))
            return
        
        config = self.config_mgr.load(item.text())
        if config:
            if 'rate' in config:
                self.pw.set_rate(config['rate'])
            self.pw.set_quantum(config.get('quantum', 1024))
            self.pw.set_min_quantum(config.get('min_quantum', 32))
            self.pw.set_max_quantum(config.get('max_quantum', 8192))
            self.profile_loaded.emit()
            QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('profile_loaded_msg'))
        else:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('select_profile'))
    
    def _delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        
        reply = QMessageBox.question(
            self, self.i18n.tr('confirmation'),
            self.i18n.tr('confirm_delete_profile').format(item.text()),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config_mgr.delete(item.text())
            self._refresh_list()
    
    def refresh_language(self):
        self.save_btn.setText(self.i18n.tr('sauvegarder_etat'))
        self.load_btn.setText(self.i18n.tr('charger'))
        self.delete_btn.setText(self.i18n.tr('delete'))
