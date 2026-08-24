#!/usr/bin/env python3
"""Onglet de gestion des périphériques"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from .icon_utils import get_device_icon_path
from .i18n import I18n

class DevicesTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self._init_ui()
        self.refresh()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        self.title_lbl = QLabel(self.i18n.tr('peripheriques_detectes'))
        layout.addWidget(self.title_lbl)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            self.i18n.tr('id'), self.i18n.tr('description'), self.i18n.tr('type'),
            self.i18n.tr('state'), self.i18n.tr('rate'), self.i18n.tr('format'),
            self.i18n.tr('range')
        ])
        self.tree.setColumnWidth(0, 50)
        self.tree.setColumnWidth(1, 220)
        self.tree.setColumnWidth(6, 140)
        layout.addWidget(self.tree)
        
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton(self.i18n.tr('rafraichir'))
        self.refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(self.refresh_btn)
        
        self.set_default_btn = QPushButton(self.i18n.tr('definir_defaut'))
        self.set_default_btn.clicked.connect(self._set_default)
        btn_layout.addWidget(self.set_default_btn)
        
        layout.addLayout(btn_layout)
        
        self.destroy_cb = QCheckBox(self.i18n.tr('mode_suppression'))
        self.destroy_cb.setStyleSheet("color: #ef5350; font-weight: bold;")
        self.destroy_cb.stateChanged.connect(self._on_destroy_state_changed)
        layout.addWidget(self.destroy_cb)
        
        self.destroy_btn = QPushButton(self.i18n.tr('supprimer_noeud'))
        self.destroy_btn.setStyleSheet("QPushButton { color: #ef5350; font-weight: bold; }")
        self.destroy_btn.clicked.connect(self._destroy_node)
        self.destroy_btn.setVisible(False)
        layout.addWidget(self.destroy_btn)
        
        self.setLayout(layout)
    
    def refresh(self):
        self.pw.invalidate_cache()
        self.tree.clear()
        devices = self.pw.get_devices()
        
        for dev in devices:
            rate_str = f"{dev['rate']} Hz" if dev['rate'] != '?' else '?'
            
            if dev['rates_min'] and dev['rates_max']:
                range_str = f"{dev['rates_min']}-{dev['rates_max']} Hz"
            elif dev['rates_default']:
                range_str = f"{dev['rates_default']} Hz (fixe)"
            else:
                range_str = "?"
            
            fmt_str = str(dev['format']) if dev['format'] != '?' else '?'
            if dev.get('bits'):
                fmt_str += f" / {dev['bits']} bits"
            
            item = QTreeWidgetItem([
                str(dev['id']),
                dev['description'],
                dev['type'],
                dev['state'],
                rate_str,
                fmt_str,
                range_str
            ])
            
            icon_path = get_device_icon_path(dev)
            if icon_path and os.path.exists(icon_path):
                item.setIcon(1, QIcon(icon_path))
            
            if dev['is_default']:
                font = item.font(0)
                font.setBold(True)
                for i in range(7):
                    item.setFont(i, font)
                item.setText(0, item.text(0) + " ★")
            
            if dev['state'] == 'running':
                item.setForeground(3, Qt.GlobalColor.green)
            elif dev['state'] == 'idle':
                item.setForeground(3, Qt.GlobalColor.gray)
            
            self.tree.addTopLevelItem(item)
    
    def load_config(self, config: dict):
        pass
    
    def _set_default(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('select_device'))
            return
        
        dev_id = int(item.text(0).replace(" ★", ""))
        if self.pw.set_default_device(dev_id):
            self.refresh()
            QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('device_default_changed'))
        else:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('device_default_error'))
    
    def _on_destroy_state_changed(self, state):
        checked = state == 2
        if checked:
            reply = QMessageBox.warning(
                self,
                "⚠️ " + self.i18n.tr('mode_suppression'),
                self.i18n.tr('destroy_warning'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.destroy_cb.blockSignals(True)
                self.destroy_cb.setChecked(False)
                self.destroy_cb.blockSignals(False)
                return
        self.destroy_btn.setVisible(checked)
    
    def _destroy_node(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('select_device'))
            return
        
        dev_id = int(item.text(0).replace(" ★", ""))
        dev_name = item.text(1)
        
        reply = QMessageBox.question(
            self,
            self.i18n.tr('confirmation'),
            self.i18n.tr('node_destroy_warning') + f"\n\n{dev_name} (ID {dev_id})"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            ok, err = self.pw.destroy_node(dev_id)
            if ok:
                self.pw.invalidate_cache()
                self.refresh()
                QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('node_destroyed'))
            else:
                QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('node_destroy_error') + f"\n{err}")
    
    def refresh_language(self):
        self.title_lbl.setText(self.i18n.tr('peripheriques_detectes'))
        self.tree.setHeaderLabels([
            self.i18n.tr('id'), self.i18n.tr('description'), self.i18n.tr('type'),
            self.i18n.tr('state'), self.i18n.tr('rate'), self.i18n.tr('format'),
            self.i18n.tr('range')
        ])
        self.refresh_btn.setText(self.i18n.tr('rafraichir'))
        self.set_default_btn.setText(self.i18n.tr('definir_defaut'))
        self.destroy_cb.setText(self.i18n.tr('mode_suppression'))
        self.destroy_btn.setText(self.i18n.tr('supprimer_noeud'))
