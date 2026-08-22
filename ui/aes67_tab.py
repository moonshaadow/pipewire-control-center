#!/usr/bin/env python3
"""Onglet de gestion AES67 via configuration native PipeWire"""
import subprocess, re, os, signal, time, socket
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea,
    QPushButton, QLabel, QSpinBox, QComboBox, QLineEdit,
    QFormLayout, QMessageBox, QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class Aes67Tab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.hostname = socket.gethostname()
        self._init_ui()
        self._load_config()
        self._update_status()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(2000)
    
    def _init_ui(self):
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(10)
        
        # Statut
        status_gb = QGroupBox("Statut AES67")
        status_layout = QVBoxLayout()
        
        self.status_lbl = QLabel("Inactif")
        self.status_lbl.setFont(QFont("Monospace", 14, QFont.Weight.Bold))
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: #ef5350;")
        status_layout.addWidget(self.status_lbl)
        
        self.ptp_lbl = QLabel("")
        self.ptp_lbl.setFont(QFont("Monospace", 8))
        self.ptp_lbl.setStyleSheet("color: #888;")
        self.ptp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.ptp_lbl)
        
        self.detail_lbl = QLabel("")
        self.detail_lbl.setFont(QFont("Monospace", 8))
        self.detail_lbl.setStyleSheet("color: #888;")
        self.detail_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.detail_lbl)
        
        status_gb.setLayout(status_layout)
        layout.addWidget(status_gb)
        
        # Bouton principal
        self.toggle_btn = QPushButton("Activer AES67")
        self.toggle_btn.setStyleSheet("QPushButton { padding: 12px; font-size: 15px; font-weight: bold; color: #4CAF50; }")
        self.toggle_btn.clicked.connect(self._toggle_aes67)
        layout.addWidget(self.toggle_btn)
        
        # Configuration
        self.config_gb = QGroupBox("Configuration de session AES67")
        config_form = QFormLayout()
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Émetteur (sortie)", "Récepteur (entrée)", "Les deux"])
        self.mode_combo.setCurrentText("Émetteur (sortie)")
        config_form.addRow("Mode :", self.mode_combo)
        
        self.interface_combo = QComboBox()
        self._populate_interfaces()
        config_form.addRow("Interface réseau :", self.interface_combo)
        
        self.address_edit = QLineEdit("239.69.150.243")
        config_form.addRow("Adresse multicast :", self.address_edit)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(5004)
        config_form.addRow("Port :", self.port_spin)
        
        self.channels_spin = QSpinBox()
        self.channels_spin.setRange(1, 64)
        self.channels_spin.setValue(2)
        config_form.addRow("Canaux de sortie :", self.channels_spin)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["S16BE", "S24BE"])
        self.format_combo.setCurrentText("S24BE")
        config_form.addRow("Format :", self.format_combo)
        
        self.rate_combo = QComboBox()
        self.rate_combo.addItems(["48000", "96000", "192000"])
        self.rate_combo.setCurrentText("48000")
        config_form.addRow("Fréquence :", self.rate_combo)
        
        self.latency_spin = QSpinBox()
        self.latency_spin.setRange(1, 100)
        self.latency_spin.setValue(5)
        self.latency_spin.setSuffix(" ms")
        config_form.addRow("Latence :", self.latency_spin)
        
        self.ttl_spin = QSpinBox()
        self.ttl_spin.setRange(1, 255)
        self.ttl_spin.setValue(32)
        config_form.addRow("TTL :", self.ttl_spin)
        
        self.ptp_cb = QCheckBox("Synchronisation PTP")
        self.ptp_cb.setChecked(False)
        config_form.addRow(self.ptp_cb)
        
        self.ptp_master_cb = QCheckBox("Devenir maître PTP")
        self.ptp_master_cb.setChecked(False)
        config_form.addRow(self.ptp_master_cb)
        
        self.config_gb.setLayout(config_form)
        layout.addWidget(self.config_gb)
        
        # Note
        note_lbl = QLabel("ℹ Pour compatibilité Dante (mode AES67), utilisez 48 kHz.\n"
                          "En mode Récepteur ou Les deux, les flux AES67 découverts sur le réseau sont ajoutés automatiquement.\n"
                          "⚠️ En mode Les deux, votre propre flux peut apparaître comme une entrée. C'est normal et sans impact.")
        note_lbl.setFont(QFont("Monospace", 8))
        note_lbl.setStyleSheet("color: #888; padding: 4px;")
        note_lbl.setWordWrap(True)
        layout.addWidget(note_lbl)
        
        # Journal
        log_gb = QGroupBox("Journal")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Monospace", 8))
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #aaa; border: 1px solid #333;")
        self.log_text.setMaximumHeight(100)
        log_layout.addWidget(self.log_text)
        log_gb.setLayout(log_layout)
        layout.addWidget(log_gb)
        
        # Nettoyage
        clean_layout = QHBoxLayout()
        self.clean_btn = QPushButton("🗑 Supprimer la configuration AES67")
        self.clean_btn.clicked.connect(self._remove_config)
        clean_layout.addWidget(self.clean_btn)
        layout.addLayout(clean_layout)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll_area)
    
    def _populate_interfaces(self):
        self.interface_combo.clear()
        try:
            result = subprocess.run(['ip', '-o', 'link', 'show'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    m = re.search(r':\s+(\w+):', line)
                    if m:
                        iface = m.group(1)
                        if iface != 'lo':
                            self.interface_combo.addItem(iface)
        except Exception:
            pass
        if self.interface_combo.count() == 0:
            self.interface_combo.addItem("eth0")
    
    def _log(self, msg, color="#aaa"):
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f'<span style="color:#666;">{now}</span> <span style="color:{color};">{msg}</span>')
    
    @property
    def _config_file(self) -> Path:
        return Path.home() / '.config' / 'pipewire' / 'pipewire.conf.d' / '20-aes67-session.conf'
    
    @property
    def _prefs_file(self) -> Path:
        return Path.home() / '.config' / 'pipewire' / 'pipewire.conf.d' / 'aes67-prefs.txt'
    
    @property
    def _ptp_service_file(self) -> Path:
        return Path.home() / '.config' / 'systemd' / 'user' / 'ptp4l.service'
    
    def _load_config(self):
        if self._prefs_file.exists():
            prefs = self._prefs_file.read_text()
            m = re.search(r'ptp_enabled=(\w+)', prefs)
            if m:
                self.ptp_cb.setChecked(m.group(1) == 'true')
            m = re.search(r'ptp_master=(\w+)', prefs)
            if m:
                self.ptp_master_cb.setChecked(m.group(1) == 'true')
        
        if self._config_file.exists():
            content = self._config_file.read_text()
            if 'rtp-sink' in content and 'create-stream' in content:
                self.mode_combo.setCurrentText("Les deux")
            elif 'rtp-sink' in content:
                self.mode_combo.setCurrentText("Émetteur (sortie)")
            elif 'create-stream' in content:
                self.mode_combo.setCurrentText("Récepteur (entrée)")
            
            m = re.search(r'local\.ifname\s*=\s*(\w+)', content)
            if m:
                idx = self.interface_combo.findText(m.group(1))
                if idx >= 0:
                    self.interface_combo.setCurrentIndex(idx)
            
            m = re.search(r'destination\.ip\s*=\s*([\d.]+)', content)
            if m:
                self.address_edit.setText(m.group(1))
            
            m = re.search(r'destination\.port\s*=\s*(\d+)', content)
            if m:
                self.port_spin.setValue(int(m.group(1)))
            
            m = re.search(r'audio\.channels\s*=\s*(\d+)', content)
            if m:
                self.channels_spin.setValue(int(m.group(1)))
            
            m = re.search(r'audio\.format\s*=\s*"(\w+)"', content)
            if m:
                self.format_combo.setCurrentText(m.group(1))
            
            m = re.search(r'audio\.rate\s*=\s*(\d+)', content)
            if m:
                self.rate_combo.setCurrentText(m.group(1))
            
            m = re.search(r'sess\.latency\.msec\s*=\s*(\d+)', content)
            if m:
                self.latency_spin.setValue(int(m.group(1)))
            
            m = re.search(r'net\.ttl\s*=\s*(\d+)', content)
            if m:
                self.ttl_spin.setValue(int(m.group(1)))
    
    def _save_prefs(self):
        prefs = f"""ptp_enabled={str(self.ptp_cb.isChecked()).lower()}
ptp_master={str(self.ptp_master_cb.isChecked()).lower()}
"""
        try:
            self._prefs_file.parent.mkdir(parents=True, exist_ok=True)
            self._prefs_file.write_text(prefs)
        except Exception:
            pass
    
    def _set_config_enabled(self, enabled):
        self.mode_combo.setEnabled(enabled)
        self.interface_combo.setEnabled(enabled)
        self.address_edit.setEnabled(enabled)
        self.port_spin.setEnabled(enabled)
        self.channels_spin.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.rate_combo.setEnabled(enabled)
        self.latency_spin.setEnabled(enabled)
        self.ttl_spin.setEnabled(enabled)
        self.ptp_cb.setEnabled(enabled)
        self.ptp_master_cb.setEnabled(enabled)
    
    def _update_status(self):
        if self._config_file.exists():
            self.status_lbl.setText("● Actif (configuré)")
            self.status_lbl.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
            self.toggle_btn.setText("Désactiver AES67")
            self.toggle_btn.setStyleSheet("QPushButton { padding: 12px; font-size: 15px; font-weight: bold; color: #ef5350; }")
            self._set_config_enabled(False)
        else:
            self.status_lbl.setText("Inactif")
            self.status_lbl.setStyleSheet("color: #ef5350; font-size: 14px; font-weight: bold;")
            self.toggle_btn.setText("Activer AES67")
            self.toggle_btn.setStyleSheet("QPushButton { padding: 12px; font-size: 15px; font-weight: bold; color: #4CAF50; }")
            self._set_config_enabled(True)
        
        if self.ptp_cb.isChecked():
            if self._ptp_service_file.exists():
                try:
                    result = subprocess.run(
                        ['systemctl', '--user', 'is-active', 'ptp4l'],
                        capture_output=True, text=True
                    )
                    if result.stdout.strip() == 'active':
                        self.ptp_lbl.setText("PTP : ✓ Actif")
                        self.ptp_lbl.setStyleSheet("color: #4CAF50;")
                    else:
                        self.ptp_lbl.setText("PTP : ✗ Inactif")
                        self.ptp_lbl.setStyleSheet("color: #ef5350;")
                except Exception:
                    self.ptp_lbl.setText("PTP : ?")
            else:
                self.ptp_lbl.setText("PTP : Service non installé")
                self.ptp_lbl.setStyleSheet("color: #ff9800;")
        else:
            self.ptp_lbl.setText("")
    
    def _check_ptp4l_installed(self) -> bool:
        """Vérifie si ptp4l est installé"""
        try:
            result = subprocess.run(['which', 'ptp4l'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_ptp_service(self):
        """Installe le service ptp4l systemd"""
        iface = self.interface_combo.currentText().strip()
        if not iface:
            return False
        
        master = self.ptp_master_cb.isChecked()
        if master:
            exec_start = f"/usr/sbin/ptp4l -i {iface} -P 1 --priority1=1 -m"
        else:
            exec_start = f"/usr/sbin/ptp4l -i {iface} -s -m"
        
        service_content = f"""[Unit]
Description=PTP4L Precision Time Protocol
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""
        
        try:
            self._ptp_service_file.parent.mkdir(parents=True, exist_ok=True)
            self._ptp_service_file.write_text(service_content)
            subprocess.run(['systemctl', '--user', 'daemon-reload'], capture_output=True)
            self._log("Service ptp4l installé", "#4CAF50")
            return True
        except Exception as e:
            self._log(f"Erreur installation service : {e}", "#ef5350")
            return False
    
    def _start_ptp(self):
        """Démarre le service ptp4l"""
        if not self._ptp_service_file.exists():
            if not self._install_ptp_service():
                return False
        
        try:
            result = subprocess.run(['systemctl', '--user', 'start', 'ptp4l'], capture_output=True)
            if result.returncode == 0:
                self._log("ptp4l démarré", "#4CAF50")
                return True
            else:
                self._log(f"Erreur démarrage ptp4l : {result.stderr}", "#ef5350")
                return False
        except Exception as e:
            self._log(f"Erreur démarrage ptp4l : {e}", "#ef5350")
            return False
    
    def _stop_ptp(self):
        """Arrête le service ptp4l"""
        try:
            result = subprocess.run(['systemctl', '--user', 'stop', 'ptp4l'], capture_output=True)
            if result.returncode == 0:
                self._log("ptp4l arrêté", "#ef5350")
                return True
        except Exception as e:
            self._log(f"Erreur arrêt ptp4l : {e}", "#ef5350")
        return False
    
    def _toggle_aes67(self):
        if self._config_file.exists():
            self._remove_config()
        else:
            self._activate_aes67()
        self._update_status()
    
    def _activate_aes67(self):
        # Vérifier PTP avant de commencer
        if self.ptp_cb.isChecked():
            if not self._check_ptp4l_installed():
                reply = QMessageBox.question(
                    self,
                    "ptp4l non installé",
                    "La synchronisation PTP nécessite linuxptp (ptp4l).\n\n"
                    "Voulez-vous l'installer maintenant ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        subprocess.run(['pkexec', 'apt', 'install', '-y', 'linuxptp'], check=True)
                        self._log("linuxptp installé", "#4CAF50")
                    except Exception as e:
                        self._log(f"Erreur installation linuxptp : {e}", "#ef5350")
                        QMessageBox.warning(self, "Erreur", "Impossible d'installer linuxptp.")
                        return
                else:
                    self._log("Installation linuxptp annulée", "#ef5350")
                    QMessageBox.warning(self, "Annulé", "Activation AES67 annulée.")
                    return
        
        reply = QMessageBox.warning(
            self,
            "⚠️ Activation AES67",
            "Cette action va :\n"
            "1. Configurer les modules RTP/SAP\n"
            "2. Redémarrer PipeWire et WirePlumber\n\n"
            "⚠️ Toute lecture audio sera interrompue.\n\n"
            "Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Démarrer PTP si nécessaire
        if self.ptp_cb.isChecked():
            if not self._start_ptp():
                QMessageBox.warning(self, "Erreur", "Impossible de démarrer ptp4l.")
                return
        
        config = self._generate_modules_only()
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._config_file.write_text(config)
            self._save_prefs()
            self._log("Modules AES67 ajoutés à la configuration", "#4CAF50")
        except Exception as e:
            self._log(f"Erreur écriture config : {e}", "#ef5350")
            return
        
        self._log("Redémarrage de PipeWire + WirePlumber...", "#4fc3f7")
        ok, msg = self.pw.restart_services()
        if ok:
            self._log("Services redémarrés avec AES67", "#4CAF50")
            QMessageBox.information(self, "Succès", "AES67 activé.")
        else:
            self._log(f"Erreur redémarrage : {msg}", "#ef5350")
            QMessageBox.warning(self, "Erreur", f"Erreur au redémarrage : {msg}")
        
        self._update_status()
    
    def _remove_config(self):
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Supprimer la configuration AES67 et redémarrer PipeWire ?\n\n"
            "⚠️ Toute lecture audio sera interrompue."
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            if self._config_file.exists():
                self._config_file.unlink()
            self._log("Configuration AES67 supprimée", "#ef5350")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur : {e}")
            return
        
        # Arrêter ptp4l si on l'a démarré
        if self.ptp_cb.isChecked():
            self._stop_ptp()
        
        self._log("Redémarrage de PipeWire + WirePlumber...", "#4fc3f7")
        ok, msg = self.pw.restart_services()
        if ok:
            self._log("Services redémarrés sans AES67", "#4CAF50")
        else:
            self._log(f"Erreur redémarrage : {msg}", "#ef5350")
        
        self._update_status()
    
    def _generate_modules_only(self) -> str:
        iface = self.interface_combo.currentText()
        addr = self.address_edit.text()
        port = self.port_spin.value()
        channels = self.channels_spin.value()
        fmt = self.format_combo.currentText()
        ttl = self.ttl_spin.value()
        mode = self.mode_combo.currentText()
        rate = self.rate_combo.currentText()
        latency = self.latency_spin.value()
        positions = " ".join([f"AUX{i+1}" for i in range(channels)])
        
        session_name = f"{self.hostname} AES67 Stream"
        node_description = f"{self.hostname} AES67 Stream"
        
        modules = []
        
        sap_rules = []
        if mode in ("Récepteur (entrée)", "Les deux"):
            sap_rules.append(f"""                {{
                    matches = [{{ rtp.session = "~.*" }}]
                    actions = {{
                        create-stream = {{
                            node.virtual = false
                            media.class = "Audio/Source"
                            device.api = aes67
                            sess.latency.msec = {latency}
                            priority.session = 100
                        }}
                    }}
                }}""")
        if mode in ("Émetteur (sortie)", "Les deux"):
            sap_rules.append("""                {
                    matches = [{ sess.sap.announce = true }]
                    actions = { announce-stream = {} }
                }""")
        
        if sap_rules:
            modules.append(f"""    {{ name = libpipewire-module-rtp-sap
        args = {{
            local.ifname = {iface}
            sap.ip = 239.255.255.255
            sap.port = 9875
            net.ttl = {ttl}
            net.loop = true
            stream.rules = [
{','.join(sap_rules)}
            ]
        }}
    }}""")
        
        if mode in ("Émetteur (sortie)", "Les deux"):
            modules.append(f"""    {{ name = libpipewire-module-rtp-sink
        args = {{
            local.ifname = {iface}
            destination.ip = {addr}
            destination.port = {port}
            net.mtu = 1280
            net.ttl = {ttl}
            net.loop = true
            sess.min-ptime = 1
            sess.max-ptime = 1
            sess.name = "{session_name}"
            sess.media = "audio"
            sess.ts-refclk = clock.system.monotonic
            sess.ptime = 1
            sess.latency.msec = {latency}
            sess.announce = true
            audio.format = "{fmt}"
            audio.rate = {rate}
            audio.channels = {channels}
            audio.position = [ {positions} ]
            stream.props = {{
                node.name = "aes67-sink"
                node.description = "{node_description}"
                media.class = "Audio/Sink"
                node.virtual = false
                device.api = aes67
                sess.sap.announce = true
                node.always-process = false
                node.pause-on-idle = true
                priority.session = 100
            }}
        }}
    }}""")
        
        return f"context.modules = [\n{',\n'.join(modules)}\n]\n"
    
    def shutdown(self):
        self.timer.stop()
        # Arrêter ptp4l si on l'avait démarré
        if self.ptp_cb.isChecked():
            self._stop_ptp()
