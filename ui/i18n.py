#!/usr/bin/env python3
"""Translation support using QTranslator"""
import os
from pathlib import Path
from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo
from PyQt6.QtWidgets import QApplication


class I18n:
    """Manages QTranslator instances for PCC and Qt native strings"""
    
    _instance = None
    _translator = None
    _qt_translator = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def setup(cls, app: QApplication, locale: str = None):
        """Install translators on the QApplication"""
        cls._translator = QTranslator()
        cls._qt_translator = QTranslator()
        
        if locale is None:
            qlocale = QLocale.system()
        else:
            qlocale = QLocale(locale)
        
        translations_dir = Path(__file__).parent.parent / 'i18n'
        
        pcc_loaded = cls._translator.load(qlocale, 'pcc', '_', str(translations_dir))
        
        qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        cls._qt_translator.load(qlocale, 'qt', '_', qt_path)
        
        app.installTranslator(cls._qt_translator)
        app.installTranslator(cls._translator)
        
        return pcc_loaded
    
    @classmethod
    def remove(cls, app: QApplication):
        """Remove translators from the QApplication"""
        if cls._qt_translator:
            app.removeTranslator(cls._qt_translator)
        if cls._translator:
            app.removeTranslator(cls._translator)