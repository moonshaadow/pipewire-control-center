#!/usr/bin/env python3
"""Onglet de gestion du buffer et de la latence"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QSpinBox, QFormLayout, QMessageBox, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class BufferTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self._init_ui()
        self.load_current()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh_device_buffers)
        self.timer.start(2000)
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # Buffer global
        buf_gb = QGroupBox("Buffer global PipeWire")
        buf_layout = QVBoxLayout()
        
        self.current_buf_lbl = QLabel()
        self.current_buf_lbl.setFont(QFont("Monospace", 11, QFont.Weight.Bold))
        self.current_buf_lbl.setStyleSheet("color: white;")
        buf_layout.addWidget(self.current_buf_lbl)
        
        buf_form = QFormLayout()
        
        self.quantum_spin = QSpinBox()
        self.quantum_spin.setRange(32, 8192)
        self.quantum_spin.setSingleStep(32)
        self.quantum_spin.setSuffix(" échantillons")
        self.quantum_spin.valueChanged.connect(self._update_latency_estimate)
        buf_form.addRow("Buffer global :", self.quantum_spin)
        
        self.min_spin = QSpinBox()
        self.min_spin.setRange(1, 1024)
        self.min_spin.setSuffix(" échantillons")
        buf_form.addRow("Buffer minimum :", self.min_spin)
        
        self.max_spin = QSpinBox()
        self.max_spin.setRange(2048, 16384)
        self.max_spin.setSuffix(" échantillons")
        buf_form.addRow("Buffer maximum :", self.max_spin)
        
        self.latency_lbl = QLabel()
        self.latency_lbl.setFont(QFont("Monospace", 9))
        self.latency_lbl.setStyleSheet("color: #aaa;")
        buf_form.addRow("Latence estimée :", self.latency_lbl)
        
        buf_layout.addLayout(buf_form)
        
        apply_btn = QPushButton("Appliquer")
        apply_btn.clicked.connect(self._apply)
        buf_layout.addWidget(apply_btn)
        
        buf_gb.setLayout(buf_layout)
        layout.addWidget(buf_gb)
        
        # Préréglages
        preset_gb = QGroupBox("Préréglages")
        preset_layout = QHBoxLayout()
        
        presets = [
            ("🎮 Gaming/Live Sound", 128),
            ("🌐 Réseau/AES67", 256),
            ("🎵 Musique", 512),
            ("🎬 Vidéo", 1024),
            ("💻 Bureau", 2048),
        ]
        
        preset_style = """
            QPushButton {
                padding: 6px 12px;
                font-size: 11px;
                min-height: 30px;
                max-height: 30px;
            }
        """
        
        for name, value in presets:
            btn = QPushButton(name)
            btn.setStyleSheet(preset_style)
            btn.clicked.connect(lambda _, v=value: self.quantum_spin.setValue(v))
            preset_layout.addWidget(btn)
        
        preset_gb.setLayout(preset_layout)
        layout.addWidget(preset_gb)
        
        # Buffers des périphériques
        devices_gb = QGroupBox("Buffers ALSA des périphériques")
        devices_layout = QVBoxLayout()
        
        self.devices_tree = QTreeWidget()
        self.devices_tree.setHeaderLabels(["Périphérique", "Buffer ALSA", "Périodes", "Total"])
        self.devices_tree.setColumnWidth(0, 200)
        self.devices_tree.setStyleSheet("QTreeWidget { background-color: #2a2a2a; color: #aaa; }")
        devices_layout.addWidget(self.devices_tree)
        
        note_lbl = QLabel("ℹ Le buffer global doit être cohérent avec le buffer ALSA du périphérique actif.\n"
                          "Un buffer global trop grand par rapport au buffer ALSA augmente la latence sans bénéfice.")
        note_lbl.setFont(QFont("Monospace", 8))
        note_lbl.setStyleSheet("color: #888;")
        note_lbl.setWordWrap(True)
        devices_layout.addWidget(note_lbl)
        
        devices_gb.setLayout(devices_layout)
        layout.addWidget(devices_gb)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def load_current(self):
        try:
            quantum = self.pw.get_quantum()
            min_q = self.pw.get_min_quantum()
            max_q = self.pw.get_max_quantum()
            
            self.quantum_spin.setValue(quantum)
            self.min_spin.setValue(min_q)
            self.max_spin.setValue(max_q)
            
            self.current_buf_lbl.setText(f"Buffer actuel : {quantum} échantillons")
            self._update_latency_estimate()
        except Exception as e:
            print(f"Erreur chargement buffer: {e}")
    
    def load_config(self, config: dict):
        pass
    
    def _update_latency_estimate(self):
        rate = self.pw.get_rate()
        quantum = self.quantum_spin.value()
        latency_ms = (quantum / rate) * 1000
        self.latency_lbl.setText(f"{latency_ms:.1f} ms à {rate} Hz")
    
    def _apply(self):
        quantum = self.quantum_spin.value()
        min_q = self.min_spin.value()
        max_q = self.max_spin.value()
        
        ok = True
        ok &= self.pw.set_quantum(quantum)
        ok &= self.pw.set_min_quantum(min_q)
        ok &= self.pw.set_max_quantum(max_q)
        
        if ok:
            self.current_buf_lbl.setText(f"Buffer actuel : {quantum} échantillons")
            QMessageBox.information(self, "Succès", "Buffer appliqué")
        else:
            QMessageBox.warning(self, "Erreur", "Échec de l'application")
    
    def _refresh_device_buffers(self):
        """Lit les buffers ALSA des périphériques et met à jour l'affichage"""
        try:
            devices = self.pw.get_devices()
            self.devices_tree.clear()
            
            for device in devices:
                data = self.pw._get_pw_dump()
                for item in data:
                    if item.get('id') == device['id']:
                        props = item.get('info', {}).get('props', {})
                        period_size = props.get('api.alsa.period-size', '?')
                        period_num = props.get('api.alsa.period-num', '?')
                        
                        if period_size != '?' and period_num != '?':
                            total = int(period_size) * int(period_num)
                        else:
                            total = '?'
                        
                        item_widget = QTreeWidgetItem([
                            device.get('description', device.get('name', '?')),
                            str(period_size),
                            str(period_num),
                            str(total)
                        ])
                        
                        if device.get('is_default'):
                            font = item_widget.font(0)
                            font.setBold(True)
                            for i in range(4):
                                item_widget.setFont(i, font)
                            item_widget.setText(0, item_widget.text(0) + " ★")
                        
                        self.devices_tree.addTopLevelItem(item_widget)
                        break
        except Exception:
            pass
    
    def shutdown(self):
        self.timer.stop()
