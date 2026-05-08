import time
import re
import base64
import json
import uuid
import random
from typing import Optional, Any, Tuple, List

# We use curl_cffi for the TLS fingerprinting to match Chrome 136
from curl_cffi import requests

from core.token_parser import TokenEntry
from core.config import Config
from core.discord_api import DiscordAPI, ApiErrorType
from tools.base_tool import BaseTool
from tools.phone_verifier import captcha_solver, sms_service

class SessionContext:
    """Discord session context with Chrome 136 browser fingerprint."""
    
    BROWSER_VERSION = "136.0.0.0"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    SEC_CH_UA = '"Not(A:Brand";v="8", "Chromium";v="136", "Google Chrome";v="136"'

    def __init__(self, proxy: str = ""):
        self.session = requests.Session(impersonate="chrome136")
        self.build_number = 503231 # Current stable
        self._proxy = proxy
        if proxy:
            p_clean = self._strip_proxy_scheme(proxy)
            self.session.proxies = {"http": f"http://{p_clean}", "https": f"http://{p_clean}"}
        
        self.fingerprint = None
        self.super_properties = self._encode_super_props()

    def _strip_proxy_scheme(self, proxy: str) -> str:
        return proxy.replace("http://", "").replace("https://", "")

    def _encode_super_props(self) -> str:
        props = {
            "os": "Windows",
            "browser": "Chrome",
            "device": "",
            "system_locale": "en-US",
            "browser_user_agent": self.UA,
            "browser_version": self.BROWSER_VERSION,
            "os_version": "10",
            "referrer": "",
            "referring_domain": "",
            "referrer_current": "",
            "referring_domain_current": "",
            "release_channel": "stable",
            "client_build_number": self.build_number,
            "client_event_source": None,
            "client_launch_id": str(uuid.uuid4()),
            "launch_signature": "a9b5fb07-92ff-493f-86fe-352a2803b3df",
            "client_heartbeat_session_id": str(uuid.uuid4()),
            "client_app_state": "focused"
        }
        return base64.b64encode(json.dumps(props, separators=(',', ':')).encode()).decode()

    def get_headers(self, token: str, endpoint_type="api", include_auth=True, include_fingerprint=True) -> dict:
        hdrs = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Priority": "u=1, i",
            "User-Agent": self.UA,
            "Sec-Ch-Ua": self.SEC_CH_UA,
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Europe/London",
            "X-Debug-Options": "bugReporterEnabled",
            "X-Super-Properties": self.super_properties
        }
        if include_auth: hdrs["Authorization"] = token
        if include_fingerprint and self.fingerprint: hdrs["X-Fingerprint"] = self.fingerprint
        
        if endpoint_type == "api":
            hdrs["Content-Type"] = "application/json"
            hdrs["Origin"] = "https://discord.com"
            hdrs["Referer"] = "https://discord.com/channels/@me"
            
        return hdrs

    def get_fingerprint(self):
        try:
            r = self.session.get("https://discord.com/api/v9/experiments", timeout=10)
            self.fingerprint = r.json().get("fingerprint")
            return self.fingerprint
        except:
            return None

