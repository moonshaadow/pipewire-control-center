#!/usr/bin/env python3
"""Helpers MPRIS pour les métadonnées des flux"""
import subprocess
import re
import time


class MprisHelper:
    """Gestion des métadonnées MPRIS"""
    
    def __init__(self, logger):
        self.logger = logger
        self._cache = {}
        self._cache_time = 0
    
    def get_players(self):
        """Liste les lecteurs MPRIS disponibles"""
        now = time.time()
        if now - self._cache_time < 5:
            return list(self._cache.keys())
        
        try:
            result = subprocess.run(
                ['dbus-send', '--session', '--print-reply',
                 '--dest=org.freedesktop.DBus',
                 '/org/freedesktop/DBus',
                 'org.freedesktop.DBus.ListNames'],
                capture_output=True, text=True, timeout=3
            )
            players = []
            for line in result.stdout.split('\n'):
                if 'org.mpris.MediaPlayer2' in line:
                    match = re.search(r'org\.mpris\.MediaPlayer2\.([^"]+)"', line)
                    if match:
                        players.append(match.group(1).strip())
            
            self._cache = {p: True for p in players}
            self._cache_time = now
            return players
        except Exception:
            return list(self._cache.keys())
    
    def get_metadata(self, player_name):
        """Récupère les métadonnées d'un lecteur MPRIS"""
        try:
            result = subprocess.run(
                ['dbus-send', '--session', '--print-reply',
                 f'--dest=org.mpris.MediaPlayer2.{player_name}',
                 '/org/mpris/MediaPlayer2',
                 'org.freedesktop.DBus.Properties.Get',
                 'string:org.mpris.MediaPlayer2.Player',
                 'string:Metadata'],
                capture_output=True, text=True, timeout=3
            )
            
            metadata = {}
            title_match = re.search(r'xesam:title.*?string\s+"([^"]+)"', result.stdout, re.DOTALL)
            artist_match = re.search(r'xesam:artist.*?string\s+"([^"]+)"', result.stdout, re.DOTALL)
            album_match = re.search(r'xesam:album.*?string\s+"([^"]+)"', result.stdout, re.DOTALL)
            
            if title_match:
                metadata['media_title'] = title_match.group(1)
            if artist_match:
                metadata['media_artist'] = artist_match.group(1)
            if album_match:
                metadata['media_album'] = album_match.group(1)
            
            return metadata
        except Exception:
            return {}
    
    def get_metadata_for_app(self, app_name):
        """Cherche les métadonnées pour une application donnée"""
        app_lower = app_name.lower()
        
        players = self.get_players()
        
        for player in players:
            player_lower = player.lower()
            if app_lower in player_lower or player_lower in app_lower:
                return self.get_metadata(player)
        
        if '.' in app_lower:
            binary_guess = app_lower.split('.')[-1]
            for player in players:
                player_lower = player.lower()
                if binary_guess in player_lower or player_lower in binary_guess:
                    return self.get_metadata(player)
        
        cleaned = re.sub(r'[\[\]]', ' ', app_lower)
        cleaned = re.sub(r'\bpipewire\b|\balsa\b|\bplayback\b|\bcapture\b', '', cleaned)
        cleaned = cleaned.strip()
        
        if cleaned and cleaned != app_lower:
            for player in players:
                if cleaned in player.lower():
                    return self.get_metadata(player)
        
        return {}
