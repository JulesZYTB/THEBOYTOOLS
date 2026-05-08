import os
import time
import threading
from typing import Optional

try:
    from pypresence import Presence
except ImportError:
    Presence = None

class DiscordRPCManager:
    """
    Manages Discord Rich Presence in a background thread.

    Usage:
        rpc = DiscordRPCManager.instance()
        rpc.start()                        # After HWID auth
        rpc.update_activity("checker")     # When user switches tool
        rpc.stop()                         # On app close
    """
    
    _instance: Optional['DiscordRPCManager'] = None
    _CLIENT_ID = "1486437824482775120"
    _DISCORD_IPC_PIPE = r"\\.\pipe\discord-ipc-0"
    
    RPC_STATES = {
        'home': {'details': 'Viewing', 'state': 'Home Page'},
        'checker': {'details': 'Viewing', 'state': 'Checker Page'},
        'captcha_checker': {'details': 'Viewing', 'state': 'Captcha Checker Page'},
        'trial_checker': {'details': 'Viewing', 'state': 'Trial Checker Page'},
        'joiner': {'details': 'Viewing', 'state': 'Joiner Page'},
        'changer': {'details': 'Viewing', 'state': 'Password Changer Page'},
        'humanizer': {'details': 'Viewing', 'state': 'Humanizer Page'},
        'unlocker': {'details': 'Viewing', 'state': 'Unlocker Page'},
        'token_cleaner': {'details': 'Viewing', 'state': 'Token Cleaner Page'},
        'separator': {'details': 'Viewing', 'state': 'Token Separator Page'},
        'get_token_email': {'details': 'Viewing', 'state': 'Get Token Email Page'},
        'phone_verifier': {'details': 'Viewing', 'state': 'Phone Verifier Page'},
        'settings': {'details': 'Configuring', 'state': 'Settings'},
        'idle': {'details': 'The Ultimate Discord Toolkit', 'state': 'Idle'}
    }

    def __init__(self):
        self._rpc = None
        self._connected = False
        self._running = False
        self._discord_available = False
        self._lock = threading.Lock()
        self._thread = None
        
        self._current_state = 'idle'
        self._start_time = int(time.time())

    @classmethod
    def instance(cls) -> 'DiscordRPCManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _is_discord_running(self) -> bool:
        """Check if Discord's IPC pipe exists (Windows only)."""
        if os.name != 'nt':
            return False
        return os.path.exists(self._DISCORD_IPC_PIPE)

    def start(self):
        """Start the RPC connection in a background thread."""
        with self._lock:
            if not self._running:
                self._running = True
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()

    def stop(self):
        """Stop the RPC connection and background thread."""
        with self._lock:
            self._running = False
            self._disconnect()

    def update_activity(self, tool_name: str):
        """Thread-safe method to update the RPC status."""
        with self._lock:
            if tool_name in self.RPC_STATES:
                self._current_state = tool_name
                self._push_update()

    def _connect(self):
        """Attempt to connect to Discord RPC."""
        if not Presence:
            return False
        
        try:
            if not self._is_discord_running():
                return False
                
            self._rpc = Presence(self._CLIENT_ID)
            self._rpc.connect()
            self._connected = True
            return True
        except:
            self._connected = False
            return False

    def _disconnect(self):
        """Disconnect from Discord RPC."""
        try:
            if self._rpc:
                self._rpc.close()
        except:
            pass
        self._rpc = None
        self._connected = False

    def _push_update(self):
        """Push the current activity state to Discord."""
        if not self._connected or not self._rpc:
            return
            
        try:
            state_data = self.RPC_STATES.get(self._current_state, self.RPC_STATES['idle'])
            self._rpc.update(
                details=state_data['details'],
                state=state_data['state'],
                large_image="logo_large",
                large_text="THEBOY TOOLS v1.1",
                start=self._start_time
            )
        except:
            self._connected = False

    def _run_loop(self):
        """Background loop: connect, update, reconnect on failure."""
        while self._running:
            if not self._connected:
                if self._connect():
                    self._push_update()
                else:
                    # Discord not running or pipe busy, wait 60s
                    time.sleep(60)
                    continue
            
            # Periodic push or just sleep while waiting for manual updates
            # Manual updates are triggered by update_activity()
            time.sleep(15)
            
            # Verify connection periodically
            if not self._is_discord_running():
                self._disconnect()
            else:
                self._push_update()

