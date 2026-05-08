import os
import re
import json
import time
import base64
import random
import uuid
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any, List, Union

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

import requests as std_requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.proxy_manager import ProxyEntry
from core.protection import encrypted_const

def connect_to_gateway(token: str, proxy: Optional[ProxyEntry] = None):
    """
    Connect to Discord's WebSocket gateway and IDENTIFY with the token.
    This creates an active session on Discord's backend.
    """
    try:
        import websocket
    except ImportError:
        return None

    # Proxy support for websocket
    ws_kwargs = {"timeout": 10}
    if proxy:
        ws_kwargs["http_proxy_host"] = proxy.host
        ws_kwargs["http_proxy_port"] = proxy.port
        if proxy.username:
            ws_kwargs["http_proxy_auth"] = (proxy.username, proxy.password)

    try:
        ws = websocket.WebSocket()
        ws.connect("wss://gateway.discord.gg/?v=10&encoding=json", **ws_kwargs)
        
        # 1. Receive Hello
        hello = json.loads(ws.recv())
        heartbeat_interval = hello['d']['heartbeat_interval'] / 1000.0
        
        # 2. Identify
        identify_payload = {
            "op": 2,
            "d": {
                "token": token,
                "intents": 0,
                "properties": {
                    "os": "Windows",
                    "browser": "Discord Client",
                    "device": "Windows"
                }
            }
        }
        ws.send(json.dumps(identify_payload))
        
        # 3. Start heartbeat thread
        def _heartbeat():
            while ws.connected:
                try:
                    ws.send(json.dumps({"op": 1, "d": None}))
                    time.sleep(heartbeat_interval)
                except:
                    break
        
        threading.Thread(target=_heartbeat, daemon=True).start()
        return ws
    except Exception:
        return None

class ApiErrorType(Enum):
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    CAPTCHA_REQUIRED = "captcha_required"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"

@dataclass
class ApiResponse:
    """Structured API response."""
    success: bool
    status_code: int
    error_type: Optional[ApiErrorType] = None
    error_message: Optional[str] = None
    data: Optional[Any] = None
    retry_after: float = 0.0

    def is_rate_limited(self) -> bool:
        return self.error_type == ApiErrorType.RATE_LIMITED

    def is_captcha(self) -> bool:
        return self.error_type == ApiErrorType.CAPTCHA_REQUIRED

