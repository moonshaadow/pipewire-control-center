#!/usr/bin/env python3
"""Onglet FX : égaliseur et compresseur avec profils - contrôle EasyEffects"""
import os
import json
import socket
import subprocess
import signal
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QPushButton, QLabel, QSlider, QMessageBox, QComboBox,
    QInputDialog, QFormLayout, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .i18n import I18n
from .logger import Logger

class EasyEffectsClient:
    """Client pour communiquer avec le serveur local d'EasyEffects"""
    
    def __init__(self):
        self.logger = Logger.instance()
        self.socket_path = os.path.join(
            os.environ.get('XDG_RUNTIME_DIR', '/tmp'),
            'EasyEffectsServer'
        )
    
    def _send(self, command, wait_response=True):
        """Envoie une commande au serveur local"""
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(self.socket_path)
            client.send(command.encode())
            response = b""
            if wait_response:
                client.settimeout(2)
                try:
                    response = client.recv(4096)
                except socket.timeout:
                    pass
            client.close()
            return response.decode() if response else None
        except FileNotFoundError:
            self.logger.debug("EasyEffects n'est pas lancé")
            return None
        except ConnectionRefusedError:
            self.logger.debug("EasyEffects a refusé la connexion")
            return None
        except Exception as e:
            self.logger.error(f"Erreur communication EasyEffects: {e}")
            return None
    
    def is_running(self):
        """Vérifie si EasyEffects est lancé"""
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(self.socket_path)
            client.close()
            return True
        except Exception:
            return False
    
    def show_window(self):
        """Affiche la fenêtre EasyEffects"""
        return self._send("show_window\n", wait_response=False)
    
    def hide_window(self):
        """Cache la fenêtre EasyEffects"""
        return self._send("hide_window\n", wait_response=False)
    
    def quit_app(self):
        """Quitte EasyEffects"""
        return self._send("quit_app\n", wait_response=False)
    
    def load_preset(self, pipeline_type, preset_name):
        """Charge un preset (pipeline_type: 'input' ou 'output')"""
        command = f"load_preset:{pipeline_type}:{preset_name}\n"
        return self._send(command)
    
    def set_global_bypass(self, bypass):
        """Active/désactive le bypass global"""
        state = 1 if bypass else 0
        command = f"global_bypass:{state}\n"
        return self._send(command)
    
    def get_global_bypass(self):
        """Obtient l'état du bypass global"""
        response = self._send("get_global_bypass\n")
        if response:
            return response.strip() == "1"
        return None
    
    def get_last_loaded_preset(self, pipeline_type):
        """Obtient le dernier preset chargé"""
        command = f"get_last_loaded_preset:{pipeline_type}\n"
        return self._send(command)


class FXTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self.i18n = I18n.instance()
        self.logger = Logger.instance()
        
        # Client EasyEffects
        self.ee_client = EasyEffectsClient()
        self.ee_process = None
        
        # Fichiers
        self.profiles_file = Path.home() / '.config' / 'pipewire-control-center' / 'fx-profiles.json'
        self.fx_mode_file = Path.home() / '.config' / 'pipewire-control-center' / 'fx-mode.json'
        
        # Mode FX
        self.fx_mode = self._load_fx_mode()
        
        # Profils par défaut
        self.default_profiles = {
            "Profil 1": {
                "name": "Profil 1",
                "eq_enabled": False,
                "comp_enabled": False,
                "eq_gains": [0.0] * 10,
                "comp_attack": 0.75,
                "comp_release": 0.5,
                "comp_gain": 12.0,
                "comp_mode": 1,
                "comp_measure": 1,
                "ee_preset_name": ""
            },
            "Profil 2": {
                "name": "Profil 2",
                "eq_enabled": False,
                "comp_enabled": False,
                "eq_gains": [0.0] * 10,
                "comp_attack": 0.75,
                "comp_release": 0.5,
                "comp_gain": 12.0,
                "comp_mode": 1,
                "comp_measure": 1,
                "ee_preset_name": ""
            },
            "Profil 3": {
                "name": "Profil 3",
                "eq_enabled": False,
                "comp_enabled": False,
                "eq_gains": [0.0] * 10,
                "comp_attack": 0.75,
                "comp_release": 0.5,
                "comp_gain": 12.0,
                "comp_mode": 1,
                "comp_measure": 1,
                "ee_preset_name": ""
            }
        }
        
        self.profiles = self._load_profiles()
        self.current_profile_name = list(self.profiles.keys())[0]
        
        # Fréquences fixes pour EQ10X2
        self.eq_frequencies = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        
        self._init_ui()
        self._load_profile_to_ui()
        self._update_ee_status()
    
    def _load_fx_mode(self):
        try:
            if self.fx_mode_file.exists():
                with open(self.fx_mode_file, 'r') as f:
                    data = json.load(f)
                    return data.get('mode', 'internal')
        except Exception:
            pass
        return 'internal'
    
    def _save_fx_mode(self):
        try:
            self.fx_mode_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.fx_mode_file, 'w') as f:
                json.dump({'mode': self.fx_mode}, f, indent=2)
        except Exception:
            pass
    
    def _load_profiles(self):
        try:
            if self.profiles_file.exists():
                with open(self.profiles_file, 'r') as f:
                    profiles = json.load(f)
                    result = self.default_profiles.copy()
                    result.update(profiles)
                    return result
        except Exception as e:
            self.logger.error(f"Erreur chargement profils FX: {e}")
        return self.default_profiles.copy()
    
    def _save_profiles(self):
        try:
            self.profiles_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.profiles_file, 'w') as f:
                json.dump(self.profiles, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde profils FX: {e}")
            return False
    
    def _init_ui(self):
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        self.main_gb = QGroupBox("FX")
        main_layout = QVBoxLayout()
        
        # Statut EasyEffects
        self.ee_status_lbl = QLabel("")
        self.ee_status_lbl.setFont(QFont("Monospace", 8))
        self.ee_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.ee_status_lbl)
        
        # Mode FX
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel(self.i18n.tr('fx_mode') + ":"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(self.i18n.tr('fx_mode_internal'), 'internal')
        self.mode_combo.addItem(self.i18n.tr('fx_mode_easyeffects'), 'easyeffects')
        idx = self.mode_combo.findData(self.fx_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        main_layout.addLayout(mode_layout)
        
        # Case à cocher globale
        self.enable_cb = QCheckBox(self.i18n.tr('fx_enable'))
        self.enable_cb.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        self.enable_cb.toggled.connect(self._update_enabled_state)
        main_layout.addWidget(self.enable_cb)
        
        # Sélecteur de profil
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel(self.i18n.tr('fx_profile') + ":"))
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(list(self.profiles.keys()))
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        profile_layout.addWidget(self.profile_combo)
        
        rename_btn = QPushButton(self.i18n.tr('fx_rename'))
        rename_btn.clicked.connect(self._rename_profile)
        profile_layout.addWidget(rename_btn)
        
        main_layout.addLayout(profile_layout)
        
        # Nom du preset EasyEffects
        ee_preset_layout = QHBoxLayout()
        ee_preset_layout.addWidget(QLabel(self.i18n.tr('fx_ee_preset') + ":"))
        
        self.ee_preset_combo = QComboBox()
        self.ee_preset_combo.setEditable(True)
        self.ee_preset_combo.setPlaceholderText("Nom du preset EasyEffects")
        ee_preset_layout.addWidget(self.ee_preset_combo, 1)
        
        main_layout.addLayout(ee_preset_layout)
        
        # Zone EQ
        self.eq_gb = QGroupBox(self.i18n.tr('fx_eq_title'))
        eq_layout = QVBoxLayout()
        
        self.eq_enable_cb = QCheckBox(self.i18n.tr('fx_eq_enable'))
        self.eq_enable_cb.toggled.connect(self._update_enabled_state)
        eq_layout.addWidget(self.eq_enable_cb)
        
        eq_sliders_layout = QHBoxLayout()
        eq_sliders_layout.setSpacing(4)
        
        self.eq_sliders = []
        for i, freq in enumerate(self.eq_frequencies):
            band_layout = QVBoxLayout()
            
            value_label = QLabel("0.0")
            value_label.setFont(QFont("Monospace", 7))
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            band_layout.addWidget(value_label)
            
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-480, 240)
            slider.setValue(0)
            slider.setFixedHeight(100)
            slider.setFixedWidth(25)
            slider.valueChanged.connect(lambda v, idx=i: self._on_eq_slider_moved(idx, v))
            band_layout.addWidget(slider, 0, Qt.AlignmentFlag.AlignHCenter)
            
            freq_text = f"{freq}" if freq < 1000 else f"{freq/1000:.1f}k"
            freq_label = QLabel(freq_text)
            freq_label.setFont(QFont("Monospace", 7))
            freq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            band_layout.addWidget(freq_label)
            
            eq_sliders_layout.addLayout(band_layout)
            self.eq_sliders.append((slider, value_label))
        
        eq_layout.addLayout(eq_sliders_layout)
        self.eq_gb.setLayout(eq_layout)
        main_layout.addWidget(self.eq_gb)
        
        # Zone Compresseur
        self.comp_gb = QGroupBox(self.i18n.tr('fx_comp_title'))
        comp_layout = QVBoxLayout()
        
        self.comp_enable_cb = QCheckBox(self.i18n.tr('fx_comp_enable'))
        self.comp_enable_cb.toggled.connect(self._update_enabled_state)
        comp_layout.addWidget(self.comp_enable_cb)
        
        comp_form = QFormLayout()
        
        self.attack_slider = QSlider(Qt.Orientation.Horizontal)
        self.attack_slider.setRange(0, 100)
        self.attack_slider.setValue(75)
        self.attack_slider.valueChanged.connect(self._on_comp_param_changed)
        self.attack_label = QLabel("0.75")
        attack_row = QHBoxLayout()
        attack_row.addWidget(self.attack_slider, 1)
        attack_row.addWidget(self.attack_label)
        comp_form.addRow(self.i18n.tr('fx_attack'), attack_row)
        
        self.release_slider = QSlider(Qt.Orientation.Horizontal)
        self.release_slider.setRange(0, 100)
        self.release_slider.setValue(50)
        self.release_slider.valueChanged.connect(self._on_comp_param_changed)
        self.release_label = QLabel("0.50")
        release_row = QHBoxLayout()
        release_row.addWidget(self.release_slider, 1)
        release_row.addWidget(self.release_label)
        comp_form.addRow(self.i18n.tr('fx_release'), release_row)
        
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(-120, 360)
        self.gain_slider.setValue(120)
        self.gain_slider.valueChanged.connect(self._on_comp_param_changed)
        self.gain_label = QLabel("12.0 dB")
        gain_row = QHBoxLayout()
        gain_row.addWidget(self.gain_slider, 1)
        gain_row.addWidget(self.gain_label)
        comp_form.addRow(self.i18n.tr('fx_makeup'), gain_row)
        
        comp_layout.addLayout(comp_form)
        self.comp_gb.setLayout(comp_layout)
        main_layout.addWidget(self.comp_gb)
        
        # Boutons
        btn_layout = QHBoxLayout()
        
        # Bouton Lancer EasyEffects
        self.launch_btn = QPushButton(self.i18n.tr('fx_launch_easyeffects'))
        self.launch_btn.clicked.connect(self._launch_easyeffects)
        self.launch_btn.setStyleSheet("QPushButton { padding: 8px; font-weight: bold; }")
        btn_layout.addWidget(self.launch_btn)
        
        # Bouton Ouvrir fenêtre
        self.show_btn = QPushButton(self.i18n.tr('fx_show_easyeffects'))
        self.show_btn.clicked.connect(self._show_easyeffects)
        self.show_btn.setEnabled(False)
        btn_layout.addWidget(self.show_btn)
        
        main_layout.addLayout(btn_layout)
        
        # Bouton Appliquer le preset
        self.apply_btn = QPushButton(self.i18n.tr('fx_apply_preset'))
        self.apply_btn.clicked.connect(self._apply_preset)
        self.apply_btn.setStyleSheet("QPushButton { padding: 8px; font-weight: bold; }")
        main_layout.addWidget(self.apply_btn)
        
        self.main_gb.setLayout(main_layout)
        scroll_layout.addWidget(self.main_gb)
        scroll_layout.addStretch()
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        
        outer = QVBoxLayout(self)
        outer.addWidget(scroll_area)
        
        self._update_mode_ui()
        self._update_enabled_state()
    
    def _on_mode_changed(self, idx):
        self.fx_mode = self.mode_combo.currentData()
        self._save_fx_mode()
        self._update_mode_ui()
        self._update_enabled_state()
    
    def _update_mode_ui(self):
        is_internal = self.fx_mode == 'internal'
        self.eq_gb.setVisible(is_internal)
        self.comp_gb.setVisible(is_internal)
        self.profile_combo.setVisible(is_internal)
    
    def _update_enabled_state(self):
        fx = self.enable_cb.isChecked()
        eq = self.eq_enable_cb.isChecked()
        comp = self.comp_enable_cb.isChecked()
        is_internal = self.fx_mode == 'internal'
        
        self.apply_btn.setEnabled(fx)
        self.launch_btn.setEnabled(True)  # Toujours actif
        self.profile_combo.setEnabled(fx and is_internal)
        self.eq_enable_cb.setEnabled(fx and is_internal)
        self.comp_enable_cb.setEnabled(fx and is_internal)
        
        if is_internal:
            for slider, label in self.eq_sliders:
                slider.setEnabled(fx and eq)
                label.setEnabled(fx and eq)
            
            self.attack_slider.setEnabled(fx and comp)
            self.release_slider.setEnabled(fx and comp)
            self.gain_slider.setEnabled(fx and comp)
    
    def _update_ee_status(self):
        """Met à jour le statut EasyEffects"""
        if self.ee_client.is_running():
            self.ee_status_lbl.setText("● EasyEffects : " + self.i18n.tr('fx_ee_running'))
            self.ee_status_lbl.setStyleSheet("color: #4CAF50;")
            self.show_btn.setEnabled(True)
        else:
            self.ee_status_lbl.setText("○ EasyEffects : " + self.i18n.tr('fx_ee_not_running'))
            self.ee_status_lbl.setStyleSheet("color: #888;")
            self.show_btn.setEnabled(False)
    
    def _launch_easyeffects(self):
        """Lance EasyEffects en arrière-plan"""
        if self.ee_client.is_running():
            QMessageBox.information(self, "EasyEffects", self.i18n.tr('fx_ee_already_running'))
            self._update_ee_status()
            return
        
        try:
            result = subprocess.run(['which', 'easyeffects'], capture_output=True, text=True)
            if result.returncode != 0:
                QMessageBox.warning(
                    self, self.i18n.tr('error_title'),
                    self.i18n.tr('fx_easyeffects_not_found')
                )
                return
            
            self.ee_process = subprocess.Popen(
                ['easyeffects', '--hide-window'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            self.logger.info(f"EasyEffects lancé (PID {self.ee_process.pid})")
            
            # Attendre que le serveur local soit prêt
            import time
            time.sleep(3)
            self._update_ee_status()
        except Exception as e:
            self.logger.error(f"Erreur lancement EasyEffects: {e}")
            QMessageBox.warning(self, self.i18n.tr('error_title'), str(e))
    
    def _show_easyeffects(self):
        """Affiche la fenêtre EasyEffects"""
        self.ee_client.show_window()
    
    def _apply_preset(self):
        """Applique le preset EasyEffects"""
        if not self.ee_client.is_running():
            QMessageBox.warning(
                self, self.i18n.tr('error_title'),
                self.i18n.tr('fx_ee_not_running_msg')
            )
            return
        
        preset_name = self.ee_preset_combo.currentText().strip()
        if not preset_name:
            QMessageBox.warning(
                self, self.i18n.tr('error_title'),
                self.i18n.tr('fx_ee_preset_name_required')
            )
            return
        
        # Charger le preset dans EasyEffects (pipeline sortie)
        self.ee_client.load_preset('output', preset_name)
        
        # Sauvegarder le nom du preset dans le profil
        self._save_current_profile()
        profile = self.profiles.get(self.current_profile_name)
        if profile:
            profile['ee_preset_name'] = preset_name
            self._save_profiles()
        
        QMessageBox.information(
            self, self.i18n.tr('success'),
            self.i18n.tr('fx_ee_preset_applied').format(name=preset_name)
        )
    
    def _on_profile_changed(self, name):
        self._save_current_profile()
        self.current_profile_name = name
        self._load_profile_to_ui()
    
    def _on_eq_slider_moved(self, idx, value):
        _, label = self.eq_sliders[idx]
        label.setText(f"{value/10:.1f}")
    
    def _on_comp_param_changed(self):
        self.attack_label.setText(f"{self.attack_slider.value()/100:.2f}")
        self.release_label.setText(f"{self.release_slider.value()/100:.2f}")
        self.gain_label.setText(f"{self.gain_slider.value()/10:.1f} dB")
    
    def _save_current_profile(self):
        if not self.current_profile_name:
            return
        p = self.profiles.get(self.current_profile_name)
        if not p:
            return
        p['eq_enabled'] = self.eq_enable_cb.isChecked()
        p['comp_enabled'] = self.comp_enable_cb.isChecked()
        p['eq_gains'] = [s.value()/10.0 for s, _ in self.eq_sliders]
        p['comp_attack'] = self.attack_slider.value() / 100.0
        p['comp_release'] = self.release_slider.value() / 100.0
        p['comp_gain'] = self.gain_slider.value() / 10.0
        p['ee_preset_name'] = self.ee_preset_combo.currentText().strip()
        self._save_profiles()
    
    def _load_profile_to_ui(self):
        p = self.profiles.get(self.current_profile_name)
        if not p:
            return
        
        self.eq_enable_cb.blockSignals(True)
        self.comp_enable_cb.blockSignals(True)
        self.eq_enable_cb.setChecked(p.get('eq_enabled', False))
        self.comp_enable_cb.setChecked(p.get('comp_enabled', False))
        self.eq_enable_cb.blockSignals(False)
        self.comp_enable_cb.blockSignals(False)
        
        # Charger le nom du preset EasyEffects
        self.ee_preset_combo.setCurrentText(p.get('ee_preset_name', ''))
        
        gains = p.get('eq_gains', [0.0]*10)
        for i, (slider, label) in enumerate(self.eq_sliders):
            if i < len(gains):
                slider.blockSignals(True)
                slider.setValue(int(gains[i]*10))
                slider.blockSignals(False)
                label.setText(f"{gains[i]:.1f}")
        
        self.attack_slider.blockSignals(True)
        self.attack_slider.setValue(int(p.get('comp_attack', 0.75)*100))
        self.attack_slider.blockSignals(False)
        
        self.release_slider.blockSignals(True)
        self.release_slider.setValue(int(p.get('comp_release', 0.5)*100))
        self.release_slider.blockSignals(False)
        
        self.gain_slider.blockSignals(True)
        self.gain_slider.setValue(int(p.get('comp_gain', 12.0)*10))
        self.gain_slider.blockSignals(False)
        
        self._on_comp_param_changed()
        self._update_enabled_state()
    
    def _rename_profile(self):
        old = self.current_profile_name
        new, ok = QInputDialog.getText(self, self.i18n.tr('fx_rename'), self.i18n.tr('fx_profile_name'), text=old)
        if ok and new and new != old:
            self.profiles[new] = self.profiles.pop(old)
            self.profiles[new]['name'] = new
            self._save_profiles()
            self.profile_combo.blockSignals(True)
            self.profile_combo.clear()
            self.profile_combo.addItems(list(self.profiles.keys()))
            self.profile_combo.setCurrentText(new)
            self.profile_combo.blockSignals(False)
            self.current_profile_name = new
    
    def refresh_language(self):
        self.enable_cb.setText(self.i18n.tr('fx_enable'))
        self.eq_gb.setTitle(self.i18n.tr('fx_eq_title'))
        self.comp_gb.setTitle(self.i18n.tr('fx_comp_title'))
        self.eq_enable_cb.setText(self.i18n.tr('fx_eq_enable'))
        self.comp_enable_cb.setText(self.i18n.tr('fx_comp_enable'))
        self.launch_btn.setText(self.i18n.tr('fx_launch_easyeffects'))
        self.show_btn.setText(self.i18n.tr('fx_show_easyeffects'))
        self.apply_btn.setText(self.i18n.tr('fx_apply_preset'))
    
    def shutdown(self):
        if self.ee_process:
            try:
                os.killpg(os.getpgid(self.ee_process.pid), signal.SIGTERM)
            except Exception:
                pass
            self.ee_process = None
