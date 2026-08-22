#!/usr/bin/env python3
# ui/frequency_tab.py
"""Onglet de configuration des fréquences et redémarrage"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QMessageBox, QListWidget,
    QListWidgetItem, QInputDialog
)
from PyQt6.QtCore import Qt
from pathlib import Path

class FrequencyTab(QWidget):
    def __init__(self, pw):
        super().__init__()
        self.pw = pw
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Fréquences autorisées
        config_gb = QGroupBox("Fréquences autorisées")
        config_layout = QVBoxLayout()
        
        config_layout.addWidget(QLabel(
            "Définit les fréquences que PipeWire peut utiliser.\n"
            "Le matériel utilisera la plus adaptée au flux en cours.\n"
            "Survit aux redémarrages.\n"
            "Fichier : ~/.config/pipewire/pipewire.conf.d/10-clock-rates.conf"
        ))
        
        self.rates_list = QListWidget()
        self.rates_list.setMaximumHeight(150)
        self._populate_rates_list()
        config_layout.addWidget(self.rates_list)
        
        btn_layout = QHBoxLayout()
        
        self.add_rate_btn = QPushButton("+ Ajouter")
        self.add_rate_btn.clicked.connect(self._add_rate)
        btn_layout.addWidget(self.add_rate_btn)
        
        self.remove_rate_btn = QPushButton("- Supprimer")
        self.remove_rate_btn.clicked.connect(self._remove_rate)
        btn_layout.addWidget(self.remove_rate_btn)
        
        config_layout.addLayout(btn_layout)
        
        save_layout = QHBoxLayout()
        self.save_config_btn = QPushButton("💾 Enregistrer")
        self.save_config_btn.clicked.connect(self._save_config)
        save_layout.addWidget(self.save_config_btn)
        
        self.remove_config_btn = QPushButton("🗑 Supprimer la configuration")
        self.remove_config_btn.clicked.connect(self._remove_config)
        save_layout.addWidget(self.remove_config_btn)
        
        config_layout.addLayout(save_layout)
        config_gb.setLayout(config_layout)
        layout.addWidget(config_gb)
        
        # Redémarrage des services
        restart_gb = QGroupBox("Appliquer les changements")
        restart_layout = QVBoxLayout()
        restart_layout.addWidget(QLabel(
            "Redémarre PipeWire et WirePlumber pour prendre en compte\n"
            "la nouvelle configuration des fréquences autorisées.\n\n"
            "⚠️ Toute lecture audio sera interrompue."
        ))
        self.restart_btn = QPushButton("🔄 Redémarrer PipeWire + WirePlumber")
        self.restart_btn.setStyleSheet("QPushButton { color: #ff9800; font-weight: bold; padding: 8px; }")
        self.restart_btn.clicked.connect(self._restart_services)
        restart_layout.addWidget(self.restart_btn)
        restart_gb.setLayout(restart_layout)
        layout.addWidget(restart_gb)
        
        # Nettoyage avancé
        clean_gb = QGroupBox("Nettoyage avancé")
        clean_layout = QVBoxLayout()
        clean_layout.addWidget(QLabel(
            "Supprime tous les fichiers de configuration locaux\n"
            "pouvant causer des conflits.\n\n"
            "Cela concerne :\n"
            "• ~/.config/pipewire/pipewire.conf.d/\n"
            "• ~/.config/wireplumber/main.lua.d/\n\n"
            "ℹ️ Le fichier pipewire.conf.d/10-clock-rates.conf\n"
            "   suffit pour le switching automatique des fréquences.\n"
            "   Tout autre fichier au même endroit, ou dans\n"
            "   wireplumber/main.lua.d/, peut interférer et bloquer\n"
            "   le changement automatique de fréquence."
        ))
        self.clean_btn = QPushButton("🧹 Nettoyer toutes les configurations locales")
        self.clean_btn.setStyleSheet("QPushButton { color: #ef5350; font-weight: bold; padding: 8px; }")
        self.clean_btn.clicked.connect(self._clean_all_configs)
        clean_layout.addWidget(self.clean_btn)
        clean_gb.setLayout(clean_layout)
        layout.addWidget(clean_gb)
        
        layout.addStretch()
        self.setLayout(layout)
    
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
            QMessageBox.information(self, "Info", "Toutes les fréquences sont déjà dans la liste")
            return
        
        rate, ok = QInputDialog.getItem(self, "Ajouter", "Fréquence :", available, 0, False)
        if ok and rate:
            item = QListWidgetItem(f"{rate} Hz")
            item.setData(Qt.ItemDataRole.UserRole, int(rate))
            self.rates_list.addItem(item)
    
    def _remove_rate(self):
        item = self.rates_list.currentItem()
        if item:
            self.rates_list.takeItem(self.rates_list.row(item))
        else:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une fréquence à supprimer")
    
    def _save_config(self):
        rates = [self.rates_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.rates_list.count())]
        if not rates:
            QMessageBox.warning(self, "Erreur", "La liste ne peut pas être vide")
            return
        
        if self.pw.write_allowed_rates(rates):
            QMessageBox.information(self, "Succès", 
                "Configuration enregistrée.\n\n"
                "Redémarrez les services pour appliquer les changements."
            )
        else:
            QMessageBox.warning(self, "Erreur", "Impossible d'écrire la configuration")
    
    def _remove_config(self):
        reply = QMessageBox.question(self, "Confirmation",
            "Supprimer la configuration persistante ?\n"
            "Les valeurs par défaut seront rétablies au prochain redémarrage.")
        if reply == QMessageBox.StandardButton.Yes:
            if self.pw.remove_config():
                self._populate_rates_list()
                QMessageBox.information(self, "Succès", "Configuration supprimée")
    
    def _restart_services(self):
        reply = QMessageBox.question(self, "Confirmation",
            "Redémarrer PipeWire et WirePlumber ?\n\n"
            "⚠️ Toute lecture audio sera interrompue.")
        if reply == QMessageBox.StandardButton.Yes:
            ok, msg = self.pw.restart_services()
            if ok:
                QMessageBox.information(self, "Succès", msg)
            else:
                QMessageBox.warning(self, "Erreur", msg)
    
    def _clean_all_configs(self):
        # Vérifier ce qui va être supprimé
        pipewire_dir = Path.home() / '.config' / 'pipewire' / 'pipewire.conf.d'
        wireplumber_dir = Path.home() / '.config' / 'wireplumber' / 'main.lua.d'
        
        files_to_delete = []
        if pipewire_dir.exists():
            files_to_delete.extend(pipewire_dir.glob('*.conf'))
        if wireplumber_dir.exists():
            files_to_delete.extend(wireplumber_dir.glob('*.lua'))
        
        if not files_to_delete:
            QMessageBox.information(self, "Info", 
                "Aucune configuration locale trouvée.\n"
                "Rien à nettoyer."
            )
            return
        
        # Afficher ce qui va être supprimé
        file_list = '\n'.join(f"  • {f}" for f in files_to_delete)
        
        reply = QMessageBox.question(self, "Confirmation",
            f"Les fichiers suivants vont être supprimés :\n\n"
            f"{file_list}\n\n"
            f"⚠️ Cette action est irréversible.\n"
            f"Les services seront redémarrés automatiquement.\n\n"
            f"Continuer ?"
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Supprimer les fichiers
        errors = []
        for f in files_to_delete:
            try:
                f.unlink()
            except Exception as e:
                errors.append(str(e))
        
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
        try:
            pipewire_config_dir = pipewire_dir.parent
            if pipewire_config_dir.exists():
                pipewire_config_dir.rmdir()
        except Exception:
            pass
        try:
            wireplumber_config_dir = wireplumber_dir.parent
            if wireplumber_config_dir.exists():
                wireplumber_config_dir.rmdir()
        except Exception:
            pass
        
        if errors:
            QMessageBox.warning(self, "Erreur", 
                f"Erreurs lors de la suppression :\n" + '\n'.join(errors)
            )
        else:
            # Redémarrer les services
            ok, msg = self.pw.restart_services()
            if ok:
                self._populate_rates_list()
                QMessageBox.information(self, "Succès", 
                    "Toutes les configurations locales ont été supprimées.\n"
                    "Services redémarrés avec la configuration par défaut."
                )
            else:
                QMessageBox.warning(self, "Erreur", 
                    f"Fichiers supprimés, mais erreur au redémarrage :\n{msg}"
                )
