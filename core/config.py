import json
import os
from typing import Any, Optional

class Config:
    _instance: Optional['Config'] = None
    CONFIG_FILE = "config.json"
    
    DEFAULT_CONFIG = {
        'thread_count': 5,
        'sound_enabled': True,
        'use_proxies': False,
        'proxy_type': 'http',
        'last_invite_code': '',
        'new_password': '',
        'email_api_keys': {
            '007hotmail': '',
            'zeus': '',
            'lution': ''
        },
        'humanizer': {
            'set_avatar': True,
            'set_display_name': True,
            'set_bio': True,
            'pfp_folder': 'humanizer_pfps'
        },
        'phone_verifier': {
            'captcha_solver': 'onyx',
            'captcha_api_keys': {
                'onyx': '',
                'hcaptchasolver': '',
                'voidsolver': '',
                'anysolver': '',
                'nopecha': '',
                'yescaptcha': ''
            },
            'sms_service': '5sim',
            'sms_api_keys': {
                '5sim': '',
                'smsbower': '',
                'herosms': '',
                'tigersms': ''
            },
            'sms_country': {
                '5sim': 'indonesia',
                'smsbower': '73',
                'herosms': '0',
                'tigersms': '0'
            }
        },
        'window': {
            'width': 1200,
            'height': 800,
            'x': 100,
            'y': 100
        },
        'updates': {
            'server_url': '',
            'auto_check': False,
            'user_id': ''
        }
    }

    def __init__(self, config_path: str = CONFIG_FILE):
        self._path = config_path
        self._data = self.DEFAULT_CONFIG.copy()
        self._load()

    @classmethod
    def instance(cls) -> 'Config':
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reset(self):
        self._data = self.DEFAULT_CONFIG.copy()
        self.save()

    def _load(self):
        """Load config from file, merge with defaults."""
        if os.path.exists(self._path):
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self._merge(self._data, saved)
            except (json.JSONDecodeError, Exception):
                pass

    def _merge(self, base: dict, override: dict):
        """Deep merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge(base[key], value)
            else:
                base[key] = value

    def save(self):
        """Save current config to file."""
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dot-separated key path (e.g. 'window.width')."""
        keys = key.split('.')
        data = self._data
        for k in keys:
            if isinstance(data, dict) and k in data:
                data = data[k]
            else:
                return default
        return data

    def set(self, key: str, value: Any):
        """Set a config value by dot-separated key path."""
        keys = key.split('.')
        data = self._data
        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value
        self.save()

    @property
    def thread_count(self) -> int:
        return self.get('thread_count', 5)

    @thread_count.setter
    def thread_count(self, value: int):
        self.set('thread_count', max(1, min(100, value)))

    @property
    def sound_enabled(self) -> bool:
        return self.get('sound_enabled', True)

    @sound_enabled.setter
    def sound_enabled(self, value: bool):
        self.set('sound_enabled', bool(value))

    @property
    def use_proxies(self) -> bool:
        return self.get('use_proxies', False)

    @use_proxies.setter
    def use_proxies(self, value: bool):
        self.set('use_proxies', bool(value))

