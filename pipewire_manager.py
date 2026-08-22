#!/usr/bin/env python3
"""Gestionnaire PipeWire - Communication via commandes système natives"""
import subprocess
import re
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class PipeWireManager:
    """Interface avec PipeWire via pw-metadata, pw-cli"""
    
    def __init__(self):
        self._check_tools()
        self._cache_file = os.path.join('/tmp', f'pw-dump-cache-{os.getuid()}.json')
        self._cache_duration = 0.2
        self._pw_dump_cache = None
        self._pw_dump_time = 0
    
    def _check_tools(self):
        for tool in ['pw-metadata', 'pw-dump']:
            try:
                subprocess.run(['which', tool], capture_output=True, check=True)
            except subprocess.CalledProcessError:
                raise RuntimeError(f"Outil manquant : {tool}")
    
    def _run(self, cmd: List[str], timeout: int = 5) -> Tuple[bool, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "", "Timeout"
        except Exception as e:
            return False, "", str(e)
    
    def invalidate_cache(self):
        """Force le rafraîchissement du cache pw-dump"""
        self._pw_dump_cache = None
        self._pw_dump_time = 0
        try:
            if os.path.exists(self._cache_file):
                os.remove(self._cache_file)
        except Exception:
            pass
    
    def _get_pw_dump(self) -> List[Dict]:
        now = time.time()
        
        if self._pw_dump_cache is not None and (now - self._pw_dump_time) < self._cache_duration:
            return self._pw_dump_cache
        
        try:
            if os.path.exists(self._cache_file):
                if (now - os.path.getmtime(self._cache_file)) < self._cache_duration:
                    with open(self._cache_file, 'r') as f:
                        self._pw_dump_cache = json.load(f)
                        self._pw_dump_time = now
                        return self._pw_dump_cache
        except Exception:
            pass
        
        ok, out, _ = self._run(['pw-dump'], timeout=3)
        if ok:
            try:
                data = json.loads(out)
                self._pw_dump_cache = data
                self._pw_dump_time = now
                try:
                    with open(self._cache_file, 'w') as f:
                        json.dump(data, f)
                except Exception:
                    pass
                return data
            except Exception:
                pass
        
        if self._pw_dump_cache is not None:
            return self._pw_dump_cache
        return []
    
    def _get_metadata(self, key: str) -> Optional[str]:
        ok, out, _ = self._run(['pw-metadata', '0', key])
        if ok:
            m = re.search(r'value:\s*(.+)', out)
            return m.group(1) if m else None
        return None
    
    def _set_metadata(self, key: str, value: str) -> bool:
        ok, _, _ = self._run(['pw-metadata', '0', key, value])
        return ok
    
    def get_rate(self) -> int:
        v = self._get_metadata('clock.rate')
        return int(v) if v and v.isdigit() else 48000
    
    def set_rate(self, rate: int) -> bool:
        """Change le taux d'échantillonnage courant"""
        return self._set_metadata('clock.rate', str(rate))
    
    def get_quantum(self) -> int:
        v = self._get_metadata('clock.quantum')
        return int(v) if v and v.isdigit() else 1024
    
    def set_quantum(self, size: int) -> bool:
        return self._set_metadata('clock.quantum', str(size))
    
    def get_min_quantum(self) -> int:
        v = self._get_metadata('clock.min-quantum')
        return int(v) if v and v.isdigit() else 32
    
    def set_min_quantum(self, size: int) -> bool:
        return self._set_metadata('clock.min-quantum', str(size))
    
    def get_max_quantum(self) -> int:
        v = self._get_metadata('clock.max-quantum')
        return int(v) if v and v.isdigit() else 8192
    
    def set_max_quantum(self, size: int) -> bool:
        return self._set_metadata('clock.max-quantum', str(size))
    
    def get_devices(self) -> List[Dict]:
        devices = []
        default_sink_name = self._get_default_device_name('Audio/Sink')
        default_source_name = self._get_default_device_name('Audio/Source')
        
        for item in self._get_pw_dump():
            if item.get('type') != 'PipeWire:Interface:Node':
                continue
            info = item.get('info', {})
            props = info.get('props', {})
            media_class = props.get('media.class', '')
            node_name = props.get('node.name', '')
            
            if media_class not in ('Audio/Sink', 'Audio/Source'):
                continue
            if 'monitor' in node_name.lower() or 'dummy' in node_name.lower():
                continue
            
            params = info.get('params', {})
            fmt = (params.get('Format', [{}]) or [{}])[0]
            enum = (params.get('EnumFormat', [{}]) or [{}])[0]
            enum_rate = enum.get('rate', {})
            
            devices.append({
                'id': item.get('id', 0),
                'name': node_name,
                'description': props.get('node.description', node_name),
                'is_default': (
                    (media_class == 'Audio/Sink' and node_name == default_sink_name) or
                    (media_class == 'Audio/Source' and node_name == default_source_name)
                ),
                'type': 'sortie' if 'Sink' in media_class else 'entrée',
                'state': info.get('state', 'idle'),
                'rate': fmt.get('rate', '?'),
                'format': fmt.get('format', '?'),
                'bits': props.get('alsa.resolution_bits'),
                'rates_min': enum_rate.get('min') if isinstance(enum_rate, dict) else None,
                'rates_max': enum_rate.get('max') if isinstance(enum_rate, dict) else None,
                'rates_default': enum_rate.get('default') if isinstance(enum_rate, dict) else enum_rate,
                'priority': int(props.get('priority.session', '0')),
            })
        
        devices.sort(key=lambda d: (not d['is_default'], -d['priority']))
        return devices
    
    def _get_default_device_name(self, media_class: str) -> Optional[str]:
        key = 'default.configured.audio.sink' if 'Sink' in media_class else 'default.configured.audio.source'
        ok, out, _ = self._run(['pw-metadata', '0', key])
        if ok:
            m = re.search(r'"name"\s*:\s*"([^"]+)"', out)
            return m.group(1) if m else None
        return None
    
    def set_default_device(self, device_id: int) -> bool:
        ok, _, _ = self._run(['wpctl', 'set-default', str(device_id)])
        return ok
    
    def get_volume(self, device_id: int) -> Optional[float]:
        data = self._get_pw_dump()
        for item in data:
            if item.get('id') == device_id:
                props_list = item.get('info', {}).get('params', {}).get('Props', [{}])
                if props_list:
                    vols = props_list[0].get('channelVolumes', [])
                    if vols:
                        avg = sum(float(v) for v in vols) / len(vols)
                        return avg ** (1/3)
        return None
    
    def set_volume(self, device_id: int, volume: float) -> bool:
        ok, _, _ = self._run(['wpctl', 'set-volume', str(device_id), f'{volume:.2f}'])
        return ok
    
    def get_stream_volume(self, stream_id: int) -> Optional[float]:
        ok, out, _ = self._run(['wpctl', 'get-volume', str(stream_id)])
        if ok:
            m = re.search(r'Volume:\s*([\d.]+)', out)
            return float(m.group(1)) if m else None
        return None
    
    @property
    def config_file(self) -> Path:
        return Path.home() / '.config' / 'pipewire' / 'pipewire.conf.d' / '10-clock-rates.conf'
    
    def read_allowed_rates(self) -> Optional[List[int]]:
        if not self.config_file.exists():
            return None
        content = self.config_file.read_text()
        m = re.search(r'allowed-rates\s*=\s*\[([^\]]+)\]', content)
        if m:
            return [int(r) for r in m.group(1).split() if r.strip().isdigit()]
        return None
    
    def write_allowed_rates(self, rates: List[int]) -> bool:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        rates_str = ' '.join(str(r) for r in sorted(rates))
        try:
            self.config_file.write_text(
                f'context.properties = {{\n'
                f'    default.clock.allowed-rates = [ {rates_str} ]\n'
                f'}}\n'
            )
            return True
        except Exception:
            return False
    
    def remove_config(self) -> bool:
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            return True
        except Exception:
            return False
    
    def destroy_node(self, node_id: int) -> Tuple[bool, str]:
        """Supprime temporairement un nœud PipeWire"""
        ok, _, err = self._run(['pw-cli', 'destroy', str(node_id)])
        return ok, err
    
    def restart_services(self) -> Tuple[bool, str]:
        ok, out, err = self._run(
            ['systemctl', '--user', 'restart', 'pipewire', 'wireplumber'],
            timeout=10
        )
        return (True, "Services redémarrés") if ok else (False, err or out or "Erreur")
    
    def get_version(self) -> str:
        ok, out, _ = self._run(['pipewire', '--version'])
        if ok:
            m = re.search(r'(\d+\.\d+\.\d+)', out)
            return m.group(1) if m else 'Inconnue'
        return 'Inconnue'
    
    def get_summary(self) -> Dict:
        devices = self.get_devices()
        return {
            'version': self.get_version(),
            'rate': self.get_rate(),
            'quantum': self.get_quantum(),
            'min_quantum': self.get_min_quantum(),
            'max_quantum': self.get_max_quantum(),
            'devices': len(devices),
            'default_sink': next((d for d in devices if d['is_default'] and d['type'] == 'sortie'), None),
            'default_source': next((d for d in devices if d['is_default'] and d['type'] == 'entrée'), None),
            'allowed_rates': self.read_allowed_rates(),
            'has_config': self.config_file.exists(),
        }
