#!/usr/bin/env python3
"""Onglet de gestion du buffer et de la latence"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QSpinBox, QFormLayout, QMessageBox, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from .i18n import I18n
from .logger import Logger

class BufferTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self._init_ui()
        self.load_current()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh_device_buffers)
        self.timer.start(2000)
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # Buffer global
        self.buf_gb = QGroupBox(self.i18n.tr('buffer_global'))
        buf_layout = QVBoxLayout()
        
        self.current_buf_lbl = QLabel()
        self.current_buf_lbl.setFont(QFont("Monospace", 11, QFont.Weight.Bold))
        self.current_buf_lbl.setStyleSheet("color: white;")
        buf_layout.addWidget(self.current_buf_lbl)
        
        buf_form = QFormLayout()
        
        self.quantum_spin = QSpinBox()
        self.quantum_spin.setRange(32, 8192)
        self.quantum_spin.setSingleStep(32)
        self.quantum_spin.setSuffix(" " + self.i18n.tr('samples'))
        self.quantum_spin.valueChanged.connect(self._on_quantum_changed)
        buf_form.addRow(self.i18n.tr('buffer_global') + ":", self.quantum_spin)
        
        self.min_spin = QSpinBox()
        self.min_spin.setRange(1, 8192)
        self.min_spin.setSuffix(" " + self.i18n.tr('samples'))
        self.min_spin.valueChanged.connect(self._on_min_changed)
        buf_form.addRow(self.i18n.tr('buffer_minimum'), self.min_spin)
        
        self.max_spin = QSpinBox()
        self.max_spin.setRange(2048, 16384)
        self.max_spin.setSuffix(" " + self.i18n.tr('samples'))
        self.max_spin.valueChanged.connect(self._on_max_changed)
        buf_form.addRow(self.i18n.tr('buffer_maximum'), self.max_spin)
        
        self.latency_lbl = QLabel()
        self.latency_lbl.setFont(QFont("Monospace", 9))
        self.latency_lbl.setStyleSheet("color: #aaa;")
        buf_form.addRow(self.i18n.tr('latence_estimee'), self.latency_lbl)
        
        # Label de fréquence actuelle
        self.rate_lbl = QLabel()
        self.rate_lbl.setFont(QFont("Monospace", 9))
        self.rate_lbl.setStyleSheet("color: #aaa;")
        buf_form.addRow(self.i18n.tr('frequence'), self.rate_lbl)
        
        buf_layout.addLayout(buf_form)
        
        self.apply_btn = QPushButton(self.i18n.tr('apply'))
        self.apply_btn.clicked.connect(self._apply)
        buf_layout.addWidget(self.apply_btn)
        
        self.buf_gb.setLayout(buf_layout)
        layout.addWidget(self.buf_gb)
        
        # Préréglages
        self.preset_gb = QGroupBox(self.i18n.tr('presets'))
        preset_layout = QHBoxLayout()
        
        presets = [
            (self.i18n.tr('preset_gaming'), 128),
            (self.i18n.tr('preset_network'), 256),
            (self.i18n.tr('preset_music'), 512),
            (self.i18n.tr('preset_video'), 1024),
            (self.i18n.tr('preset_desktop'), 2048),
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
        
        self.preset_gb.setLayout(preset_layout)
        layout.addWidget(self.preset_gb)
        
        # Buffers des périphériques
        self.devices_gb = QGroupBox(self.i18n.tr('buffers_alsa'))
        devices_layout = QVBoxLayout()
        
        self.devices_tree = QTreeWidget()
        self.devices_tree.setHeaderLabels([
            self.i18n.tr('description'), "ALSA", self.i18n.tr('channels'), "Total"
        ])
        self.devices_tree.setColumnWidth(0, 200)
        self.devices_tree.setStyleSheet("QTreeWidget { background-color: #2a2a2a; color: #aaa; }")
        devices_layout.addWidget(self.devices_tree)
        
        note_lbl = QLabel(self.i18n.tr('buffer_note'))
        note_lbl.setFont(QFont("Monospace", 8))
        note_lbl.setStyleSheet("color: #888;")
        note_lbl.setWordWrap(True)
        devices_layout.addWidget(note_lbl)
        
        self.devices_gb.setLayout(devices_layout)
        layout.addWidget(self.devices_gb)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def showEvent(self, event):
        """Démarre le timer quand l'onglet devient visible"""
        super().showEvent(event)
        self.timer.start(2000)
        self._refresh_device_buffers()
    
    def hideEvent(self, event):
        """Arrête le timer quand l'onglet n'est plus visible"""
        super().hideEvent(event)
        self.timer.stop()
    
    def load_current(self):
        try:
            quantum = self.pw.get_quantum()
            min_q = self.pw.get_min_quantum()
            max_q = self.pw.get_max_quantum()
            
            self.quantum_spin.blockSignals(True)
            self.min_spin.blockSignals(True)
            self.max_spin.blockSignals(True)
            
            self.quantum_spin.setValue(quantum)
            self.min_spin.setValue(min_q)
            self.max_spin.setValue(max_q)
            
            self.quantum_spin.blockSignals(False)
            self.min_spin.blockSignals(False)
            self.max_spin.blockSignals(False)
            
            self.current_buf_lbl.setText(self.i18n.tr('buffer_actuel').format(quantum))
            self._update_latency_estimate()
            self._update_rate_label()
        except Exception as e:
            self.logger.error(f"Erreur chargement buffer: {e}")
    
    def load_config(self, config: dict):
        """Charge les paramètres depuis un profil"""
        try:
            if 'quantum' in config:
                self.quantum_spin.setValue(config['quantum'])
            if 'min_quantum' in config:
                self.min_spin.setValue(config['min_quantum'])
            if 'max_quantum' in config:
                self.max_spin.setValue(config['max_quantum'])
            self._update_latency_estimate()
            self._update_rate_label()
        except Exception as e:
            self.logger.error(f"Erreur chargement config buffer: {e}")
    
    def _on_quantum_changed(self, value):
        """Met à jour les contraintes quand le quantum change"""
        # Ajuster le min si nécessaire
        if value < self.min_spin.value():
            self.min_spin.setValue(value)
        # Ajuster le max si nécessaire
        if value > self.max_spin.value():
            self.max_spin.setValue(value)
        
        self._update_latency_estimate()
    
    def _on_min_changed(self, value):
        """Met à jour les contraintes quand le min change"""
        # Le max doit être supérieur au min
        if value >= self.max_spin.value():
            self.max_spin.setValue(value + 1)
        self._update_latency_estimate()
    
    def _on_max_changed(self, value):
        """Met à jour les contraintes quand le max change"""
        # Le min doit être inférieur au max
        if value <= self.min_spin.value():
            self.min_spin.setValue(value - 1)
        self._update_latency_estimate()
    
    def _validate_ranges(self) -> bool:
        """Valide la cohérence des plages"""
        quantum = self.quantum_spin.value()
        min_q = self.min_spin.value()
        max_q = self.max_spin.value()
        
        if min_q >= max_q:
            QMessageBox.warning(
                self, self.i18n.tr('error_title'),
                f"Le minimum ({min_q}) doit être inférieur au maximum ({max_q})"
            )
            return False
        
        if quantum < min_q:
            QMessageBox.warning(
                self, self.i18n.tr('error_title'),
                f"Le buffer global ({quantum}) est inférieur au minimum ({min_q})"
            )
            return False
        
        if quantum > max_q:
            QMessageBox.warning(
                self, self.i18n.tr('error_title'),
                f"Le buffer global ({quantum}) est supérieur au maximum ({max_q})"
            )
            return False
        
        return True
    
    def _update_latency_estimate(self):
        rate = self.pw.get_rate()
        quantum = self.quantum_spin.value()
        latency_ms = (quantum / rate) * 1000
        self.latency_lbl.setText(f"{latency_ms:.1f} {self.i18n.tr('milliseconds')}")
    
    def _update_rate_label(self):
        rate = self.pw.get_rate()
        self.rate_lbl.setText(f"{rate} {self.i18n.tr('hz')}")
    
    def _apply(self):
        if not self._validate_ranges():
            return
        
        quantum = self.quantum_spin.value()
        min_q = self.min_spin.value()
        max_q = self.max_spin.value()
        
        ok = True
        ok &= self.pw.set_quantum(quantum)
        ok &= self.pw.set_min_quantum(min_q)
        ok &= self.pw.set_max_quantum(max_q)
        
        if ok:
            self.current_buf_lbl.setText(self.i18n.tr('buffer_actuel').format(quantum))
            self.logger.info(f"Buffer appliqué: quantum={quantum}, min={min_q}, max={max_q}")
            QMessageBox.information(self, self.i18n.tr('success'), self.i18n.tr('buffer_applied'))
        else:
            self.logger.error("Échec de l'application du buffer")
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('buffer_apply_error'))
    
    def _refresh_device_buffers(self):
        """Lit les buffers ALSA des périphériques et met à jour l'affichage"""
        try:
            data = self.pw._get_pw_dump()
            devices = self.pw.get_devices()
            
            # Créer un dictionnaire pour O(1) au lieu de O(n²)
            data_by_id = {item.get('id'): item for item in data}
            
            self.devices_tree.clear()
            
            for device in devices:
                item_data = data_by_id.get(device['id'])
                if not item_data:
                    continue
                
                props = item_data.get('info', {}).get('props', {})
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
        except Exception as e:
            self.logger.error(f"Erreur refresh buffers ALSA: {e}")
    
    def refresh_language(self):
        self.buf_gb.setTitle(self.i18n.tr('buffer_global'))
        self.preset_gb.setTitle(self.i18n.tr('presets'))
        self.devices_gb.setTitle(self.i18n.tr('buffers_alsa'))
        self.apply_btn.setText(self.i18n.tr('apply'))
        self.quantum_spin.setSuffix(" " + self.i18n.tr('samples'))
        self.min_spin.setSuffix(" " + self.i18n.tr('samples'))
        self.max_spin.setSuffix(" " + self.i18n.tr('samples'))
        self.devices_tree.setHeaderLabels([
            self.i18n.tr('description'), "ALSA", self.i18n.tr('channels'), "Total"
        ])
        self._update_latency_estimate()
        self._update_rate_label()
    
    def shutdown(self):
        self.timer.stop()
