import os
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QSoundEffect
from core.config import Config

def _get_project_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # This is in source/core/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_asset_root() -> str:
    """
    Get the root path for bundled assets (EXE-safe).
    
    In Nuitka onefile builds, bundled data is extracted alongside modules
    in a temp directory. Use __file__ to locate it.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(__file__))
    return _get_project_root()

class SoundManager:
    """
    Sound Manager — Toggle-able click, success, and error sound effects.
    Uses QSoundEffect from PyQt6 for EXE-friendly sound playback.
    """
    _instance = None
    SOUNDS = {'click': 'click.wav', 'success': 'success.wav', 'error': 'error.wav'}

    def __init__(self):
        self._effects = {}
        self._sound_dir = os.path.join(_get_asset_root(), 'assets', 'sounds')
        self._loaded = False
        self._cfg = Config.instance()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def ensure_loaded(self):
        """Load sounds lazily. Must be called from the main GUI thread."""
        if self._loaded:
            return
        
        for name, filename in self.SOUNDS.items():
            filepath = os.path.join(self._sound_dir, filename)
            if os.path.exists(filepath):
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(filepath))
                effect.setVolume(0.5)
                self._effects[name] = effect
        
        self._loaded = True

    @property
    def enabled(self) -> bool:
        return self._cfg.get('sound_enabled', True)

    @enabled.setter
    def enabled(self, value: bool):
        self._cfg.set('sound_enabled', value)

    def play(self, sound_name: str):
        """Play a sound effect if sounds are enabled."""
        if not self.enabled:
            return
            
        self.ensure_loaded()
        effect = self._effects.get(sound_name)
        if effect:
            effect.play()

    def click(self):
        """Play click sound."""
        self.play('click')

    def success(self):
        """Play success sound."""
        self.play('success')

    def error(self):
        """Play error sound."""
        self.play('error')

    def set_volume(self, volume: float):
        """Set volume for all effects (0.0 to 1.0)."""
        volume = max(0.0, min(1.0, volume))
        self.ensure_loaded()
        for effect in self._effects.values():
            effect.setVolume(volume)
