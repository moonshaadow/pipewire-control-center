#!/usr/bin/env python3
# ui/profiles_tab.py
"""Profiles management tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QInputDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from .logger import Logger

class ProfilesTab(QWidget):
    profile_loaded = pyqtSignal()
    
    def __init__(self, pw, config_mgr):
        super().__init__()
        self.pw = pw
        self.config_mgr = config_mgr
        self.logger = Logger.instance()
        self._init_ui()
        self._refresh_list()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton(self.tr("Save state"))
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)
        
        self.load_btn = QPushButton(self.tr("Load"))
        self.load_btn.clicked.connect(self._load)
        btn_layout.addWidget(self.load_btn)
        
        self.delete_btn = QPushButton(self.tr("Delete"))
        self.delete_btn.clicked.connect(self._delete)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _refresh_list(self):
        self.list_widget.clear()
        self.list_widget.addItems(self.config_mgr.list_profiles())
    
    def _save(self):
        name, ok = QInputDialog.getText(self, self.tr("Save profile"), self.tr("Profile name"))
        if ok and name:
            existing = self.config_mgr.load(name)
            if existing is not None:
                reply = QMessageBox.question(
                    self, self.tr("Confirmation"),
                    self.tr("Profile \"{name}\" already exists.\nDo you want to overwrite it?").format(name=name)
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
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.tr("Profile \"{name}\" saved").format(name=name),
                        3000
                    )
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Configuration error"))
    
    def _load(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Please select a profile"))
            return
        
        config = self.config_mgr.load(item.text())
        if config:
            if 'rate' in config:
                self.pw.set_rate(config['rate'])
            self.pw.set_quantum(config.get('quantum', 1024))
            self.pw.set_min_quantum(config.get('min_quantum', 32))
            self.pw.set_max_quantum(config.get('max_quantum', 8192))
            self.profile_loaded.emit()
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.tr("Profile \"{name}\" loaded").format(name=item.text()),
                    3000
                )
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Please select a profile"))
    
    def _delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        
        reply = QMessageBox.question(
            self, self.tr("Confirmation"),
            self.tr("Delete profile \"{name}\"?").format(name=item.text()),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            profile_name = item.text()
            self.config_mgr.delete(profile_name)
            self._refresh_list()
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.tr("Profile \"{name}\" deleted").format(name=profile_name),
                    3000
                )
    
    def refresh_language(self):
        self.save_btn.setText(self.tr("Save state"))
        self.load_btn.setText(self.tr("Load"))
        self.delete_btn.setText(self.tr("Delete"))