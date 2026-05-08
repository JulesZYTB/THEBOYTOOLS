import os
import logging
from datetime import datetime
from typing import Optional, ClassVar
from PyQt6.QtCore import QObject, pyqtSignal

class LogLevel:
    """Log level constants with colors for the GUI console."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    
    COLORS = {
        DEBUG: "#808080",
        INFO: "#ffffff",
        SUCCESS: "#0ff0b3",
        WARNING: "#ffb347",
        ERROR: "#ff4757"
    }

class LogSignals(QObject):
    """Qt signals for thread-safe log emission."""
    log = pyqtSignal(str, str)  # message, level

class AppLogger:
    """
    Application-wide logger that writes to both file and emits Qt signals
    for the GUI console.
    """
    _instance: Optional['AppLogger'] = None
    SUCCESS_LEVEL = 25

    def __init__(self, log_dir: str = "logs"):
        self._log_dir = log_dir
        if not os.path.exists(self._log_dir):
            os.makedirs(self._log_dir, exist_ok=True)
            
        log_file = os.path.join(self._log_dir, f"theboy_tools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        self._file_logger = logging.getLogger("TheBoyTools")
        self._file_logger.setLevel(logging.DEBUG)
        
        # Avoid duplicate handlers
        if not self._file_logger.handlers:
            handler = logging.FileHandler(log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S'))
            self._file_logger.addHandler(handler)
            
        logging.addLevelName(self.SUCCESS_LEVEL, "SUCCESS")
        self._signals = LogSignals()

    @classmethod
    def instance(cls) -> 'AppLogger':
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (useful for testing)."""
        cls._instance = None

    @property
    def signals(self) -> LogSignals:
        return self._signals

    def _log(self, message: str, level: str):
        """Internal log method."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"{timestamp} > {message}"
        
        # Emit to UI
        self._signals.log.emit(formatted, level)
        
        # Write to file
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.SUCCESS: self.SUCCESS_LEVEL,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR
        }
        numeric_level = level_map.get(level, logging.INFO)
        self._file_logger.log(numeric_level, message)

    def debug(self, message: str):
        self._log(message, LogLevel.DEBUG)

    def info(self, message: str):
        self._log(message, LogLevel.INFO)

    def success(self, message: str):
        self._log(message, LogLevel.SUCCESS)

    def warning(self, message: str):
        self._log(message, LogLevel.WARNING)

    def error(self, message: str):
        self._log(message, LogLevel.ERROR)

    def api_error(self, token_preview: str, status_code: int, message: str):
        """Log a Discord API error with token preview (first 20 chars)."""
        preview = token_preview[:20]
        self.error(f"[{preview}...] HTTP {status_code}: {message}")
