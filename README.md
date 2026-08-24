# PipeWire Control Center (PCC)
<<<<<<< HEAD

Interface graphique de configuration avancée pour PipeWire, avec notamment gestion fine des samplerates et du buffer, et prise en charge d'AES67.

MISES EN GARDE : 

Cette application a été developpée dans un but personnel, à (très) grand renfort d'IA.

PCC a été testé et est fonctionnnel sous Linux Mint 22.3, Cinnamon/XFCE, avec Pipewire 1.0.5 / Wireplumber 0.4.17 .

Les procédures d'installation ci-dessous sont génériques et fournies à titre indicatif seuleument, elles peuvent nécessiter des ajustements.

A VENIR :

- Personnalisation de l'interface,

- Meilleur support d'AES67,

- Prise en charge d'AVB, dans la mesure du possible,

- Gestion de profils audio permettant égalisation et compression en fonction du contexte

=======

Advanced graphical configuration interface for PipeWire, featuring fine-grained control of sample rates and buffer sizes, as well as AES67 support.
>>>>>>> da07098 (Ajout du système i18n complet (FR/EN), configuration UI, comportement fermeture, journal enrichi AES67/PTP)

WARNINGS:

This application was developed for personal use, with significant assistance from AI.

PCC has been tested and is functional on Linux Mint 22.3, Cinnamon/XFCE, with PipeWire 1.0.5 / WirePlumber 0.4.17.

The installation procedures below are generic and provided for informational purposes only; they may require adjustments.

COMING SOON:

- UI customization,

- Improved AES67 support,

- AVB support, as far as possible,

- Audio profile management with equalization and compression based on context


## Features

- **Audio**: device selection, real-time monitoring (frequency, format, streams), global and per-stream volume with 150% boost
- **Frequencies**: configuration of allowed sample rates (automatic switching), service restart, advanced cleanup of local configurations
- **Buffer**: buffer size and latency adjustment with presets (Gaming, AES67, Music, Video, Desktop)
- **Devices**: detailed list, default device selection, temporary node removal
- **AES67**: enable/disable, sender/receiver configuration, PTP synchronization (linuxptp), multicast
- **Profiles**: save and load configurations (rate, quantum, min/max buffer)
- **Status**: system information (version, buffer, latency, xruns), event log (frequency, device, and stream changes)

## Installation

chmod +x install.sh
./install.sh

The script automatically detects your distribution and installs the required dependencies.

## System Dependencies

| Package | Description |
|---------|-------------|
| pipewire | Audio server |
| wireplumber | Session manager |
| python3-pyqt6 | Graphical interface |
| rsync | File copying (installation) |
| linuxptp | PTP synchronization (optional, for AES67) |

### Installation by Distribution

# Debian / Ubuntu / Linux Mint
sudo apt install pipewire wireplumber python3-pyqt6 rsync

# Fedora
sudo dnf install pipewire wireplumber python3-pyqt6 rsync

# Arch / Manjaro
sudo pacman -S pipewire wireplumber python-pyqt6 rsync

## Locations

| Item | Path |
|------|------|
| Application | ~/.local/share/pipewire-control-center/ |
| Executable | ~/.local/bin/pipewire-control-center |
| Icon | ~/.local/share/icons/hicolor/scalable/apps/pipewire-control-center.svg |
| Launcher | ~/.local/share/applications/pipewire-control-center.desktop |
| PipeWire Configuration | ~/.config/pipewire/pipewire.conf.d/10-clock-rates.conf |
| AES67 Configuration | ~/.config/pipewire/pipewire.conf.d/20-aes67-session.conf |
| User Profiles | ~/.config/pipewire-control-center/profiles/ |

## Uninstallation

chmod +x uninstall.sh
./uninstall.sh

## Usage

Launch pipewire-control-center from the terminal or via the Applications menu (Audio category).

The application remains in the system tray after the window is closed.

## Manual Configuration

The generated configuration file is located at ~/.config/pipewire/pipewire.conf.d/10-clock-rates.conf.

Format:
context.properties = {
    default.clock.allowed-rates = [ 44100 48000 88200 96000 176400 192000 ]
}

## Project Structure

pipewire-control-center/
├── LICENSE
├── README.md
├── main.py                 # Entry point with system tray
├── pipewire_manager.py     # PipeWire API (pw-metadata, pw-dump, wpctl)
├── config_manager.py       # JSON profile management
├── install.sh              # Installation script
├── uninstall.sh            # Uninstallation script
├── requirements.txt        # Python dependencies
├── ui/
│   ├── __init__.py         # UI package
│   ├── main_window.py      # Main window with navigation
│   ├── audio_tab.py        # Audio tab (outputs, inputs, streams)
│   ├── frequency_tab.py    # Frequencies tab
│   ├── buffer_tab.py       # Buffer/Latency tab
│   ├── devices_tab.py      # Devices tab
│   ├── aes67_tab.py        # AES67 tab
│   ├── profiles_tab.py     # Profiles tab
│   ├── status_tab.py       # Status/Log tab
│   └── icon_utils.py       # Shared icon utilities
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

## Technical Notes

### pw-dump Cache
The application uses a 200ms cache for pw-dump data to limit system load. The cache is automatically invalidated upon user actions.

### Refresh Timers
- **Audio**: 200ms (5 FPS) - volumes, streams, states
- **Buffer**: 2s - ALSA buffers
- **AES67**: 2s - PTP status and configuration
- **Status**: 1.5s - frequency/device/stream changes

### Permissions
The application runs in user space without requiring root privileges, except for installing linuxptp (via pkexec).

## License

MIT © 2026 A. Vartanian
