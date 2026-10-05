#!/usr/bin/env python3
"""Routing tab: WirePlumber routing rules management"""
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
from .logger import Logger

class RoutingTab(QWidget):
    """WirePlumber routing rules management tab"""
    
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.logger = Logger.instance()
        self.rules_file = Path.home() / '.config' / 'wireplumber' / 'main.lua.d' / '51-pcc-routing.lua'
        self._init_ui()
        self.refresh()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title
        title_lbl = QLabel(self.tr("Routing"))
        title_lbl.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        layout.addWidget(title_lbl)
        
        # Description
        desc_lbl = QLabel(
            self.tr("Per-application routing rules.\n"
                    "Rules created here are persistent and applied by WirePlumber.")
        )
        desc_lbl.setFont(QFont("Monospace", 9))
        desc_lbl.setStyleSheet("color: #888;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)
        
        # Rules list
        self.rules_gb = QGroupBox(self.tr("Routing"))
        rules_layout = QVBoxLayout()
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            self.tr("Application"), self.tr("Linked device")
        ])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 300)
        self.tree.setStyleSheet("QTreeWidget { background-color: #2a2a2a; color: #aaa; }")
        rules_layout.addWidget(self.tree)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton(self.tr("Add"))
        self.add_btn.clicked.connect(self._add_rule)
        btn_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton(self.tr("Remove"))
        self.remove_btn.clicked.connect(self._remove_rule)
        btn_layout.addWidget(self.remove_btn)
        
        self.reload_btn = QPushButton(self.tr("Reload WirePlumber"))
        self.reload_btn.setToolTip(self.tr("Restart WirePlumber to apply rules"))
        self.reload_btn.clicked.connect(self._reload_wireplumber)
        btn_layout.addWidget(self.reload_btn)
        
        btn_layout.addStretch()
        rules_layout.addLayout(btn_layout)
        
        self.rules_gb.setLayout(rules_layout)
        layout.addWidget(self.rules_gb)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def list_rules(self):
        """List all existing PCC rules"""
        rules = []
        if not self.rules_file.exists():
            return rules
        
        try:
            content = self.rules_file.read_text()
            
            # Parse rules with regex
            pattern = r'rule\s*=\s*\{\s*matches\s*=\s*\{\s*\{\s*"application\.process\.binary"\s*,\s*"equals"\s*,\s*"([^"]+)"\s*\}\s*\}\s*,\s*apply_properties\s*=\s*\{\s*\["target\.object"\]\s*=\s*"([^"]+)"\s*\}\s*\}'
            
            for match in re.finditer(pattern, content):
                rules.append({
                    'app_binary': match.group(1),
                    'target_device': match.group(2)
                })
        except Exception as e:
            self.logger.error(f"Routing rules read error: {e}")
        
        return rules
    
    def refresh(self):
        """Refresh the rules list"""
        self.tree.clear()
        rules = self.list_rules()
        
        for rule in rules:
            item = QTreeWidgetItem([
                rule['app_binary'],
                rule['target_device']
            ])
            self.tree.addTopLevelItem(item)
        
        # Update group title
        self.rules_gb.setTitle(f"{self.tr('Routing')} ({len(rules)})")
    
    def _add_rule(self):
        """Add a routing rule"""
        dialog = AddRuleDialog(self.pw, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_binary = dialog.app_combo.currentText().strip()
            target_device = dialog.device_combo.currentData()
            
            if not app_binary:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Please enter an application name"))
                return
            
            # Add the rule
            if self._write_rule(app_binary, target_device):
                self.refresh()
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.tr("Routing rule added: {app} -> {device}").format(app=app_binary, device=target_device),
                        3000
                    )
    
    def _write_rule(self, app_binary, target_device):
        """Write a rule to the Lua file"""
        try:
            # Remove old rule if it exists
            self._delete_rule(app_binary)
            
            # Add header if needed
            if not self.rules_file.exists():
                self.rules_file.parent.mkdir(parents=True, exist_ok=True)
                self.rules_file.write_text("-- Routing rules created by PCC\n")
            
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
            
            self.logger.info(f"Rule added: {app_binary} -> {target_device}")
            return True
        except Exception as e:
            self.logger.error(f"Rule add error: {e}")
            QMessageBox.warning(self, self.tr("Error"), str(e))
            return False
    
    def _delete_rule(self, app_binary):
        """Delete a specific rule"""
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
            self.logger.error(f"Rule delete error: {e}")
    
    def _remove_rule(self):
        """Remove the selected rule"""
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Please select a rule"))
            return
        
        app_binary = item.text(0)
        
        reply = QMessageBox.question(
            self,
            self.tr("Confirmation"),
            self.tr("Delete rule for {app}?").format(app=app_binary),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_rule(app_binary)
            self.refresh()
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.tr("Routing rule removed: {app}").format(app=app_binary),
                    3000
                )
    
    def _reload_wireplumber(self):
        """Restart WirePlumber"""
        reply = QMessageBox.question(
            self,
            self.tr("Confirmation"),
            self.tr("Restarting WirePlumber will interrupt active audio streams.\n"
                    "Do you want to continue?"),
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
                self.logger.info("WirePlumber restarted")
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.tr("WirePlumber reloaded"),
                        3000
                    )
            else:
                self.logger.error(f"WirePlumber restart failed: {result.stderr}")
                QMessageBox.warning(self, self.tr("Error"), self.tr("Restart failed"))
        except Exception as e:
            self.logger.error(f"WirePlumber restart error: {e}")
            QMessageBox.warning(self, self.tr("Error"), str(e))
    
    def refresh_language(self):
        self.rules_gb.setTitle(f"{self.tr('Routing')} ({len(self.list_rules())})")
        self.tree.setHeaderLabels([
            self.tr("Application"), self.tr("Linked device")
        ])
        self.add_btn.setText(self.tr("Add"))
        self.remove_btn.setText(self.tr("Remove"))
        self.reload_btn.setText(self.tr("Reload WirePlumber"))
        self.reload_btn.setToolTip(self.tr("Restart WirePlumber to apply rules"))


class AddRuleDialog(QDialog):
    """Dialog to add a routing rule"""
    
    def __init__(self, pw, parent=None):
        super().__init__(parent)
        self.pw = pw
        self.setWindowTitle(self.tr("Routing"))
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Application selector
        self.app_combo = QComboBox()
        self.app_combo.setEditable(True)
        self.app_combo.setPlaceholderText(self.tr("Binary name (e.g. firefox, vlc, mpd)"))
        apps = self._get_applications()
        self.app_combo.addItems(apps)
        form_layout.addRow(self.tr("Application") + ':', self.app_combo)
        
        # Device selector
        self.device_combo = QComboBox()
        devices = self.pw.get_devices()
        for device in devices:
            if device['type'] == 'output':
                self.device_combo.addItem(device['description'], device['name'])
        form_layout.addRow(self.tr("Device") + ':', self.device_combo)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox()
        ok_btn = button_box.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = button_box.addButton(self.tr("Cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(button_box)
    
    def _get_applications(self):
        """List known audio application binaries"""
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
        
        # Add common applications
        common_apps = ['firefox', 'vlc', 'mpv', 'spotify', 'chromium', 'chrome', 'mpd']
        for app in common_apps:
            apps.add(app)
        
        return sorted(apps)