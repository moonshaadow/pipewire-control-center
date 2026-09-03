#!/usr/bin/env python3
"""Onglet Réglages : fréquences et buffer"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QStackedWidget,
    QButtonGroup, QPushButton, QLabel, QMessageBox, QListWidget,
    QListWidgetItem, QInputDialog, QSpinBox, QFormLayout, QTreeWidget,
    QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from .i18n import I18n
from .logger import Logger

class SettingsTab(QWidget):
    """Onglet Réglages avec sous-onglets Fréquences et Buffer"""
    
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        self._init_ui()
        self._load_current_buffer()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Boutons de sous-onglets
        sub_nav_layout = QHBoxLayout()
        sub_nav_layout.setContentsMargins(0, 4, 0, 4)
        sub_nav_layout.setSpacing(1)
        sub_nav_layout.addStretch()
        
        self.sub_btn_group = QButtonGroup()
        self.sub_btn_group.setExclusive(True)
        
        self.sub_buttons = []
        sub_pages = [
            (self.i18n.tr('frequencies'), 0),
            (self.i18n.tr('buffer'), 1)
        ]
        
        for text, idx in sub_pages:
            btn = QPushButton(text)
            btn.setCheckable(True)
            self.sub_btn_group.addButton(btn, idx)
            sub_nav_layout.addWidget(btn)
            self.sub_buttons.append(btn)
        
        sub_nav_layout.addStretch()
        layout.addLayout(sub_nav_layout)
        
        # Stack pour les pages
        self.sub_stack = QStackedWidget()
        
        # Page Fréquences
        self.freq_page = QWidget()
        freq_layout = QVBoxLayout()
        freq_layout.setSpacing(15)
        
        self.config_gb = QGroupBox(self.i18n.tr('frequences_autorisees'))
        config_layout = QVBoxLayout()
        
        config_layout.addWidget(QLabel(self.i18n.tr('frequencies_description')))
        
        self.rates_list = QListWidget()
        self.rates_list.setMaximumHeight(150)
        self._populate_rates_list()
        config_layout.addWidget(self.rates_list)
        
        btn_layout = QHBoxLayout()
        
        self.add_rate_btn = QPushButton(self.i18n.tr('ajouter'))
        self.add_rate_btn.clicked.connect(self._add_rate)
        btn_layout.addWidget(self.add_rate_btn)
        
        self.remove_rate_btn = QPushButton(self.i18n.tr('supprimer'))
        self.remove_rate_btn.clicked.connect(self._remove_rate)
        btn_layout.addWidget(self.remove_rate_btn)
        
        config_layout.addLayout(btn_layout)
        
        save_layout = QHBoxLayout()
        self.save_config_btn = QPushButton(self.i18n.tr('enregistrer'))
        self.save_config_btn.clicked.connect(self._save_config)
        save_layout.addWidget(self.save_config_btn)
        
        self.remove_config_btn = QPushButton(self.i18n.tr('supprimer_config'))
        self.remove_config_btn.clicked.connect(self._remove_config)
        save_layout.addWidget(self.remove_config_btn)
        
        config_layout.addLayout(save_layout)
        self.config_gb.setLayout(config_layout)
        freq_layout.addWidget(self.config_gb)
        freq_layout.addStretch()
        self.freq_page.setLayout(freq_layout)
        self.sub_stack.addWidget(self.freq_page)
        
        # Page Buffer
        self.buffer_page = QWidget()
        buffer_layout = QVBoxLayout()
        buffer_layout.setSpacing(12)
        
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
        
        self.rate_lbl = QLabel()
        self.rate_lbl.setFont(QFont("Monospace", 9))
        self.rate_lbl.setStyleSheet("color: #aaa;")
        buf_form.addRow(self.i18n.tr('frequence'), self.rate_lbl)
        
        buf_layout.addLayout(buf_form)
        
        self.apply_btn = QPushButton(self.i18n.tr('apply'))
        self.apply_btn.clicked.connect(self._apply_buffer)
        buf_layout.addWidget(self.apply_btn)
        
        self.buf_gb.setLayout(buf_layout)
        buffer_layout.addWidget(self.buf_gb)
        
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
        buffer_layout.addWidget(self.preset_gb)
        
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
        buffer_layout.addWidget(self.devices_gb)
        buffer_layout.addStretch()
        self.buffer_page.setLayout(buffer_layout)
        self.sub_stack.addWidget(self.buffer_page)
        
        layout.addWidget(self.sub_stack)
        
        # Sélection par défaut
        self.sub_buttons[0].setChecked(True)
        self.sub_btn_group.idClicked.connect(self.sub_stack.setCurrentIndex)
        
        # Timer pour le refresh des buffers ALSA
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh_device_buffers)
        
        self.setLayout(layout)
    
    def set_theme_colors(self, colors):
        """Applique les couleurs du thème aux sous-onglets"""
        sub_btn_style = f"""
            QPushButton {{
                background-color: {colors['btn_bg']};
                color: {colors['btn_text']};
                border: 1px solid {colors['titlebar_bg']};
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 13px;
                margin: 0 1px;
            }}
            QPushButton:checked {{
                background-color: {colors['btn_checked']};
                color: {colors['btn_text_checked']};
                border-color: {colors['btn_checked']};
            }}
            QPushButton:hover:!checked {{
                background-color: {colors['btn_hover']};
                color: {colors['btn_text_hover']};
            }}
        """
        for btn in self.sub_buttons:
            btn.setStyleSheet(sub_btn_style)
    
    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start(2000)
        self._refresh_device_buffers()
    
    def hideEvent(self, event):
        super().hideEvent(event)
        self.timer.stop()
    
    def _populate_rates_list(self):
        self.rates_list.clear()
        rates = self.pw.read_allowed_rates()
        if rates:
            for r in rates:
                item = QListWidgetItem(f"{r} Hz")
                item.setData(Qt.ItemDataRole.UserRole, r)
                self.rates_list.addItem(item)
        else:
            for r in [44100, 48000, 88200, 96000, 176400, 192000]:
                item = QListWidgetItem(f"{r} Hz")
                item.setData(Qt.ItemDataRole.UserRole, r)
                self.rates_list.addItem(item)
    
    def _add_rate(self):
        all_rates = ['44100', '48000', '88200', '96000', '176400', '192000']
        current = {self.rates_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.rates_list.count())}
        available = [r for r in all_rates if int(r) not in current]
        
        if not available:
            QMessageBox.information(self, self.i18n.tr('info'), self.i18n.tr('all_frequencies_added'))
            return
        
        rate, ok = QInputDialog.getItem(self, self.i18n.tr('add_frequency'), self.i18n.tr('frequency'), available, 0, False)
        if ok and rate:
            item = QListWidgetItem(f"{rate} Hz")
            item.setData(Qt.ItemDataRole.UserRole, int(rate))
            self.rates_list.addItem(item)
    
    def _remove_rate(self):
        item = self.rates_list.currentItem()
        if item:
            self.rates_list.takeItem(self.rates_list.row(item))
        else:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('select_frequency'))
    
    def _save_config(self):
        rates = [self.rates_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.rates_list.count())]
        if not rates:
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('list_empty'))
            return
        
        if self.pw.write_allowed_rates(rates):
            self.pw.apply_allowed_rates(rates)
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                rates_str = ', '.join(str(r) for r in rates)
                main_window.statusBar().showMessage(
                    self.i18n.tr('frequencies_saved').format(rates=rates_str),
                    3000
                )
        else:
            self.logger.error("Échec écriture fréquences")
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('config_error'))
    
    def _remove_config(self):
        reply = QMessageBox.question(
            self,
            self.i18n.tr('confirmation'),
            self.i18n.tr('remove_config_confirm'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.pw.remove_config():
                self._populate_rates_list()
                main_window = self.window()
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(
                        self.i18n.tr('frequency_config_removed'),
                        3000
                    )
            else:
                QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('config_error'))
    
    def _load_current_buffer(self):
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
    
    def _on_quantum_changed(self, value):
        if value < self.min_spin.value():
            self.min_spin.setValue(value)
        if value > self.max_spin.value():
            self.max_spin.setValue(value)
        self._update_latency_estimate()
    
    def _on_min_changed(self, value):
        if value >= self.max_spin.value():
            self.max_spin.setValue(value + 1)
        self._update_latency_estimate()
    
    def _on_max_changed(self, value):
        if value <= self.min_spin.value():
            self.min_spin.setValue(value - 1)
        self._update_latency_estimate()
    
    def _validate_ranges(self) -> bool:
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
    
    def _apply_buffer(self):
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
            main_window = self.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(
                    self.i18n.tr('buffer_applied_status').format(quantum=quantum),
                    3000
                )
        else:
            self.logger.error("Échec de l'application du buffer")
            QMessageBox.warning(self, self.i18n.tr('error_title'), self.i18n.tr('buffer_apply_error'))
    
    def _refresh_device_buffers(self):
        try:
            data = self.pw._get_pw_dump()
            devices = self.pw.get_devices()
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
    
    def load_current(self):
        self._load_current_buffer()
    
    def load_config(self, config: dict):
        if 'quantum' in config:
            self.quantum_spin.setValue(config['quantum'])
        if 'min_quantum' in config:
            self.min_spin.setValue(config['min_quantum'])
        if 'max_quantum' in config:
            self.max_spin.setValue(config['max_quantum'])
        self._update_latency_estimate()
        self._update_rate_label()
    
    def refresh_language(self):
        self.sub_buttons[0].setText(self.i18n.tr('frequencies'))
        self.sub_buttons[1].setText(self.i18n.tr('buffer'))
        self.config_gb.setTitle(self.i18n.tr('frequences_autorisees'))
        self.add_rate_btn.setText(self.i18n.tr('ajouter'))
        self.remove_rate_btn.setText(self.i18n.tr('supprimer'))
        self.save_config_btn.setText(self.i18n.tr('enregistrer'))
        self.remove_config_btn.setText(self.i18n.tr('supprimer_config'))
        self.buf_gb.setTitle(self.i18n.tr('buffer_global'))
        self.preset_gb.setTitle(self.i18n.tr('presets'))
        self.devices_gb.setTitle(self.i18n.tr('buffers_alsa'))
        self.apply_btn.setText(self.i18n.tr('apply'))
        self._update_latency_estimate()
        self._update_rate_label()
    
    def shutdown(self):
        self.timer.stop()
