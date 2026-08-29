#!/usr/bin/env python3
# ui/frequency_tab.py
"""Onglet de configuration des fréquences"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QMessageBox, QListWidget,
    QListWidgetItem, QInputDialog
)
from PyQt6.QtCore import Qt
from .i18n import I18n
from .logger import Logger

class FrequencyTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Fréquences autorisées
        self.config_gb = QGroupBox(self.i18n.tr('frequences_autorisees'))
        config_layout = QVBoxLayout()
        
        config_layout.addWidget(QLabel(self.i18n.tr('frequencies_description')))
        
        self.rates_list = QListWidget()
        self.rates_list.setMaximumHeight(150)
        self._populate_rates_list()
        config_layout.addWidget(self.rates_list)
        
        btn_layout = QHBoxLayout()
        
        self.add_rate_btn = QPushButton(self.i18n.tr('ajouter'))
        self.add_rate_btn.clicked.connect(self._add_rate)
        btn_layout.addWidget(self.add_rate_btn)
        
        self.remove_rate_btn = QPushButton(self.i18n.tr('supprimer'))
        self.remove_rate_btn.clicked.connect(self._remove_rate)
        btn_layout.addWidget(self.remove_rate_btn)
        
        config_layout.addLayout(btn_layout)
        
        save_layout = QHBoxLayout()
        self.save_config_btn = QPushButton(self.i18n.tr('enregistrer'))
        self.save_config_btn.clicked.connect(self._save_config)
        save_layout.addWidget(self.save_config_btn)
        
        self.remove_config_btn = QPushButton(self.i18n.tr('supprimer_config'))
        self.remove_config_btn.clicked.connect(self._remove_config)
        save_layout.addWidget(self.remove_config_btn)
        
        config_layout.addLayout(save_layout)
        self.config_gb.setLayout(config_layout)
        layout.addWidget(self.config_gb)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _populate_rates_list(self):
        self.rates_list.clear()
        rates = self.pw.read_allowed_rates()
        if rates:
            for r in rates:
                item = QListWidgetItem(f"{r} Hz")
                item.setData(Qt.ItemDataRole.UserRole, r)
                self.rates_list.addItem(item)
        else:
            for r in [44100, 48000, 88200, 96000, 176400, 192000]:
                item = QListWidgetItem(f"{r} Hz")
                item.setData(Qt.ItemDataRole.UserRole, r)
                self.rates_list.addItem(item)
    
    def _add_rate(self):
        all_rates = ['44100', '48000', '88200', '96000', '176400', '192000']
        current = {self.rates_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.rates_list.count())}
        available = [r for r in all_rates if int(r) not in current]
        
        if not available:
            QMessageBox.information(self, self.i18n.tr('info'), self.i18n.tr('all_frequencies_added'))
            return
        
        rate, ok = QInputDialog.getItem(self, self.i18n.tr('add_frequency'), self.i18n.tr('frequency'), available, 0, False)
        if ok and rate:
            item = QListWidgetItem(f"{rate} Hz")
            item.setData(Qt.ItemDataRole.UserRole, int(rate))
            self.rates_list.addItem(item)
    
    def _remove_rate(self):
        item = self.rates_list.currentItem()
        if item:
            self.rates_list.takeItem(self.rates_list.row(item))
        else:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('select_frequency'))
    
    def _save_config(self):
        rates = [self.rates_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.rates_list.count())]
        if not rates:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('list_empty'))
            return
        
        if self.pw.write_allowed_rates(rates):
            self.logger.info(f"Fréquences sauvegardées: {rates}")
            
            # Demander si l'utilisateur veut redémarrer
            reply = QMessageBox.question(
                self,
                self.i18n.tr('success'),
                self.i18n.tr('config_saved_restart'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                ok, msg = self.pw.restart_services()
                if ok:
                    QMessageBox.information(self, self.i18n.tr('success'), msg)
                else:
                    QMessageBox.warning(self, self.i18n.tr('error_title'), msg)
        else:
            self.logger.error("Échec écriture fréquences")
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('config_error'))
    
    def _remove_config(self):
        reply = QMessageBox.question(
            self,
            self.i18n.tr('confirmation'),
            self.i18n.tr('remove_config_confirm'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.pw.remove_config():
                self._populate_rates_list()
                QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('config_removed'))
            else:
                QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('config_error'))
    
    def refresh_language(self):
        self.config_gb.setTitle(self.i18n.tr('frequences_autorisees'))
        self.add_rate_btn.setText(self.i18n.tr('ajouter'))
        self.remove_rate_btn.setText(self.i18n.tr('supprimer'))
        self.save_config_btn.setText(self.i18n.tr('enregistrer'))
        self.remove_config_btn.setText(self.i18n.tr('supprimer_config'))
