#!/usr/bin/env python3
"""Gestion des profils de configuration"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class ConfigManager:
    def __init__(self):
        self.profiles_dir = Path.home() / '.config' / 'pipewire-control-center' / 'profiles'
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, name: str, config: Dict) -> bool:
        try:
            (self.profiles_dir / f"{name.lower().replace(' ', '_')}.json").write_text(
                json.dumps({'name': name, 'created': datetime.now().isoformat(), 'config': config}, indent=2)
            )
            return True
        except: return False
    
    def load(self, name: str) -> Optional[Dict]:
        f = self.profiles_dir / f"{name.lower().replace(' ', '_')}.json"
        if f.exists():
            try: return json.loads(f.read_text()).get('config')
            except: pass
        return None
    
    def list_profiles(self) -> List[str]:
        profiles = []
        for f in self.profiles_dir.glob('*.json'):
            try: profiles.append(json.loads(f.read_text()).get('name', f.stem))
            except: profiles.append(f.stem)
        return sorted(profiles)
    
    def delete(self, name: str) -> bool:
        f = self.profiles_dir / f"{name.lower().replace(' ', '_')}.json"
        if f.exists():
            try: f.unlink(); return True
            except: pass
        return False
