#!/usr/bin/env python3
"""Onglet de gestion des périphériques"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from .icon_utils import get_device_icon_path

class DevicesTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self._init_ui()
        self.refresh()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Périphériques audio détectés :"))
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "ID", "Description", "Type", "État", "Fréquence", "Format", "Gamme"
        ])
        self.tree.setColumnWidth(0, 50)
        self.tree.setColumnWidth(1, 220)
        self.tree.setColumnWidth(6, 140)
        layout.addWidget(self.tree)
        
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(self.refresh_btn)
        
        self.set_default_btn = QPushButton("Définir par défaut")
        self.set_default_btn.clicked.connect(self._set_default)
        btn_layout.addWidget(self.set_default_btn)
        
        layout.addLayout(btn_layout)
        
        self.destroy_cb = QCheckBox("Mode suppression de nœud")
        self.destroy_cb.setStyleSheet("color: #ef5350; font-weight: bold;")
        self.destroy_cb.stateChanged.connect(self._on_destroy_state_changed)
        layout.addWidget(self.destroy_cb)
        
        self.destroy_btn = QPushButton("🗑 Supprimer le nœud sélectionné")
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
            
            # Icône dans la colonne Description
            icon_path = get_device_icon_path(dev)
            if icon_path and __import__('os').path.exists(icon_path):
                item.setIcon(1, QIcon(icon_path))
            
            if dev['is_default']:
                font = item.font(0)
                font.setBold(True)
                for i in range(7):
                    item.setFont(i, font)
                # Étoile dans la colonne ID
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
            QMessageBox.warning(self, "Erreur", "Sélectionnez un périphérique")
            return
        
        dev_id = int(item.text(0).replace(" ★", ""))
        if self.pw.set_default_device(dev_id):
            self.refresh()
            QMessageBox.information(self, "Succès", "Périphérique par défaut changé")
        else:
            QMessageBox.warning(self, "Erreur", "Impossible de changer le périphérique")
    
    def _on_destroy_state_changed(self, state):
        checked = state == 2  # Qt.CheckState.Checked.value
        if checked:
            reply = QMessageBox.warning(
                self,
                "⚠️ Mode suppression de nœud",
                "Ce mode permet de supprimer temporairement un nœud PipeWire.\n\n"
                "Le nœud sera recréé au prochain redémarrage de PipeWire\n"
                "ou lors d'un changement de profil.\n\n"
                "⚠️ Si vous supprimez un périphérique actif, la lecture audio\n"
                "sera interrompue et basculera sur un autre périphérique.\n\n"
                "Continuer ?",
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
            QMessageBox.warning(self, "Erreur", "Sélectionnez un périphérique à supprimer")
            return
        
        dev_id = int(item.text(0).replace(" ★", ""))
        dev_name = item.text(1)
        
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Supprimer le nœud « {dev_name} » (ID {dev_id}) ?\n\n"
            "Cette action est temporaire."
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            ok, err = self.pw.destroy_node(dev_id)
            if ok:
                self.pw.invalidate_cache()
                self.refresh()
                QMessageBox.information(self, "Succès", f"Nœud {dev_id} supprimé.")
            else:
                QMessageBox.warning(self, "Erreur", f"Échec : {err}")