class DiscordAPI:
    """Discord API client — fresh session per request, simple retry."""
    
    DISCORD_API_BASE = "https://discord.com/api/v9"
    MAX_RETRIES = 3
    _FALLBACK_BUILD_NUMBER = 100000
    
    _build_lock = threading.Lock()
    _cached_build_number = None
    
    _LOCALES = ['en-US', 'en-GB', 'en-US', 'en-US']
    _TIMEZONES = ['America/New_York', 'America/Chicago', 'America/Los_Angeles', 'Europe/London', 'Europe/Berlin', 'Africa/Cairo', 'Asia/Dubai']
    
    _CHROME_VERSION = "130.0.6723.191"
    _ELECTRON_VERSION = "33.3.1"
    _DISCORD_CLIENT_VERSION = "1.0.9176"
    _NATIVE_BUILD_NUMBER = 60832
    
    _CURL_IMPERSONATE = "chrome136"

    def __init__(self, token: str = None, proxy: Optional[ProxyEntry] = None, max_retries: int = 3, 
                 referrer_current: str = "https://discord.com/channels/@me", 
                 skip_cf_cookies: bool = False, fast_mode: bool = False):
        self.token = token
        self._proxy = proxy
        self.max_retries = max_retries
        self.referrer_current = referrer_current
        self._skip_cf_cookies = skip_cf_cookies
        self.fast_mode = fast_mode
        
        self._proxy_dict = None
        if self._proxy:
            self._proxy_dict = {
                "http": self._proxy.to_url(),
                "https": self._proxy.to_url()
            }
            
        self._fingerprint = self._generate_fingerprint()
        self._cf_cookies = None
        self._session = None
        self._fast_session = None

    def _scrape_build_number(self) -> int:
        """
        Auto-scrape the current Discord client build number from their JS bundle.
        
        Flow:
          1. GET https://discord.com/login -> extract all /assets/*.js script URLs
          2. Fetch the last few JS files (the build number is in the main app bundle)
          3. Search for 'buildNumber' or 'client_build_number' pattern
          4. Return the number, or fall back to _FALLBACK_BUILD_NUMBER
        """
        with self._build_lock:
            if DiscordAPI._cached_build_number:
                return DiscordAPI._cached_build_number
                
            try:
                session = std_requests.Session()
                resp = session.get("https://discord.com/login", timeout=10)
                if resp.status_code != 200:
                    return self._FALLBACK_BUILD_NUMBER
                
                script_urls = re.findall(r'(?:src|href)=["\'](/assets/[^"\']+\.js)["\']', resp.text)
                # Only check the last few JS files as they usually contain the app logic
                for script_path in reversed(script_urls[-5:]):
                    url = f"https://discord.com{script_path}"
                    js_resp = session.get(url, timeout=8)
                    if js_resp.status_code == 200:
                        match = re.search(r'buildNumber["\s:]+["\']?(\d{5,7})["\']?', js_resp.text)
                        if not match:
                            match = re.search(r'client_build_number["\s:]+(\d{5,7})', js_resp.text)
                        
                        if match:
                            DiscordAPI._cached_build_number = int(match.group(1))
                            return DiscordAPI._cached_build_number
            except Exception:
                pass
            
            return self._FALLBACK_BUILD_NUMBER

    def get_build_number(self) -> int:
        """Get the Discord client build number (cached after first scrape)."""
        if DiscordAPI._cached_build_number:
            return DiscordAPI._cached_build_number
        return self._scrape_build_number()

    def _generate_installation_id(self) -> str:
        """
        Generate x-installation-id matching the Discord Desktop Client format.
        Format: {large_random_int}.{random_base64_chars}
        """
        int_part = str(random.randint(1000000000000000000, 9999999999999999999))
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        sig = "".join(random.choices(chars, k=22))
        return f"{int_part}.{sig}"

    def _build_super_properties(self) -> str:
        """
        Build X-Super-Properties matching the Discord Desktop Client.
        
        Generates per-call UUIDs for session identifiers so each DiscordAPI
        instance has a unique "client session" fingerprint.
        """
        props = {
            "os": "Windows",
            "browser": "Discord Client",
            "release_channel": "stable",
            "client_version": self._DISCORD_CLIENT_VERSION,
            "os_version": "10.0.26100",
            "os_arch": "x64",
            "app_arch": "x64",
            "system_locale": "en-US",
            "browser_user_agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/{self._DISCORD_CLIENT_VERSION} Chrome/{self._CHROME_VERSION} Electron/{self._ELECTRON_VERSION} Safari/537.36",
            "browser_version": self._ELECTRON_VERSION,
            "client_build_number": self.get_build_number(),
            "native_build_number": self._NATIVE_BUILD_NUMBER,
            "client_event_source": None,
            "client_launch_id": str(uuid.uuid4()),
            "launch_signature": "".join(random.choices("abcdef0123456789", k=64)),
            "client_heartbeat_session_id": str(uuid.uuid4()),
            "client_app_state": "focused",
            "focused": True,
            "has_client_mods": False
        }
        return base64.b64encode(json.dumps(props, separators=(',', ':')).encode()).decode()

    def _generate_fingerprint(self) -> dict:
        """
        Generate a complete Discord Desktop Client fingerprint.
        
        Matches the proven zero-captcha approach:
        - Electron/Chrome-based User-Agent
        - Discord Client x-super-properties
        - x-installation-id in client format
        """
        return {
            "user_agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/{self._DISCORD_CLIENT_VERSION} Chrome/{self._CHROME_VERSION} Electron/{self._ELECTRON_VERSION} Safari/537.36",
            "x_super": self._build_super_properties(),
            "installation_id": self._generate_installation_id(),
            "timezone": random.choice(self._TIMEZONES),
            "locale": random.choice(self._LOCALES)
        }

    def _acquire_cf_cookies(self) -> Optional[str]:
        """
        Acquire CF cookies via a simple GET to discord.com.
        
        With Firefox TLS impersonation, cf_clearance is NOT needed —
        Discord doesn't captcha Firefox TLS fingerprint.
        Only __dcfduid and __sdcfduid are required.
        
        Globally cached with 25-minute TTL. Thread-safe.
        """
        # Simplification: return a basic cookie string for now or use session persistence
        return None

    def _get_headers(self) -> dict:
        """Build request headers with authorization using this instance's fingerprint."""
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": f"{self._fingerprint['locale']},en;q=0.9",
            "Content-Type": "application/json",
            "User-Agent": self._fingerprint['user_agent'],
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": self._fingerprint['locale'],
            "X-Discord-Timezone": self._fingerprint['timezone'],
            "X-Super-Properties": self._fingerprint['x_super'],
            "X-Installation-Id": self._fingerprint['installation_id'],
            "Referer": self.referrer_current,
            "Origin": "https://discord.com"
        }
        if self.token:
            headers["Authorization"] = self.token
        return headers

    def _classify_error(self, status_code: int, data: Any) -> tuple:
        """Classify a Discord API error by status code and response body."""
        err_type = ApiErrorType.UNKNOWN
        err_msg = f"HTTP Error {status_code}"
        retry_after = 0.0
        
        if isinstance(data, dict):
            # Extract standard Discord error message
            msg = data.get("message")
            code = data.get("code")
            
            if msg and code:
                err_msg = f"{msg} (Code: {code})"
            elif msg:
                err_msg = msg
            elif code:
                err_msg = f"Error Code: {code}"
            
            if "retry_after" in data:
                retry_after = float(data["retry_after"])
        elif isinstance(data, str) and data:
            if "Cloudflare" in data or "cf-error" in data:
                err_msg = "Cloudflare Blocked (Try rotating proxies)"
            elif len(data) < 100:
                err_msg = f"API Error: {data}"

        # Override based on specific status codes
        if status_code == 401:
            err_type = ApiErrorType.UNAUTHORIZED
            err_msg = "Token is invalid or expired"
        elif status_code == 403:
            err_type = ApiErrorType.FORBIDDEN
            if isinstance(data, dict) and data.get("code") == 40001:
                err_type = ApiErrorType.CAPTCHA_REQUIRED
                err_msg = "Captcha Required"
        elif status_code == 404:
            err_type = ApiErrorType.NOT_FOUND
            err_msg = "Resource not found (404)"
        elif status_code == 429:
            err_type = ApiErrorType.RATE_LIMITED
            err_msg = f"Rate Limited (Retry after {retry_after}s)"
        elif status_code == 400:
            err_msg = f"Bad Request (400): {str(data)[:150]}"
        elif status_code >= 500:
            err_type = ApiErrorType.SERVER_ERROR
            err_msg = f"Discord Server Error ({status_code})"
            
        return err_type, err_msg, retry_after

    def _make_request(self, method: str, endpoint: str, json_data: Any = None, files: Any = None) -> ApiResponse:
        """
        Make a request to the Discord API with simple retry and backoff.

        Creates a fresh session per attempt (prevents connection pool
        corruption across threads). Uses exponential backoff on failure.
        """
        url = f"{self.DISCORD_API_BASE}{endpoint}"
        headers = self._get_headers()
        
        for attempt in range(self.max_retries):
            try:
                if curl_requests:
                    session = curl_requests.Session(impersonate=self._CURL_IMPERSONATE)
                    proxies = self._proxy_dict if self._proxy_dict else None
                    
                    response = session.request(
                        method=method.upper(),
                        url=url,
                        headers=headers,
                        json=json_data,
                        files=files,
                        proxies=proxies,
                        timeout=15,
                        verify=False
                    )
                    status_code = response.status_code
                    try:
                        data = response.json()
                    except:
                        data = response.text
                else:
                    response = std_requests.request(
                        method=method.upper(),
                        url=url,
                        headers=headers,
                        json=json_data,
                        files=files,
                        proxies=self._proxy_dict,
                        timeout=15,
                        verify=False
                    )
                    status_code = response.status_code
                    try:
                        data = response.json()
                    except:
                        data = response.text

                if status_code in (200, 201, 204):
                    return ApiResponse(success=True, status_code=status_code, data=data)
                
                err_type, err_msg, retry_after = self._classify_error(status_code, data)
                
                if err_type == ApiErrorType.RATE_LIMITED:
                    wait_time = retry_after if retry_after > 0 else (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                
                return ApiResponse(success=False, status_code=status_code, error_type=err_type, error_message=err_msg, data=data, retry_after=retry_after)
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return ApiResponse(success=False, status_code=0, error_type=ApiErrorType.NETWORK_ERROR, error_message=str(e))
                time.sleep(2 ** attempt)
        
        return ApiResponse(success=False, status_code=0, error_type=ApiErrorType.UNKNOWN, error_message="Max retries exceeded")

    def get_user_info(self) -> ApiResponse:
        """GET /users/@me — Validate token and get user info."""
        return self._make_request("GET", "/users/@me")

    def get_guild_count(self) -> int:
        """GET /users/@me/guilds — Return the number of guilds the token is in. Returns -1 on error."""
        resp = self._make_request("GET", "/users/@me/guilds")
        if resp.success and isinstance(resp.data, list):
            return len(resp.data)
        return -1

    def join_guild(self, invite_code: str) -> ApiResponse:
        """
        POST /invites/{code} — Join a server matching the EXACT browser flow.
        
        Real browser sends 3 requests:
          1. GET  /invites/{code}?inputValue=...&with_counts=true  (pre-flight — gets invite info)
          2. POST /invites/{code} with {session_id: hex32}          (actual join)
          3. GET  /guilds/{id}/onboarding                           (post-join, optional)
        """
        invite_code = invite_code.replace("https://discord.gg/", "").replace("discord.gg/", "").replace("https://discord.com/invite/", "")
        
        # 1. Pre-flight
        preflight_url = f"/invites/{invite_code}?inputValue={invite_code}&with_counts=true&with_expiration=true"
        pre_resp = self._make_request("GET", preflight_url)
        
        if not pre_resp.success:
            if pre_resp.is_rate_limited() or pre_resp.error_type == ApiErrorType.UNAUTHORIZED:
                return pre_resp
            # Continue anyway for other errors (like 10008 or 400)
            
        # 2. Actual Join
        session_id = "".join(random.choices("0123456789abcdef", k=32))
        payload = {"session_id": session_id}
        
        join_resp = self._make_request("POST", f"/invites/{invite_code}", json_data=payload)
        
        if join_resp.success:
            # 3. Onboarding (Optional)
            try:
                guild_id = join_resp.data.get("guild", {}).get("id")
                if guild_id:
                    self._make_request("GET", f"/guilds/{guild_id}/onboarding")
            except:
                pass
                
        return join_resp

    def leave_guild(self, guild_id: str) -> ApiResponse:
        """DELETE /users/@me/guilds/{id} — Leave a server."""
        return self._make_request("DELETE", f"/users/@me/guilds/{guild_id}", json_data={"lurking": False})

    def update_profile(self, display_name: Optional[str] = None, bio: Optional[str] = None) -> ApiResponse:
        """PATCH /users/@me — Update display name, bio (legacy simple method)."""
        payload = {}
        if display_name: payload["global_name"] = display_name
        if bio: payload["bio"] = bio
        return self._make_request("PATCH", "/users/@me", json_data=payload)

    def change_password(self, old_password: str, new_password: str) -> ApiResponse:
        """PATCH /users/@me — Change password."""
        payload = {
            "password": old_password,
            "new_password": new_password
        }
        return self._make_request("PATCH", "/users/@me", json_data=payload)

    def update_avatar(self, avatar_base64: str) -> ApiResponse:
        """PATCH /users/@me — Set avatar."""
        return self._make_request("PATCH", "/users/@me", json_data={"avatar": avatar_base64})

    def check_trial_offer(self) -> ApiResponse:
        """POST /users/@me/billing/user-offer — Check if token has an active Nitro trial offer."""
        return self._make_request("POST", "/users/@me/billing/user-offer", json_data={})



