import os
import re
import json
import time
import hashlib
import uuid
import platform
import subprocess
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import requests
from core.config import Config
from core.logger import AppLogger
from core.protection import SecureString

APP_VERSION = "1.1.0"

class ServerSignals(QObject):
    """Signals for real-time updates."""
    presence_updated = pyqtSignal(int)      # online_count
    announcement_updated = pyqtSignal(str)   # message
    update_available = pyqtSignal(str, str)  # version, url

class ServerManager:
    """Supabase-backed remote control — singleton."""
    
    _instance: Optional['ServerManager'] = None
    CURRENT_VERSION = "1.1.0"
    GITHUB_REPO_OWNER = "HimTheBoy"
    GITHUB_REPO_NAME = "THEBOY-TOOLS"
    
    # Encrypted Supabase credentials (placeholders, would normally be decrypted via SecureString)
    _ENC_SB_URL = "3a199dcebdee788e3d75c5cdd8ff89456e64290c28b08b76fde3391c63edd7eaa38faa5313414d51bf8950a0525293f6"
    _ENC_SB_KEY = "8f148e0d24f3c733eab7c18e60a74724f4963e20a4f0d267ad3deb594699560ab26d530925820765b32adedb21afd453"

    def __init__(self):
        self._config = Config.instance()
        self._logger = AppLogger.instance()
        self.signals = ServerSignals()
        
        self._hwid = self.get_hwid()
        self._username = ""
        self._announcement = ""
        self._announcement_id = ""
        self._feature_flags = {}
        self._allowed_tools = "*"
        self._authenticated = False
        
        # Timers
        self._heartbeat_timer = QTimer()
        self._poll_timer = QTimer()

    @classmethod
    def instance(cls) -> 'ServerManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def get_hwid(self) -> str:
        """
        Generate a machine-unique hardware ID.
        
        IMPORTANT: Do NOT change the order or logic of raw_parts collection.
        Changing it will alter existing users' HWIDs and lock them out.
        """
        raw_parts = []
        
        # 1. Disk Serial (Windows)
        try:
            cmd = ['wmic', 'diskdrive', 'get', 'SerialNumber']
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, creationflags=0x08000000) # CREATE_NO_WINDOW
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and "SerialNumber" not in line]
            if lines:
                raw_parts.append(lines[0])
        except: pass
        
        # 2. System UUID (Windows)
        try:
            cmd = ['wmic', 'csproduct', 'get', 'UUID']
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, creationflags=0x08000000)
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and "UUID" not in line]
            if lines:
                raw_parts.append(lines[0])
        except: pass
        
        # 3. MAC Address
        try:
            mac = hex(uuid.getnode())
            raw_parts.append(f"mac-{mac}")
        except: pass
        
        # Fallback if all failed
        if not raw_parts:
            raw_parts.append(platform.node())
            raw_parts.append(platform.machine())
            raw_parts.append(platform.processor())
            
        raw = "|".join(raw_parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _sb_request(self, method: str, path: str, json_data: dict = None, timeout: int = 10) -> requests.Response:
        """Decrypt credentials -> make request -> zero from memory."""
        # In a real scenario, SecureString would decrypt these on the fly
        sb_url = SecureString(self._ENC_SB_URL).decrypt()
        sb_key = SecureString(self._ENC_SB_KEY).decrypt()
        
        url = f"{sb_url}{path}"
        headers = {
            "apikey": sb_key,
            "Authorization": f"Bearer {sb_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
            "x-hwid": self._hwid
        }
        
        return requests.request(method, url, headers=headers, json=json_data, timeout=timeout)

    def user_login(self, username: str = "") -> dict:
        """
        Register or authenticate the user via HWID against Supabase.
        Returns: {"valid": bool, "message": str, "needs_username": bool}
        """
        try:
            # 1. Lookup
            resp = self._sb_request("GET", f"/rest/v1/licenses?hwid=eq.{self._hwid}&select=*")
            if resp.status_code != 200:
                return {"valid": False, "message": "Server error — try again later", "needs_username": False}
            
            data = resp.json()
            
            if not data:
                # Need registration
                if not username:
                    return {"valid": False, "needs_username": True, "message": "Username required for first launch"}
                
                # Register
                payload = {
                    "username": username,
                    "hwid": self._hwid,
                    "active": True,
                    "allowed_tools": "*",
                    "note": f"Auto-registered {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                    "app_version": self.CURRENT_VERSION,
                    "key": str(uuid.uuid4())
                }
                reg_resp = self._sb_request("POST", "/rest/v1/licenses", json_data=payload)
                if reg_resp.status_code not in (200, 201):
                    return {"valid": False, "message": "Registration failed", "needs_username": False}
                data = reg_resp.json()

            user_row = data[0] if isinstance(data, list) else data
            
            # Check active
            if not user_row.get("active", True):
                return {"valid": False, "message": "Access has been revoked by admin", "needs_username": False}
            
            # Check expiry
            expires_at = user_row.get("expires_at")
            if expires_at:
                exp_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > exp_dt:
                    return {"valid": False, "message": "Access has expired", "needs_username": False}
            
            self._username = user_row.get("username", "User")
            self._allowed_tools = user_row.get("allowed_tools", "*")
            self._authenticated = True
            
            # Start background tasks
            self._report_version()
            self._start_heartbeat()
            self.log_activity("login", {"version": self.CURRENT_VERSION})
            
            return {"valid": True, "message": "Authentication successful", "needs_username": False}
            
        except requests.exceptions.ConnectionError:
            return {"valid": True, "message": "Offline mode", "needs_username": False}
        except Exception as e:
            return {"valid": False, "message": f"Validation error: {str(e)}", "needs_username": False}

    def _report_version(self):
        """PATCH the user's app_version in the licenses table."""
        try:
            self._sb_request("PATCH", f"/rest/v1/licenses?hwid=eq.{self._hwid}", 
                             json_data={"app_version": self.CURRENT_VERSION})
        except: pass

    def _update_last_seen(self):
        """PATCH the user's last_seen timestamp."""
        try:
            now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            self._sb_request("PATCH", f"/rest/v1/licenses?hwid=eq.{self._hwid}", 
                             json_data={"last_seen": now_utc})
        except: pass

    def _start_heartbeat(self):
        """Start QTimers: heartbeat (last_seen) every 2 min, polling every 30s."""
        self._heartbeat_timer.setInterval(120000)
        self._heartbeat_timer.timeout.connect(self._update_last_seen)
        self._heartbeat_timer.start()
        
        self._poll_timer.setInterval(30000)
        self._poll_timer.timeout.connect(self._poll_online_count)
        self._poll_timer.timeout.connect(self._poll_announcement)
        self._poll_timer.start()

    def _poll_online_count(self):
        """Call the get_online_count() RPC to get active users."""
        try:
            # Users active in the last 5 minutes
            resp = self._sb_request("POST", "/rest/v1/rpc/get_online_count", timeout=8)
            if resp.status_code == 200:
                count = int(resp.text)
                self.signals.presence_updated.emit(max(1, count))
        except: pass

    def _poll_announcement(self):
        """Query 'app_config' for the current announcement."""
        try:
            resp = self._sb_request("GET", "/rest/v1/app_config?select=announcement,announcement_id&limit=1", timeout=8)
            if resp.status_code == 200:
                data = resp.json()[0]
                new_announcement = data.get("announcement", "")
                new_id = str(data.get("announcement_id", ""))
                
                if new_id != self._announcement_id:
                    self._announcement = new_announcement
                    self._announcement_id = new_id
                    self.signals.announcement_updated.emit(self._announcement)
        except: pass

    def check_app_status(self) -> dict:
        """Check kill-switch and updates."""
        try:
            resp = self._sb_request("GET", "/rest/v1/app_config?select=*&limit=1")
            if resp.status_code == 200:
                data = resp.json()[0]
                if data.get("kill_switch", False):
                    return {"allowed": False, "message": data.get("kill_message", "Application is currently disabled by admin")}
            
            # Check GitHub for updates
            gh = self._check_github_update()
            if gh.get("update_available"):
                self.signals.update_available.emit(gh["latest_version"], gh["download_url"])
                
            return {"allowed": True, "message": "OK", "update_available": gh.get("update_available")}
        except:
            return {"allowed": True, "message": "Offline check skipped"}

    def _check_github_update(self) -> dict:
        """Query GitHub Releases API."""
        try:
            api_url = f"https://api.github.com/repos/{self.GITHUB_REPO_OWNER}/{self.GITHUB_REPO_NAME}/releases/latest"
            headers = {"Accept": "application/vnd.github+json"}
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                latest_tag = data.get("tag_name", "").lstrip("vV")
                
                # Version comparison
                if latest_tag != self.CURRENT_VERSION:
                    download_url = ""
                    for asset in data.get("assets", []):
                        if asset.get("name", "").endswith(".exe"):
                            download_url = asset.get("browser_download_url", "")
                            break
                    return {"update_available": True, "latest_version": latest_tag, "download_url": download_url}
            return {"update_available": False}
        except:
            return {"update_available": False}

    def get_feature_flags(self) -> dict:
        """Read the `feature_flags` table."""
        try:
            resp = self._sb_request("GET", "/rest/v1/feature_flags?select=*")
            if resp.status_code == 200:
                self._feature_flags = {row["tool_name"]: row["enabled"] for row in resp.json()}
            return self._feature_flags
        except:
            return {}

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled globally and allowed for this user."""
        global_enabled = self._feature_flags.get(tool_name, True)
        user_allowed = self._allowed_tools == "*" or tool_name in self._allowed_tools.split(",")
        return global_enabled and user_allowed

    def log_activity(self, action: str, details: dict):
        """Fire-and-forget activity log."""
        def _post():
            try:
                payload = {
                    "hwid": self._hwid,
                    "action": action,
                    "details": json.dumps(details),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                self._sb_request("POST", "/rest/v1/user_activity", json_data=payload)
            except: pass
            
        threading.Thread(target=_post, daemon=True).start()

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    @property
    def app_version(self) -> str:
        return self.CURRENT_VERSION
    
    @property
    def announcement(self) -> str:
        return self._announcement

    @property
    def announcement_id(self) -> str:
        return self._announcement_id

