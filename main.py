#!/usr/bin/env python3
"""PipeWire Control Center"""
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from ui.main_window import MainWindow
from ui.logger import Logger

def main():
    # Initialiser le logger
    logger = Logger.instance()
    logger.info("=== Démarrage de PipeWire Control Center ===")
    
    app = QApplication(sys.argv)
    app.setApplicationName("PipeWire Control Center")
    app.setStyle('Fusion')
    app.setQuitOnLastWindowClosed(False)
    
    # Icône systray
    icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
    systray_icon = os.path.join(icons_dir, "pcc.svg")
    
    try:
        window = MainWindow()
        
        tray = QSystemTrayIcon()
        if os.path.exists(systray_icon):
            tray.setIcon(QIcon(systray_icon))
        else:
            tray.setIcon(QIcon.fromTheme('audio-card'))
        tray.setToolTip("PipeWire Control Center")
        
        menu = QMenu()
        show_action = QAction("Afficher")
        show_action.triggered.connect(lambda: (window.show(), window.raise_()))
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("Quitter")
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)
        
        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason: window.show() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        tray.show()
        
        window.show()
        logger.info("Application démarrée")
        return app.exec()
    except RuntimeError as e:
        logger.critical(f"Erreur Runtime: {e}")
        QMessageBox.critical(None, "Erreur", str(e))
    except Exception as e:
        logger.exception(f"Erreur inattendue: {e}")
        QMessageBox.critical(None, "Erreur", f"Erreur inattendue : {e}")
    return 1

if __name__ == "__main__":
    sys.exit(main())
