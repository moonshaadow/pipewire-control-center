# PipeWire Control Center

Interface graphique de configuration avancée pour PipeWire.

## Fonctionnalités

- **Audio** : sélection du périphérique, monitoring temps réel (fréquence, format, flux), volume global et par flux avec suramplification (150%)
- **Fréquences** : configuration des taux d'échantillonnage autorisés (switching automatique), redémarrage des services, nettoyage avancé des configurations locales
- **Buffer** : réglage de la taille de buffer et de la latence avec préréglages (Gaming, AES67, Musique, Vidéo, Bureau)
- **Périphériques** : liste détaillée, définition du périphérique par défaut, suppression temporaire de nœuds
- **AES67** : activation/désactivation, configuration émetteur/récepteur, synchronisation PTP (linuxptp), multicast
- **Profils** : sauvegarde et chargement de configurations (rate, quantum, min/max buffer)
- **État** : informations système (version, buffer, latence, xruns), journal des événements (changements de fréquence, périphérique, flux)

## Installation

chmod +x install.sh
./install.sh

Le script détecte automatiquement votre distribution et installe les dépendances nécessaires.

## Dépendances système

| Paquet | Description |
|--------|-------------|
| pipewire | Serveur audio |
| wireplumber | Gestionnaire de session |
| python3-pyqt6 | Interface graphique |
| rsync | Copie des fichiers (installation) |
| linuxptp | Synchronisation PTP (optionnel, pour AES67) |

### Installation par distribution

# Debian / Ubuntu / Linux Mint
sudo apt install pipewire wireplumber python3-pyqt6 rsync

# Fedora
sudo dnf install pipewire wireplumber python3-pyqt6 rsync

# Arch / Manjaro
sudo pacman -S pipewire wireplumber python-pyqt6 rsync

## Emplacements

| Élément | Chemin |
|---------|--------|
| Application | ~/.local/share/pipewire-control-center/ |
| Exécutable | ~/.local/bin/pipewire-control-center |
| Icône | ~/.local/share/icons/hicolor/scalable/apps/pipewire-control-center.svg |
| Lanceur | ~/.local/share/applications/pipewire-control-center.desktop |
| Configuration PipeWire | ~/.config/pipewire/pipewire.conf.d/10-clock-rates.conf |
| Configuration AES67 | ~/.config/pipewire/pipewire.conf.d/20-aes67-session.conf |
| Profils utilisateur | ~/.config/pipewire-control-center/profiles/ |

## Désinstallation

chmod +x uninstall.sh
./uninstall.sh

## Utilisation

Lancez pipewire-control-center depuis le terminal ou via le menu Applications (catégorie Audio).

L'application reste dans la barre système (systray) après fermeture de la fenêtre.

## Configuration manuelle

Le fichier de configuration généré se trouve dans ~/.config/pipewire/pipewire.conf.d/10-clock-rates.conf.

Format :
context.properties = {
    default.clock.allowed-rates = [ 44100 48000 88200 96000 176400 192000 ]
}

## Structure du projet

pipewire-control-center/
├── LICENSE
├── README.md
├── main.py                 # Point d'entrée avec systray
├── pipewire_manager.py     # API PipeWire (pw-metadata, pw-dump, wpctl)
├── config_manager.py       # Gestion des profils JSON
├── install.sh              # Script d'installation
├── uninstall.sh            # Script de désinstallation
├── requirements.txt        # Dépendances Python
├── ui/
│   ├── __init__.py         # Package UI
│   ├── main_window.py      # Fenêtre principale avec navigation
│   ├── audio_tab.py        # Onglet Audio (sorties, entrées, flux)
│   ├── frequency_tab.py    # Onglet Fréquences
│   ├── buffer_tab.py       # Onglet Buffer/Latence
│   ├── devices_tab.py      # Onglet Périphériques
│   ├── aes67_tab.py        # Onglet AES67
│   ├── profiles_tab.py     # Onglet Profils
│   ├── status_tab.py       # Onglet État/Journal
│   └── icon_utils.py       # Utilitaires d'icônes partagés
└── icons/
    ├── hdmi.svg
    ├── headphone.svg
    ├── microphone.svg
    ├── network.svg
    ├── pcc.svg
    ├── pcc-color.svg
    ├── speaker.svg
    ├── usb.svg
    ├── usb-color.svg
    └── pcc.png

## Notes techniques

### Cache pw-dump
L'application utilise un cache de 200ms pour les données pw-dump afin de limiter la charge système. Le cache est invalidé automatiquement lors des actions utilisateur.

### Timers de rafraîchissement
- **Audio** : 200ms (5 FPS) - volumes, flux, états
- **Buffer** : 2s - buffers ALSA
- **AES67** : 2s - statut PTP et configuration
- **État** : 1.5s - changements de fréquence/périphérique/flux

### Permissions
L'application fonctionne en espace utilisateur sans nécessiter de privilèges root, sauf pour l'installation de linuxptp (via pkexec).

## Licence

MIT © 2026 A. Vartanian
