import os
import sys
import threading
from abc import ABC, abstractmethod
from typing import Optional, Any

from core.token_parser import TokenEntry
from core.proxy_manager import ProxyRotator, ProxyEntry
from core.discord_api import DiscordAPI
from core.logger import AppLogger

def _get_project_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # This might be different depending on where tools are located
    # In the source structure, source/tools/base_tool.py is 2 levels deep
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class BaseTool(ABC):
    """
    BaseTool — Abstract base class for all THEBOY TOOLS.
    Every tool extends this class to get standardized logging, result tracking, and file output.
    """
    
    TOOL_NAME = "Base"
    
    def __init__(self, log_callback=None, save_output: bool = True):
        self._logger = AppLogger.instance()
        self._output_root = os.path.join(_get_project_root(), "output", self.TOOL_NAME)
        self._file_lock = threading.Lock()
        self._written_lines = {}  # {filepath: set(lines)}
        self._duplicate_count = 0
        self.save_output = save_output
        self._log_callback = log_callback

    @abstractmethod
    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        """
        Process a single token. Must be implemented by each tool.
        Returns: dict with at least {"success": bool, "message": str}
        """
        pass

    def get_api(self, proxy: Optional[ProxyEntry] = None) -> DiscordAPI:
        """Create a DiscordAPI instance, optionally with a proxy."""
        return DiscordAPI(token=None, proxy=proxy)

    def log(self, token: str, message: str, level: str = "INFO", preview: bool = True):
        """Log a message for a specific token with preview."""
        token_preview = f"[{token[:10]}...] " if preview and token else ""
        formatted = f"{token_preview}{message}"
        
        # Internal file logging
        if level.upper() == "SUCCESS":
            self._logger.info(f"[SUCCESS] {formatted}")
        elif level.upper() == "WARNING":
            self._logger.warning(formatted)
        elif level.upper() == "ERROR":
            self._logger.error(formatted)
        else:
            self._logger.info(formatted)
            
        # UI callback
        if self._log_callback:
            self._log_callback(token, message, level.upper())

    def _get_output_dir(self, subfolder: str = "") -> str:
        """Get the output directory for this tool, creating it if needed."""
        path = os.path.join(self._output_root, subfolder)
        os.makedirs(path, exist_ok=True)
        return path

    def append_to_file(self, filename: str, line: str, subfolder: str = ""):
        """
        Append a single line to an output file in real-time (thread-safe).
        Skips duplicate lines per file. No-op when save_output is False.
        """
        if not self.save_output:
            return
            
        with self._file_lock:
            out_dir = self._get_output_dir(subfolder)
            filepath = os.path.join(out_dir, filename if filename.endswith(".txt") else f"{filename}.txt")
            
            if filepath not in self._written_lines:
                self._written_lines[filepath] = set()
                
            if line in self._written_lines[filepath]:
                self._duplicate_count += 1
                return
                
            self._written_lines[filepath].add(line)
            
            try:
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(f"{line}\n")
            except Exception as e:
                self._logger.error(f"Error writing to {filename}: {str(e)}")

    def clear_output(self):
        """Clear all output files for a fresh run."""
        if not os.path.exists(self._output_root):
            return
            
        for root, dirs, files in os.walk(self._output_root):
            for file in files:
                if file.endswith(".txt"):
                    try:
                        os.remove(os.path.join(root, file))
                    except:
                        pass

    def execute(self, token_entry: TokenEntry, proxy_rotator: Optional[ProxyRotator] = None, **kwargs) -> dict:
        """
        Wrapper that handles proxy rotation and error catching.
        Called by ToolWorker for each token.
        """
        proxy = proxy_rotator.get_proxy() if proxy_rotator else None
        
        try:
            # Inject proxy into kwargs so tool can use it
            kwargs['proxy'] = proxy
            result = self.process_token(token_entry, **kwargs)
            return result
        except Exception as e:
            error_msg = f"Error processing token: {str(e)}"
            token_preview = token_entry.token[:20] if token_entry.token else "N/A"
            self.log(token_preview, error_msg, "ERROR")
            return {"success": False, "message": error_msg}

