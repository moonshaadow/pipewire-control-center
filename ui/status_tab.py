#!/usr/bin/env python3
"""Onglet d'état avec journal enrichi et boutons d'action"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTextEdit,
    QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from datetime import datetime
import subprocess
import re
import os
from pathlib import Path
from .i18n import I18n
from .logger import Logger

class StatusTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self._events = []
        self._logged_aes67_lines = set()
        self._prev_rate = None
        self._prev_device = None
        self._prev_stream_ids = set()
        self._prev_xruns = 0
        self._prev_ptp_state = None
        self._prev_aes67_state = None
        self._prev_aes67_log_size = 0
        self._init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_changes)
        self.timer.start(1500)
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        self.version_lbl = QLabel(f"PipeWire Control Center v1.0 — PipeWire {self.pw.get_version()}")
        self.version_lbl.setFont(QFont("Monospace", 9))
        self.version_lbl.setStyleSheet("color: #666; padding: 4px;")
        self.version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.version_lbl)
        
        # Boutons d'action centrés
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.addStretch(1)
        
        self.restart_btn = QPushButton(self.i18n.tr('redemarrer_services'))
        self.restart_btn.setToolTip(self.i18n.tr('restart_btn_tooltip'))
        self.restart_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-weight: bold;
                border: 1px solid #ff9800;
                border-radius: 4px;
                color: #ff9800;
            }
            QPushButton:hover {
                background-color: #ff9800;
                color: #000;
            }
        """)
        self.restart_btn.clicked.connect(self._restart_services)
        actions_layout.addWidget(self.restart_btn)
        
        self.clean_btn = QPushButton(self.i18n.tr('nettoyer_configs'))
        self.clean_btn.setToolTip(self.i18n.tr('clean_btn_tooltip'))
        self.clean_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-weight: bold;
                border: 1px solid #ef5350;
                border-radius: 4px;
                color: #ef5350;
            }
            QPushButton:hover {
                background-color: #ef5350;
                color: #000;
            }
        """)
        self.clean_btn.clicked.connect(self._clean_all_configs)
        actions_layout.addWidget(self.clean_btn)
        
        actions_layout.addStretch(1)
        layout.addLayout(actions_layout)
        
        # Système
        self.sys_gb = QGroupBox(self.i18n.tr('systeme'))
        sys_layout = QVBoxLayout()
        self.sys_text = QTextEdit()
        self.sys_text.setReadOnly(True)
        self.sys_text.setFont(QFont("Monospace", 9))
        self.sys_text.setStyleSheet("color: #ccc; padding: 8px; background-color: #2a2a2a; border-radius: 4px; border: none;")
        self.sys_text.setFixedHeight(150)
        self.sys_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._update_sys()
        sys_layout.addWidget(self.sys_text)
        self.refresh_sys_btn = QPushButton(self.i18n.tr('rafraichir'))
        self.refresh_sys_btn.clicked.connect(self._update_sys)
        sys_layout.addWidget(self.refresh_sys_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.sys_gb.setLayout(sys_layout)
        layout.addWidget(self.sys_gb)
        
        # Journal
        self.events_gb = QGroupBox(self.i18n.tr('journal'))
        events_layout = QVBoxLayout()
        self.events_text = QTextEdit()
        self.events_text.setReadOnly(True)
        self.events_text.setFont(QFont("Monospace", 8))
        self.events_text.setStyleSheet("background-color: #1e1e1e; color: #aaa; border: 1px solid #333;")
        self.events_text.setMinimumHeight(200)
        events_layout.addWidget(self.events_text)
        
        btn_layout = QHBoxLayout()
        self.clear_btn = QPushButton(self.i18n.tr('effacer'))
        self.clear_btn.clicked.connect(lambda: (self._events.clear(), self._refresh_events()))
        btn_layout.addWidget(self.clear_btn)
        
        self.auto_scroll_cb = QPushButton(self.i18n.tr('auto_scroll_on'))
        self.auto_scroll_cb.setCheckable(True)
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.toggled.connect(
            lambda checked: self.auto_scroll_cb.setText(
                self.i18n.tr('auto_scroll_on') if checked else self.i18n.tr('auto_scroll_off')
            )
        )
        btn_layout.addWidget(self.auto_scroll_cb)
        
        btn_layout.addStretch()
        events_layout.addLayout(btn_layout)
        self.events_gb.setLayout(events_layout)
        layout.addWidget(self.events_gb)
        self.setLayout(layout)
    
    def _restart_services(self):
        """Redémarre PipeWire et WirePlumber"""
        reply = QMessageBox.question(
            self,
            self.i18n.tr('confirmation'),
            self.i18n.tr('restart_confirm') + "\n\n" + self.i18n.tr('restart_warning'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok, msg = self.pw.restart_services()
            if ok:
                self._log(msg, "#4CAF50", self.i18n.tr('category_audio'))
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.i18n.tr('services_restarted'),
                        3000
                    )
            else:
                self._log(msg, "#ef5350", self.i18n.tr('category_audio'))
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.i18n.tr('services_restart_error'),
                        3000
                    )
    
    def _clean_all_configs(self):
        """Supprime toutes les configurations locales"""
        pipewire_dir = Path.home() / '.config' / 'pipewire' / 'pipewire.conf.d'
        wireplumber_dir = Path.home() / '.config' / 'wireplumber' / 'main.lua.d'
        
        files_to_delete = []
        if pipewire_dir.exists():
            files_to_delete.extend(pipewire_dir.glob('*.conf'))
        if wireplumber_dir.exists():
            files_to_delete.extend(wireplumber_dir.glob('*.lua'))
        
        if not files_to_delete:
            QMessageBox.information(self, self.i18n.tr('info'), self.i18n.tr('no_local_config'))
            return
        
        file_list = '\n'.join(f"  • {f}" for f in files_to_delete)
        
        reply = QMessageBox.question(
            self,
            self.i18n.tr('confirmation'),
            self.i18n.tr('clean_confirm').format(file_list=file_list),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        errors = []
        for f in files_to_delete:
            try:
                f.unlink()
                self.logger.info(f"Fichier supprimé: {f}")
            except Exception as e:
                errors.append(str(e))
                self.logger.error(f"Erreur suppression {f}: {e}")
        
        # Supprimer les dossiers vides
        try:
            if pipewire_dir.exists():
                pipewire_dir.rmdir()
        except Exception:
            pass
        try:
            if wireplumber_dir.exists():
                wireplumber_dir.rmdir()
        except Exception:
            pass
        
        if errors:
            self._log(self.i18n.tr('clean_errors').format(errors='\n'.join(errors)), "#ef5350", self.i18n.tr('category_general'))
        else:
            self._log(self.i18n.tr('clean_configs_success'), "#4CAF50", self.i18n.tr('category_general'))
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.i18n.tr('configs_cleaned'),
                    3000
                )
            # Redémarrer les services
            ok, msg = self.pw.restart_services()
            if ok:
                self._log(msg, "#4CAF50", self.i18n.tr('category_audio'))
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.i18n.tr('services_restarted'),
                        3000
                    )
            else:
                self._log(msg, "#ef5350", self.i18n.tr('category_audio'))
    
    def _update_sys(self):
        try:
            pw_v = "Inconnue"
            result = subprocess.run(['pipewire', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                m = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
                if m: pw_v = m.group(1)
            
            wp_v = "Inconnue"
            result = subprocess.run(['wireplumber', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                m = re.search(r'(\d+\.\d+\.\d+)', result.stdout + result.stderr)
                if m: wp_v = m.group(1)
            
            rates = self.pw.read_allowed_rates()
            rates_str = ', '.join(map(str, sorted(rates))) + ' Hz' if rates else self.i18n.tr('default_rates')
            
            devices = self.pw.get_devices()
            sinks = sum(1 for d in devices if d['type'] == 'sortie')
            sources = sum(1 for d in devices if d['type'] == 'entrée')
            
            quantum = self.pw.get_quantum()
            rate = self.pw.get_rate()
            latency_ms = (quantum / rate) * 1000 if rate else 0
            
            xruns = self._get_xruns()
            aes67_state = self._get_aes67_state()
            ptp_state = self._get_ptp_state()
            detected_str = self.i18n.tr('detected')
            
            self.sys_text.setHtml(
                f"<b>PipeWire</b>     {pw_v}<br>"
                f"<b>WirePlumber</b>  {wp_v}<br><br>"
                f"<b>{self.i18n.tr('outputs')}</b>      {sinks} {detected_str}<br>"
                f"<b>{self.i18n.tr('inputs')}</b>      {sources} {detected_str}<br><br>"
                f"<b>{self.i18n.tr('frequencies')}</b>   {rates_str}<br><br>"
                f"<b>{self.i18n.tr('buffer')}</b>       {quantum} {self.i18n.tr('samples')}<br>"
                f"<b>{self.i18n.tr('latence')}</b>      {latency_ms:.1f} {self.i18n.tr('milliseconds')} ({rate} {self.i18n.tr('hz')})<br><br>"
                f"<b>{self.i18n.tr('xruns')}</b>        {xruns}<br><br>"
                f"<b>AES67</b>        {aes67_state}<br>"
                f"<b>PTP</b>          {ptp_state}"
            )
        except Exception as e:
            self.sys_text.setHtml(f"Erreur : {e}")
    
    def _get_xruns(self):
        try:
            r = subprocess.run(['pw-top', '-b', '-n1'], capture_output=True, text=True, timeout=3)
            total = sum(int(m.group(1)) for m in re.finditer(r'xrun\S*\s+(\d+)', r.stdout))
            return self.i18n.tr('since_start').format(total=total)
        except Exception:
            return self.i18n.tr('not_available')
    
    def _get_aes67_state(self):
        config_file = os.path.expanduser('~/.config/pipewire/pipewire.conf.d/20-aes67-session.conf')
        if os.path.exists(config_file):
            return self.i18n.tr('enabled')
        return self.i18n.tr('disabled')
    
    def _get_ptp_state(self):
        try:
            r = subprocess.run(['systemctl', '--user', 'is-active', 'ptp4l'], capture_output=True, text=True)
            if r.stdout.strip() == 'active':
                return self.i18n.tr('enabled')
            return self.i18n.tr('disabled')
        except Exception:
            return self.i18n.tr('not_available')
    
    def _log(self, msg, color="#aaa", category=None):
        if category is None:
            category = self.i18n.tr('category_general')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._events.append((timestamp, category, msg, color))
        if len(self._events) > 500:
            self._events = self._events[-500:]
        self._refresh_events()
    
    def _refresh_events(self):
        self.events_text.setHtml(''.join(
            f'<span style="color:#555;">{t}</span> '
            f'<span style="color:#777;">[{c}]</span> '
            f'<span style="color:{col};">{m}</span><br>'
            for t, c, m, col in self._events
        ))
        if self.auto_scroll_cb.isChecked():
            self.events_text.verticalScrollBar().setValue(self.events_text.verticalScrollBar().maximum())
    
    def _check_changes(self):
        try:
            s = self.pw.get_summary()
            
            if self._prev_rate is not None and s['rate'] != self._prev_rate:
                self._log(self.i18n.tr('frequency_changed').format(self._prev_rate, s['rate']), "#4fc3f7", self.i18n.tr('category_audio'))
            self._prev_rate = s['rate']
            
            dev = s['default_sink']['description'] if s['default_sink'] else self.i18n.tr('none')
            if self._prev_device is not None and dev != self._prev_device:
                self._log(self.i18n.tr('device_changed').format(self._prev_device, dev), "#81c784", self.i18n.tr('category_audio'))
            self._prev_device = dev
            
            current = {d['name'] for d in self.pw.get_devices() if d['type'] == 'sortie' and d.get('state') == 'running'}
            for name in current - self._prev_stream_ids:
                self._log(self.i18n.tr('stream_started').format(name), "#4CAF50", self.i18n.tr('category_audio'))
            for name in self._prev_stream_ids - current:
                self._log(self.i18n.tr('stream_stopped').format(name), "#ef5350", self.i18n.tr('category_audio'))
            self._prev_stream_ids = current
            
            xruns_str = self._get_xruns()
            if xruns_str != self.i18n.tr('not_available'):
                xruns_match = re.search(r'(\d+)', xruns_str)
                if xruns_match:
                    current_xruns = int(xruns_match.group(1))
                    if self._prev_xruns > 0 and current_xruns > self._prev_xruns:
                        delta = current_xruns - self._prev_xruns
                        self._log(self.i18n.tr('xrun_detected').format(delta, current_xruns), "#ff9800", self.i18n.tr('category_audio'))
                    self._prev_xruns = current_xruns
            
            aes67_state = self._get_aes67_state()
            if self._prev_aes67_state is not None and aes67_state != self._prev_aes67_state:
                if aes67_state == self.i18n.tr('enabled'):
                    self._log(self.i18n.tr('aes67_activated'), "#4CAF50", self.i18n.tr('category_aes67'))
                else:
                    self._log(self.i18n.tr('aes67_deactivated'), "#ef5350", self.i18n.tr('category_aes67'))
            self._prev_aes67_state = aes67_state
            
            ptp_state = self._get_ptp_state()
            if self._prev_ptp_state is not None and ptp_state != self._prev_ptp_state:
                self._log(self.i18n.tr('ptp_state_changed').format(self._prev_ptp_state, ptp_state), "#ab47bc", self.i18n.tr('category_ptp'))
            self._prev_ptp_state = ptp_state
            
            if ptp_state == self.i18n.tr('enabled'):
                desync = self._check_ptp_desync()
                if desync:
                    self._log(self.i18n.tr('ptp_desync'), "#ef5350", self.i18n.tr('category_ptp'))
            
            self._check_aes67_logs()
        except Exception:
            pass
    
    def _check_aes67_logs(self):
        try:
            r = subprocess.run(
                ['journalctl', '--user', '-u', 'pipewire', '--since', '2 seconds ago', '--no-pager', '-g', 'aes67|rtp|sap'],
                capture_output=True, text=True, timeout=2
            )
            if r.stdout.strip():
                for line in r.stdout.strip().split('\n'):
                    if line and line not in self._logged_aes67_lines:
                        self._log(line, "#00bcd4", self.i18n.tr('category_aes67'))
                        self._logged_aes67_lines.add(line)
            
            log_file = os.path.expanduser('~/.local/share/pipewire-control-center/aes67.log')
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > self._prev_aes67_log_size:
                        new_lines = lines[self._prev_aes67_log_size:]
                        for line in new_lines:
                            line = line.strip()
                            if line:
                                self._log(line, "#00bcd4", self.i18n.tr('category_aes67'))
                        self._prev_aes67_log_size = len(lines)
        except Exception:
            pass
    
    def _check_ptp_desync(self):
        try:
            r = subprocess.run(
                ['journalctl', '--user', '-u', 'ptp4l', '--since', '2 seconds ago', '--no-pager'],
                capture_output=True, text=True, timeout=2
            )
            return 'offset' in r.stdout and ('master offset' in r.stdout or 'synchronized' not in r.stdout)
        except Exception:
            return False
    
    def refresh(self):
        self._update_sys()
    
    def refresh_language(self):
        self.sys_gb.setTitle(self.i18n.tr('systeme'))
        self.events_gb.setTitle(self.i18n.tr('journal'))
        self.refresh_sys_btn.setText(self.i18n.tr('rafraichir'))
        self.clear_btn.setText(self.i18n.tr('effacer'))
        self.restart_btn.setText(self.i18n.tr('redemarrer_services'))
        self.restart_btn.setToolTip(self.i18n.tr('restart_btn_tooltip'))
        self.clean_btn.setText(self.i18n.tr('nettoyer_configs'))
        self.clean_btn.setToolTip(self.i18n.tr('clean_btn_tooltip'))
        self.auto_scroll_cb.setText(
            self.i18n.tr('auto_scroll_on') if self.auto_scroll_cb.isChecked() else self.i18n.tr('auto_scroll_off')
        )
        self._update_sys()
    
    def shutdown(self):
        self.timer.stop()
