#!/usr/bin/env python3
"""Onglet d'état"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QTextEdit, QPushButton, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from datetime import datetime
import subprocess
import re

class StatusTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self._events = []
        self._prev_rate = None
        self._prev_device = None
        self._prev_stream_ids = set()
        self._init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_changes)
        self.timer.start(1500)
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        layout.addWidget(QLabel(f"PipeWire Control Center v1.0 — PipeWire {self.pw.get_version()}"))
        layout.itemAt(0).widget().setFont(QFont("Monospace", 9))
        layout.itemAt(0).widget().setStyleSheet("color: #666; padding: 4px;")
        layout.itemAt(0).widget().setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Système
        sys_gb = QGroupBox("Système")
        sys_layout = QVBoxLayout()
        self.sys_text = QTextEdit()
        self.sys_text.setReadOnly(True)
        self.sys_text.setFont(QFont("Monospace", 9))
        self.sys_text.setStyleSheet("color: #ccc; padding: 8px; background-color: #2a2a2a; border-radius: 4px; border: none;")
        self.sys_text.setFixedHeight(185)
        self.sys_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._update_sys()
        sys_layout.addWidget(self.sys_text)
        btn = QPushButton("🔄 Rafraîchir")
        btn.clicked.connect(self._update_sys)
        sys_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
        sys_gb.setLayout(sys_layout)
        layout.addWidget(sys_gb)
        
        # Journal
        events_gb = QGroupBox("Journal")
        events_layout = QVBoxLayout()
        self.events_text = QTextEdit()
        self.events_text.setReadOnly(True)
        self.events_text.setFont(QFont("Monospace", 8))
        self.events_text.setStyleSheet("background-color: #1e1e1e; color: #aaa; border: 1px solid #333;")
        self.events_text.setMaximumHeight(300)
        events_layout.addWidget(self.events_text)
        clear_btn = QPushButton("Effacer")
        clear_btn.clicked.connect(lambda: (self._events.clear(), self._refresh_events()))
        events_layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        events_gb.setLayout(events_layout)
        layout.addWidget(events_gb)
        self.setLayout(layout)
    
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
            rates_str = ', '.join(map(str, sorted(rates))) + ' Hz' if rates else "Par défaut (48000 uniquement)"
            
            devices = self.pw.get_devices()
            sinks = sum(1 for d in devices if d['type'] == 'sortie')
            sources = sum(1 for d in devices if d['type'] == 'entrée')
            
            quantum = self.pw.get_quantum()
            rate = self.pw.get_rate()
            latency_ms = (quantum / rate) * 1000 if rate else 0
            
            xruns = "Non disponible"
            try:
                r = subprocess.run(['pw-top', '-b', '-n1'], capture_output=True, text=True, timeout=3)
                total = sum(int(m.group(1)) for m in re.finditer(r'xrun\S*\s+(\d+)', r.stdout))
                xruns = f"{total} (depuis démarrage)"
            except Exception:
                pass
            
            self.sys_text.setHtml(
                f"<b>PipeWire</b>     {pw_v}<br>"
                f"<b>WirePlumber</b>  {wp_v}<br><br>"
                f"<b>Sorties</b>      {sinks} détectée(s)<br>"
                f"<b>Entrées</b>      {sources} détectée(s)<br><br>"
                f"<b>Fréquences</b>   {rates_str}<br><br>"
                f"<b>Buffer</b>       {quantum} éch.<br>"
                f"<b>Latence</b>      {latency_ms:.1f} ms (à {rate} Hz)<br><br>"
                f"<b>Xruns</b>        {xruns}"
            )
        except Exception as e:
            self.sys_text.setHtml(f"Erreur : {e}")
    
    def _log(self, msg, color="#aaa"):
        self._events.append((datetime.now().strftime("%H:%M:%S"), msg, color))
        if len(self._events) > 100: self._events = self._events[-100:]
        self._refresh_events()
    
    def _refresh_events(self):
        self.events_text.setHtml(''.join(
            f'<span style="color:#666;">{t}</span> <span style="color:{c};">{m}</span><br>'
            for t, m, c in self._events
        ))
        self.events_text.verticalScrollBar().setValue(self.events_text.verticalScrollBar().maximum())
    
    def _check_changes(self):
        try:
            s = self.pw.get_summary()
            
            if self._prev_rate is not None and s['rate'] != self._prev_rate:
                self._log(f"Fréquence : {self._prev_rate} → {s['rate']} Hz", "#4fc3f7")
            self._prev_rate = s['rate']
            
            dev = s['default_sink']['description'] if s['default_sink'] else "Aucun"
            if self._prev_device is not None and dev != self._prev_device:
                self._log(f"Périphérique : {self._prev_device} → {dev}", "#81c784")
            self._prev_device = dev
            
            current = {d['name'] for d in self.pw.get_devices() if d['type'] == 'sortie' and d.get('state') == 'running'}
            for name in current - self._prev_stream_ids: self._log(f"Flux démarré : {name}", "#4CAF50")
            for name in self._prev_stream_ids - current: self._log(f"Flux arrêté : {name}", "#ef5350")
            self._prev_stream_ids = current
        except Exception:
            pass
    
    def refresh(self): self._update_sys()
    def shutdown(self): self.timer.stop()
