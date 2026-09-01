#!/usr/bin/env python3
"""Onglet Routing : gestion des règles de routing WirePlumber"""
import subprocess
import json
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QMessageBox, QTreeWidget, QTreeWidgetItem, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .i18n import I18n
from .logger import Logger

class RoutingTab(QWidget):
    """Onglet de gestion des règles de routing WirePlumber"""
    
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self.rules_file = Path.home() / '.config' / 'wireplumber' / 'main.lua.d' / '51-pcc-routing.lua'
        self._init_ui()
        self.refresh()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Titre
        title_lbl = QLabel(self.i18n.tr('routing'))
        title_lbl.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        layout.addWidget(title_lbl)
        
        # Description
        desc_lbl = QLabel(
            "Règles de routing par application.\n"
            "Les règles créées ici sont persistantes et appliquées par WirePlumber."
        )
        desc_lbl.setFont(QFont("Monospace", 9))
        desc_lbl.setStyleSheet("color: #888;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)
        
        # Liste des règles
        self.rules_gb = QGroupBox(self.i18n.tr('routing'))
        rules_layout = QVBoxLayout()
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            self.i18n.tr('application'), self.i18n.tr('linked_device')
        ])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 300)
        self.tree.setStyleSheet("QTreeWidget { background-color: #2a2a2a; color: #aaa; }")
        rules_layout.addWidget(self.tree)
        
        # Boutons
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton(self.i18n.tr('ajouter'))
        self.add_btn.clicked.connect(self._add_rule)
        btn_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton(self.i18n.tr('supprimer'))
        self.remove_btn.clicked.connect(self._remove_rule)
        btn_layout.addWidget(self.remove_btn)
        
        self.reload_btn = QPushButton(self.i18n.tr('reload_wireplumber'))
        self.reload_btn.setToolTip(self.i18n.tr('reload_wireplumber_tooltip'))
        self.reload_btn.clicked.connect(self._reload_wireplumber)
        btn_layout.addWidget(self.reload_btn)
        
        btn_layout.addStretch()
        rules_layout.addLayout(btn_layout)
        
        self.rules_gb.setLayout(rules_layout)
        layout.addWidget(self.rules_gb)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def list_rules(self):
        """Liste toutes les règles PCC existantes"""
        rules = []
        if not self.rules_file.exists():
            return rules
        
        try:
            content = self.rules_file.read_text()
            
            # Parser les règles avec regex
            pattern = r'rule\s*=\s*\{\s*matches\s*=\s*\{\s*\{\s*"application\.process\.binary"\s*,\s*"equals"\s*,\s*"([^"]+)"\s*\}\s*\}\s*,\s*apply_properties\s*=\s*\{\s*\["target\.object"\]\s*=\s*"([^"]+)"\s*\}\s*\}'
            
            for match in re.finditer(pattern, content):
                rules.append({
                    'app_binary': match.group(1),
                    'target_device': match.group(2)
                })
        except Exception as e:
            self.logger.error(f"Erreur lecture règles routing: {e}")
        
        return rules
    
    def refresh(self):
        """Rafraîchit la liste des règles"""
        self.tree.clear()
        rules = self.list_rules()
        
        for rule in rules:
            item = QTreeWidgetItem([
                rule['app_binary'],
                rule['target_device']
            ])
            self.tree.addTopLevelItem(item)
        
        # Mettre à jour le titre du groupe
        self.rules_gb.setTitle(f"{self.i18n.tr('routing')} ({len(rules)})")
    
    def _add_rule(self):
        """Ajoute une règle de routing"""
        dialog = AddRuleDialog(self.pw, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_binary = dialog.app_combo.currentText().strip()
            target_device = dialog.device_combo.currentData()
            
            if not app_binary:
                QMessageBox.warning(self, 'Erreur', 'Veuillez entrer un nom d\'application')
                return
            
            # Ajouter la règle
            if self._write_rule(app_binary, target_device):
                self.refresh()
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.i18n.tr('routing_rule_added').format(app=app_binary, device=target_device),
                        3000
                    )
    
    def _write_rule(self, app_binary, target_device):
        """Écrit une règle dans le fichier Lua"""
        try:
            # Supprimer l'ancienne règle si elle existe
            self._delete_rule(app_binary)
            
            # Ajouter le header si nécessaire
            if not self.rules_file.exists():
                self.rules_file.parent.mkdir(parents=True, exist_ok=True)
                self.rules_file.write_text("-- Règles de routing créées par PCC\n")
            
            rule_lua = f"""
rule = {{
  matches = {{
    {{ "application.process.binary", "equals", "{app_binary}" }}
  }},
  apply_properties = {{
    ["target.object"] = "{target_device}"
  }}
}}

-- [PCC-END:{app_binary}]
"""
            
            with open(self.rules_file, 'a') as f:
                f.write(rule_lua)
            
            self.logger.info(f"Règle ajoutée: {app_binary} → {target_device}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur ajout règle: {e}")
            QMessageBox.warning(self, 'Erreur', str(e))
            return False
    
    def _delete_rule(self, app_binary):
        """Supprime une règle spécifique"""
        try:
            if not self.rules_file.exists():
                return
            
            content = self.rules_file.read_text()
            
            end_marker = f"-- [PCC-END:{app_binary}]"
            end_idx = content.find(end_marker)
            
            if end_idx == -1:
                return
            
            start_idx = content.rfind("rule = {", 0, end_idx)
            
            if start_idx == -1:
                return
            
            new_content = content[:start_idx] + content[end_idx + len(end_marker):]
            self.rules_file.write_text(new_content)
        except Exception as e:
            self.logger.error(f"Erreur suppression règle: {e}")
    
    def _remove_rule(self):
        """Supprime la règle sélectionnée"""
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, 'Erreur', 'Sélectionnez une règle')
            return
        
        app_binary = item.text(0)
        
        reply = QMessageBox.question(
            self,
            self.i18n.tr('confirmation'),
            f"Supprimer la règle pour {app_binary} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_rule(app_binary)
            self.refresh()
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.i18n.tr('routing_rule_removed').format(app=app_binary),
                    3000
                )
    
    def _reload_wireplumber(self):
        """Redémarre WirePlumber"""
        reply = QMessageBox.question(
            self,
            self.i18n.tr('confirmation'),
            self.i18n.tr('reload_wireplumber_confirm'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            result = subprocess.run(
                ['systemctl', '--user', 'restart', 'wireplumber'],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                self.logger.info("WirePlumber redémarré")
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.i18n.tr('wireplumber_reloaded'),
                        3000
                    )
            else:
                self.logger.error(f"Échec redémarrage WirePlumber: {result.stderr}")
                QMessageBox.warning(self, 'Erreur', 'Échec du redémarrage')
        except Exception as e:
            self.logger.error(f"Erreur redémarrage WirePlumber: {e}")
            QMessageBox.warning(self, 'Erreur', str(e))
    
    def refresh_language(self):
        self.rules_gb.setTitle(f"{self.i18n.tr('routing')} ({len(self.list_rules())})")
        self.tree.setHeaderLabels([
            self.i18n.tr('application'), self.i18n.tr('linked_device')
        ])
        self.add_btn.setText(self.i18n.tr('ajouter'))
        self.remove_btn.setText(self.i18n.tr('supprimer'))
        self.reload_btn.setText(self.i18n.tr('reload_wireplumber'))
        self.reload_btn.setToolTip(self.i18n.tr('reload_wireplumber_tooltip'))


class AddRuleDialog(QDialog):
    """Dialog pour ajouter une règle de routing"""
    
    def __init__(self, pw, parent=None):
        super().__init__(parent)
        self.pw = pw
        self.i18n = I18n.instance()
        self.setWindowTitle(self.i18n.tr('routing'))
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Sélecteur d'application
        self.app_combo = QComboBox()
        self.app_combo.setEditable(True)
        self.app_combo.setPlaceholderText("Nom du binaire (ex: firefox, vlc, mpd)")
        apps = self._get_applications()
        self.app_combo.addItems(apps)
        form_layout.addRow('Application:', self.app_combo)
        
        # Sélecteur de périphérique
        self.device_combo = QComboBox()
        devices = self.pw.get_devices()
        for device in devices:
            if device['type'] == 'sortie':
                self.device_combo.addItem(device['description'], device['name'])
        form_layout.addRow('Périphérique:', self.device_combo)
        
        layout.addLayout(form_layout)
        
        # Boutons
        button_box = QDialogButtonBox()
        ok_btn = button_box.addButton('OK', QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = button_box.addButton('Annuler', QDialogButtonBox.ButtonRole.RejectRole)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(button_box)
    
    def _get_applications(self):
        """Liste les binaires d'applications audio connus"""
        apps = set()
        try:
            result = subprocess.run(['pw-dump'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for item in data:
                    if item.get('type') == 'PipeWire:Interface:Node':
                        info = item.get('info', {})
                        props = info.get('props', {})
                        binary = props.get('application.process.binary', '')
                        if binary and binary not in ('wireplumber', 'pipewire', 'wpctl'):
                            apps.add(binary)
        except Exception:
            pass
        
        # Ajouter des applications courantes
        common_apps = ['firefox', 'vlc', 'mpv', 'spotify', 'chromium', 'chrome', 'mpd']
        for app in common_apps:
            apps.add(app)
        
        return sorted(apps)