class PhoneVerifier(BaseTool):
    """
    Phone Verifier — Discord phone verification tool.
    """
    
    TOOL_NAME = "phone_verifier"

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)
        self._config = Config.instance()

    def _solve_and_retry_captcha(self, ctx: SessionContext, err_data: dict, token: str, url: str, payload: dict, 
                                 solver_name: str, captcha_key: str, proxy_str: str, log_fn):
        """Solve captcha from error response and retry the request."""
        sitekey = err_data.get("captcha_sitekey") or "a9b5fb07-92ff-493f-86fe-352a2803b3df"
        rqdata = err_data.get("captcha_rqdata")
        rqtoken = err_data.get("captcha_rqtoken")
        session_id = err_data.get("captcha_session_id")
        
        log_fn("Captcha required. Solving...", "WARNING")
        cap = captcha_solver.solve_hcaptcha(
            solver_name=solver_name,
            api_key=captcha_key,
            sitekey=sitekey,
            site_url="https://discord.com",
            rqdata=rqdata,
            proxy=proxy_str,
            user_agent=ctx.UA,
            log_func=log_fn
        )
        
        if not cap:
            return None
        
        hdrs = ctx.get_headers(token)
        hdrs["X-Captcha-Key"] = cap
        if rqtoken: hdrs["X-Captcha-Rqtoken"] = rqtoken
        if session_id: hdrs["X-Captcha-Session-Id"] = session_id
        
        r2 = ctx.session.post(url, json=payload, headers=hdrs, timeout=30)
        return r2

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        token = token_entry.token
        password = token_entry.password or kwargs.get('password')
        email = token_entry.email or "N/A"
        
        solver_name = kwargs.get('captcha_solver', 'onyx')
        captcha_key = kwargs.get('captcha_api_key', '')
        sms_svc = kwargs.get('sms_service', '5sim')
        sms_api_key = kwargs.get('sms_api_key', '')
        sms_country = kwargs.get('sms_country', '6') # default id
        sms_operator = kwargs.get('sms_operator', 'any')
        
        proxy = kwargs.get('proxy')
        proxy_str = f"{proxy.host}:{proxy.port}" if proxy else ""
        
        if not password:
            self.log(token, "No password — SKIPPED (email:pass:token format required)", "ERROR")
            self.append_to_file("SKIPPED_NO_PASS", token_entry.raw_line, "Result")
            return {"success": False, "message": "No password", "status": "skipped"}

        ctx = SessionContext(proxy_str)
        ctx.get_fingerprint()
        
        log_fn = lambda m, l: self.log(token, m, l)

        # 1. Check current status
        log_fn("Checking account status...", "INFO")
        hdrs = ctx.get_headers(token)
        try:
            r = ctx.session.get("https://discord.com/api/v9/users/@me", headers=hdrs, timeout=15)
            if r.status_code == 401:
                log_fn("Invalid token", "ERROR")
                self.append_to_file("INVALID", token_entry.raw_line, "Result")
                return {"success": False, "status": "invalid"}
            
            data = r.json()
            if data.get("phone"):
                log_fn("Already has phone — skipping", "SUCCESS")
                self.append_to_file("ALREADY_VERIFIED", token_entry.raw_line, "Result")
                return {"success": True, "status": "already_verified"}
        except:
            log_fn("Connection error — skipping", "ERROR")
            return {"success": False, "status": "failed"}

        # 2. Purchase Phone
        log_fn(f"Purchasing phone ({sms_svc})...", "INFO")
        order_id, phone = sms_service.purchase_phone(
            service=sms_svc, api_key=sms_api_key, 
            country=sms_country, operator=sms_operator, 
            log_func=log_fn
        )
        if not order_id:
            return {"success": False, "message": "Failed to purchase phone", "status": "failed"}

        # 3. Add Phone to Discord
        log_fn(f"Adding phone {phone} to Discord...", "INFO")
        clean_phone = phone if phone.startswith("+") else f"+{phone}"
        url = "https://discord.com/api/v9/users/@me/phone"
        payload = {"phone": clean_phone, "change_phone_reason": "user_action_required"}
        
        r = ctx.session.post(url, json=payload, headers=ctx.get_headers(token), timeout=30)
        
        if r.status_code == 400 and "captcha_" in r.text:
            r = self._solve_and_retry_captcha(ctx, r.json(), token, url, payload, solver_name, captcha_key, proxy_str, log_fn)

        if not r or r.status_code not in [200, 204]:
            err_data = r.json() if r else {}
            log_fn(f"Failed to add phone: {err_data.get('message') or 'Unknown'}", "ERROR")
            sms_service.manage_order(sms_svc, sms_api_key, order_id, "cancel", log_func=log_fn)
            return {"success": False, "message": "Failed to add phone", "status": "failed"}

        # 4. Fetch OTP
        log_fn("Waiting for OTP...", "INFO")
        otp = sms_service.fetch_otp(sms_svc, sms_api_key, order_id, log_func=log_fn)
        if not otp:
            sms_service.manage_order(sms_svc, sms_api_key, order_id, "cancel", log_func=log_fn)
            return {"success": False, "message": "OTP timeout", "status": "failed"}

        # 5. Verify OTP
        log_fn(f"OTP received: {otp}. Verifying...", "INFO")
        url = "https://discord.com/api/v9/phone-verifications/verify"
        payload = {"code": otp, "phone": clean_phone}
        r = ctx.session.post(url, json=payload, headers=ctx.get_headers(token), timeout=30)
        
        if r.status_code not in [200, 204]:
            log_fn(f"OTP verification failed: {r.text}", "ERROR")
            sms_service.manage_order(sms_svc, sms_api_key, order_id, "cancel", log_func=log_fn)
            return {"success": False, "message": "OTP verification failed", "status": "failed"}

        phone_token = r.json().get("token")

        # 6. Finalize
        log_fn("Finalizing verification...", "INFO")
        url = "https://discord.com/api/v9/users/@me/phone"
        payload = {"password": password, "phone_token": phone_token}
        r = ctx.session.post(url, json=payload, headers=ctx.get_headers(token), timeout=30)
        
        if r.status_code in [200, 204]:
            log_fn("Phone verified successfully!", "SUCCESS")
            sms_service.manage_order(sms_svc, sms_api_key, order_id, "finish", log_func=log_fn)
            self.append_to_file("VERIFIED", f"{email}:{password}:{token} | Phone: {phone}", "Result")
            return {"success": True, "status": "verified"}
        else:
            log_fn(f"Finalization failed: {r.text}", "ERROR")
            return {"success": False, "message": "Finalization failed", "status": "failed"}

    def reset(self):
        self.clear_output()

