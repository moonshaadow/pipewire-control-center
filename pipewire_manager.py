#!/usr/bin/env python3
"""PipeWire Manager - Communication via native system commands"""
import subprocess
import re
import json
import time
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ui.logger import Logger

class PipeWireManager:
    """Interface with PipeWire via pw-metadata, pw-cli"""
    
    def __init__(self):
        self.logger = Logger.instance()
        self._check_tools()
        self._cache_file = os.path.join('/tmp', f'pw-dump-cache-{os.getuid()}.json')
        self._cache_duration = 0.2
        self._pw_dump_cache = None
        self._pw_dump_time = 0
        self._pw_dump_hash = None
        self.logger.info("PipeWireManager initialized")
    
    def _check_tools(self):
        for tool in ['pw-metadata', 'pw-dump']:
            try:
                subprocess.run(['which', tool], capture_output=True, check=True)
            except subprocess.CalledProcessError:
                self.logger.error(f"Missing tool: {tool}")
                raise RuntimeError(f"Missing tool: {tool}")
    
    def _run(self, cmd: List[str], timeout: int = 5) -> Tuple[bool, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if r.returncode != 0:
                self.logger.debug(f"Command failed ({r.returncode}): {' '.join(cmd)}")
                self.logger.debug(f"stderr: {r.stderr.strip()}")
            return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout ({timeout}s): {' '.join(cmd)}")
            return False, "", "Timeout"
        except Exception as e:
            self.logger.error(f"Execution error {' '.join(cmd)}: {e}")
            return False, "", str(e)
    
    def invalidate_cache(self):
        """Force pw-dump cache refresh"""
        self._pw_dump_cache = None
        self._pw_dump_time = 0
        try:
            if os.path.exists(self._cache_file):
                os.remove(self._cache_file)
        except Exception as e:
            self.logger.warning(f"Cache invalidation error: {e}")
    
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
        except Exception as e:
            self.logger.debug(f"Cache read error: {e}")
        
        ok, out, _ = self._run(['pw-dump'], timeout=3)
        if ok:
            try:
                data = json.loads(out)
                self._pw_dump_cache = data
                self._pw_dump_time = now
                try:
                    with open(self._cache_file, 'w') as f:
                        json.dump(data, f)
                except Exception as e:
                    self.logger.debug(f"Cache write error: {e}")
                return data
            except Exception as e:
                self.logger.error(f"pw-dump parsing error: {e}")
        
        if self._pw_dump_cache is not None:
            self.logger.debug("Using previous cache (pw-dump failed)")
            return self._pw_dump_cache
        return []

    def has_changed(self) -> bool:
        """Return True if pw-dump has changed since last call
        
        This method compares an MD5 hash of the current pw-dump with
        the previous hash. It only returns True if the data has
        actually changed, avoiding unnecessary UI refreshes.
        """
        data = self._get_pw_dump()
        json_str = json.dumps(data, sort_keys=True)
        current_hash = hashlib.md5(json_str.encode()).hexdigest()
        
        if current_hash != self._pw_dump_hash:
            self._pw_dump_hash = current_hash
            return True
        return False
    
    def _get_metadata(self, key: str) -> Optional[str]:
        ok, out, _ = self._run(['pw-metadata', '0', key])
        if ok:
            m = re.search(r'value:\s*(.+)', out)
            return m.group(1) if m else None
        return None
    
    def _set_metadata(self, key: str, value: str) -> bool:
        ok, _, _ = self._run(['pw-metadata', '0', key, value])
        if ok:
            self.logger.info(f"Metadata changed: {key} = {value}")
        else:
            self.logger.warning(f"Metadata change failed: {key} = {value}")
        return ok
    
    def get_rate(self) -> int:
        v = self._get_metadata('clock.rate')
        return int(v) if v and v.isdigit() else 48000
    
    def set_rate(self, rate: int) -> bool:
        self.logger.info(f"Rate change: {rate} Hz")
        return self._set_metadata('clock.rate', str(rate))
    
    def get_quantum(self) -> int:
        v = self._get_metadata('clock.quantum')
        return int(v) if v and v.isdigit() else 1024
    
    def set_quantum(self, size: int) -> bool:
        self.logger.info(f"Buffer change: {size} samples")
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
            info = item.get('info')
            if info is None:
                continue
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
                'type': 'output' if 'Sink' in media_class else 'input',
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
        self.logger.info(f"Default device change: ID {device_id}")
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
        self.logger.debug(f"Volume change: ID {device_id} -> {volume:.2f}")
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
        """Write configuration file (persistent)"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        rates_str = ' '.join(str(r) for r in sorted(rates))
        try:
            self.config_file.write_text(
                f'context.properties = {{\n'
                f'    default.clock.allowed-rates = [ {rates_str} ]\n'
                f'}}\n'
            )
            self.logger.info(f"Allowed rates written: {rates_str}")
            return True
        except Exception as e:
            self.logger.error(f"Rate write error: {e}")
            return False
    
    def apply_allowed_rates(self, rates: List[int]) -> bool:
        """Apply allowed rates via metadata (immediate, no restart)"""
        rates_str = ','.join(str(r) for r in sorted(rates))
        self.logger.info(f"Immediate rate application: {rates_str}")
        return self._set_metadata('default.clock.allowed-rates', rates_str)
    
    def remove_config(self) -> bool:
        try:
            if self.config_file.exists():
                self.config_file.unlink()
                self.logger.info("Rate configuration removed")
            return True
        except Exception as e:
            self.logger.error(f"Configuration removal error: {e}")
            return False
    
    def destroy_node(self, node_id: int) -> Tuple[bool, str]:
        self.logger.warning(f"Node removal: ID {node_id}")
        ok, _, err = self._run(['pw-cli', 'destroy', str(node_id)])
        return ok, err
    
    def _save_volumes(self) -> Dict[int, float]:
        """Save current device volumes"""
        volumes = {}
        try:
            devices = self.get_devices()
            for device in devices:
                vol = self.get_volume(device['id'])
                if vol is not None:
                    volumes[device['id']] = vol
                    self.logger.debug(f"Volume saved: {device['name']} -> {vol:.2f}")
        except Exception as e:
            self.logger.warning(f"Volume save error: {e}")
        return volumes
    
    def _wait_for_devices(self, timeout: float = 5.0) -> bool:
        """Wait for devices to reappear after restart (polling)"""
        self.logger.info("Waiting for devices...")
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                self.invalidate_cache()
                devices = self.get_devices()
                if len(devices) > 0:
                    self.logger.info(f"Devices detected: {len(devices)}")
                    return True
            except Exception as e:
                self.logger.debug(f"Device detection error: {e}")
            
            time.sleep(0.5)
        
        self.logger.warning(f"Timeout ({timeout}s): devices not detected")
        return False
    
    def _restore_volumes(self, volumes: Dict[int, float]):
        """Restore volumes after restart with polling"""
        if not volumes:
            return
        
        if not self._wait_for_devices(timeout=5.0):
            self.logger.warning("Cannot restore volumes: devices not detected")
            return
        
        try:
            devices = self.get_devices()
            restored = 0
            for device in devices:
                if device['id'] in volumes:
                    vol = volumes[device['id']]
                    if self.set_volume(device['id'], vol):
                        restored += 1
                        self.logger.info(f"Volume restored: {device['name']} -> {vol:.2f}")
            
            self.logger.info(f"Volumes restored: {restored}/{len(volumes)}")
        except Exception as e:
            self.logger.warning(f"Volume restore error: {e}")
    
    def restart_services(self) -> Tuple[bool, str]:
        """Gentle restart: WirePlumber stopped first, PipeWire socket preserved, volumes restored"""
        self.logger.info("Gentle restart of PipeWire + WirePlumber services")
        
        # 1. Save volumes
        volumes = self._save_volumes()
        self.logger.info(f"Volumes saved: {len(volumes)}")
        
        # 2. Stop WirePlumber first
        self.logger.info("Stopping WirePlumber...")
        ok_wp_stop, _, err_wp_stop = self._run(
            ['systemctl', '--user', 'stop', 'wireplumber'],
            timeout=5
        )
        if not ok_wp_stop:
            self.logger.warning(f"WirePlumber stop error: {err_wp_stop}")
        
        # 3. Restart PipeWire WITHOUT touching the socket
        self.logger.info("Restarting PipeWire (socket preserved)...")
        ok_pw, _, err_pw = self._run(
            ['systemctl', '--user', 'restart', 'pipewire.service'],
            timeout=10
        )
        
        # 4. Restart WirePlumber
        self.logger.info("Restarting WirePlumber...")
        ok_wp_start, _, err_wp_start = self._run(
            ['systemctl', '--user', 'start', 'wireplumber'],
            timeout=10
        )
        
        # 5. Invalidate cache
        self.invalidate_cache()
        
        # 6. Restore volumes with polling
        if volumes:
            self.logger.info(f"Restoring {len(volumes)} volumes...")
            self._restore_volumes(volumes)
        
        if ok_pw and ok_wp_start:
            self.logger.info("Services restarted successfully")
            return True, "Services restarted"
        else:
            error_msg = err_pw or err_wp_start or "Unknown error"
            self.logger.error(f"Service restart error: {error_msg}")
            return False, error_msg
    
    def get_version(self) -> str:
        ok, out, _ = self._run(['pipewire', '--version'])
        if ok:
            m = re.search(r'(\d+\.\d+\.\d+)', out)
            return m.group(1) if m else 'Unknown'
        return 'Unknown'
    
    def get_summary(self) -> Dict:
        devices = self.get_devices()
        return {
            'version': self.get_version(),
            'rate': self.get_rate(),
            'quantum': self.get_quantum(),
            'min_quantum': self.get_min_quantum(),
            'max_quantum': self.get_max_quantum(),
            'devices': len(devices),
            'default_sink': next((d for d in devices if d['is_default'] and d['type'] == 'output'), None),
            'default_source': next((d for d in devices if d['is_default'] and d['type'] == 'input'), None),
            'allowed_rates': self.read_allowed_rates(),
            'has_config': self.config_file.exists(),
        }