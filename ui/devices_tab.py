#!/usr/bin/env python3
"""Onglet de gestion des périphériques et des nœuds d'application"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QLabel, QCheckBox,
    QGroupBox, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction
from .icon_utils import get_device_icon_path
from .i18n import I18n

class DevicesTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self._init_ui()
        self.refresh()
        
        # Timer de rafraîchissement automatique
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)  # 2 secondes
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # --- Tableau des périphériques ---
        self.devices_gb = QGroupBox(self.i18n.tr('peripheriques_detectes'))
        devices_layout = QVBoxLayout()
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            self.i18n.tr('id'), self.i18n.tr('description'), self.i18n.tr('type'),
            self.i18n.tr('state'), self.i18n.tr('rate'), self.i18n.tr('format'),
            self.i18n.tr('range')
        ])
        self.tree.setColumnWidth(0, 50)
        self.tree.setColumnWidth(1, 220)
        self.tree.setColumnWidth(6, 140)
        devices_layout.addWidget(self.tree)
        
        # Boutons d'action
        btn_layout = QHBoxLayout()
        
        self.set_default_btn = QPushButton(self.i18n.tr('definir_defaut'))
        self.set_default_btn.clicked.connect(self._set_default)
        btn_layout.addWidget(self.set_default_btn)
        
        btn_layout.addStretch()
        devices_layout.addLayout(btn_layout)
        
        # Mode suppression
        self.destroy_cb = QCheckBox(self.i18n.tr('mode_suppression'))
        self.destroy_cb.setStyleSheet("color: #ef5350; font-weight: bold;")
        self.destroy_cb.stateChanged.connect(self._on_destroy_state_changed)
        devices_layout.addWidget(self.destroy_cb)
        
        self.destroy_btn = QPushButton(self.i18n.tr('supprimer_noeud'))
        self.destroy_btn.setStyleSheet("QPushButton { color: #ef5350; font-weight: bold; }")
        self.destroy_btn.clicked.connect(self._destroy_node)
        self.destroy_btn.setVisible(False)
        devices_layout.addWidget(self.destroy_btn)
        
        self.devices_gb.setLayout(devices_layout)
        layout.addWidget(self.devices_gb)
        
        # --- Tableau des applications ---
        self.apps_gb = QGroupBox(self.i18n.tr('applications'))
        apps_layout = QVBoxLayout()
        
        self.apps_tree = QTreeWidget()
        self.apps_tree.setHeaderLabels([
            self.i18n.tr('id'), self.i18n.tr('application'), self.i18n.tr('type'),
            self.i18n.tr('state'), self.i18n.tr('rate'), self.i18n.tr('format'),
            self.i18n.tr('linked_device')
        ])
        self.apps_tree.setColumnWidth(0, 50)
        self.apps_tree.setColumnWidth(1, 180)
        self.apps_tree.setColumnWidth(6, 200)
        self.apps_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.apps_tree.customContextMenuRequested.connect(self._show_app_context_menu)
        apps_layout.addWidget(self.apps_tree)
        
        self.apps_gb.setLayout(apps_layout)
        layout.addWidget(self.apps_gb)
        
        self.setLayout(layout)
    
    def showEvent(self, event):
        """Démarre le timer quand l'onglet devient visible"""
        super().showEvent(event)
        self.timer.start(2000)
        self.refresh()
    
    def hideEvent(self, event):
        """Arrête le timer quand l'onglet n'est plus visible"""
        super().hideEvent(event)
        self.timer.stop()
    
    def refresh(self):
        self.pw.invalidate_cache()
        self._refresh_devices()
        self._refresh_apps()
    
    def _refresh_devices(self):
        # Sauvegarder la sélection actuelle
        selected_item = self.tree.currentItem()
        selected_id = None
        if selected_item:
            selected_text = selected_item.text(0).replace(" ★", "")
            try:
                selected_id = int(selected_text)
            except ValueError:
                selected_id = None
        
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
            
            # Restaurer la sélection
            if selected_id is not None and dev['id'] == selected_id:
                self.tree.setCurrentItem(item)
    
    def _refresh_apps(self):
        """Rafraîchit le tableau des nœuds d'application"""
        # Sauvegarder la sélection actuelle
        selected_item = self.apps_tree.currentItem()
        selected_id = None
        if selected_item:
            selected_id = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        self.apps_tree.clear()
        
        data = self.pw._get_pw_dump()
        devices = {d['id']: d for d in self.pw.get_devices()}
        
        for item in data:
            if item.get('type') != 'PipeWire:Interface:Node':
                continue
            
            info = item.get('info', {})
            props = info.get('props', {})
            media_class = props.get('media.class', '')
            
            if media_class not in ('Stream/Output/Audio', 'Stream/Input/Audio'):
                continue
            
            node_name = props.get('node.name', '')
            if 'monitor' in node_name.lower() or node_name in ('pipewire', 'WirePlumber'):
                continue
            
            app_name = props.get('application.name') or props.get('node.name', 'Inconnu')
            node_id = item.get('id', 0)
            state = info.get('state', 'idle')
            
            params = info.get('params', {})
            fmt = (params.get('Format', [{}]) or [{}])[0]
            rate = fmt.get('rate', '?')
            fmt_str = fmt.get('format', '?')
            
            rate_str = f"{rate} Hz" if rate != '?' else '?'
            
            if 'Output' in media_class:
                type_str = self.i18n.tr('sortie')
            else:
                type_str = self.i18n.tr('entree')
            
            linked_device = ''
            if 'Output' in media_class:
                sink_id = props.get('node.target') or props.get('target.object')
                if sink_id:
                    try:
                        sink_id_int = int(sink_id)
                        if sink_id_int in devices:
                            linked_device = devices[sink_id_int].get('description', sink_id)
                    except (ValueError, TypeError):
                        pass
                if not linked_device:
                    for link in data:
                        if link.get('type') == 'PipeWire:Interface:Link':
                            link_info = link.get('info', {})
                            if link_info.get('output-node-id') == node_id:
                                sink_id = link_info.get('input-node-id')
                                if sink_id and sink_id in devices:
                                    linked_device = devices[sink_id].get('description', str(sink_id))
                                    break
            else:
                source_id = props.get('node.target') or props.get('target.object')
                if source_id:
                    try:
                        source_id_int = int(source_id)
                        if source_id_int in devices:
                            linked_device = devices[source_id_int].get('description', source_id)
                    except (ValueError, TypeError):
                        pass
                if not linked_device:
                    for link in data:
                        if link.get('type') == 'PipeWire:Interface:Link':
                            link_info = link.get('info', {})
                            if link_info.get('input-node-id') == node_id:
                                source_id = link_info.get('output-node-id')
                                if source_id and source_id in devices:
                                    linked_device = devices[source_id].get('description', str(source_id))
                                    break
            
            app_item = QTreeWidgetItem([
                str(node_id),
                app_name,
                type_str,
                state,
                rate_str,
                str(fmt_str) if fmt_str != '?' else '?',
                linked_device if linked_device else '?'
            ])
            
            app_item.setData(0, Qt.ItemDataRole.UserRole, node_id)
            app_item.setData(1, Qt.ItemDataRole.UserRole, app_name)
            
            if state == 'running':
                app_item.setForeground(3, Qt.GlobalColor.green)
            elif state == 'idle':
                app_item.setForeground(3, Qt.GlobalColor.gray)
            else:
                app_item.setForeground(3, Qt.GlobalColor.orange)
            
            self.apps_tree.addTopLevelItem(app_item)
            
            # Restaurer la sélection
            if selected_id is not None and node_id == selected_id:
                self.apps_tree.setCurrentItem(app_item)
    
    def _show_app_context_menu(self, pos):
        """Affiche le menu contextuel pour les nœuds d'application"""
        item = self.apps_tree.itemAt(pos)
        if not item:
            return
        
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        app_name = item.data(1, Qt.ItemDataRole.UserRole)
        
        if not node_id:
            return
        
        menu = QMenu(self)
        kill_action = QAction(f"🗑 {self.i18n.tr('supprimer_noeud')} : {app_name}", self)
        kill_action.triggered.connect(lambda: self._kill_app_node(node_id, app_name))
        menu.addAction(kill_action)
        menu.exec(self.apps_tree.viewport().mapToGlobal(pos))
    
    def _kill_app_node(self, node_id, app_name):
        """Supprime le flux d'une application après confirmation"""
        reply = QMessageBox.warning(
            self,
            self.i18n.tr('confirmation'),
            f"Supprimer le flux de « {app_name} » (ID {node_id}) ?\n\n"
            "Cette action détruira le nœud PipeWire de l'application.\n"
            "L'application devra peut-être être redémarrée pour recréer son flux.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            ok, err = self.pw.destroy_node(node_id)
            if ok:
                self.pw.invalidate_cache()
                self.refresh()
                QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('node_destroyed'))
            else:
                QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('node_destroy_error') + f"\n{err}")
    
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
        self.devices_gb.setTitle(self.i18n.tr('peripheriques_detectes'))
        self.apps_gb.setTitle(self.i18n.tr('applications'))
        self.tree.setHeaderLabels([
            self.i18n.tr('id'), self.i18n.tr('description'), self.i18n.tr('type'),
            self.i18n.tr('state'), self.i18n.tr('rate'), self.i18n.tr('format'),
            self.i18n.tr('range')
        ])
        self.apps_tree.setHeaderLabels([
            self.i18n.tr('id'), self.i18n.tr('application'), self.i18n.tr('type'),
            self.i18n.tr('state'), self.i18n.tr('rate'), self.i18n.tr('format'),
            self.i18n.tr('linked_device')
        ])
        self.set_default_btn.setText(self.i18n.tr('definir_defaut'))
        self.destroy_cb.setText(self.i18n.tr('mode_suppression'))
        self.destroy_btn.setText(self.i18n.tr('supprimer_noeud'))
