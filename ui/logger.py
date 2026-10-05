#!/usr/bin/env python3
"""Centralized logging system for PipeWire Control Center"""
import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

class Logger:
    """Singleton for centralized log management"""
    _instance = None
    
    def __init__(self):
        self.log_dir = Path.home() / '.local' / 'share' / 'pipewire-control-center' / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / 'app.log'
        
        # Main logger configuration
        self.logger = logging.getLogger('PipeWireControlCenter')
        self.logger.setLevel(logging.DEBUG)
        
        # Avoid duplicates if already configured
        if not self.logger.handlers:
            # File handler with rotation
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=1_000_000,  # 1 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # Detailed format
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(module)s.%(funcName)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)
    
    def get_log_file(self):
        return str(self.log_file)
    
    def clear_logs(self):
        """Clear all log files"""
        try:
            for f in self.log_dir.glob('*.log*'):
                f.unlink()
            self.logger.info("Logs cleared")
        except Exception as e:
            self.logger.error(f"Error clearing logs: {e}")