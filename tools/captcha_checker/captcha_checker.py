import time
import random
from typing import Optional, Any

from core.token_parser import TokenEntry
from core.discord_api import DiscordAPI, ApiErrorType
from tools.base_tool import BaseTool

class CaptchaChecker(BaseTool):
    """
    CaptchaChecker — Check if tokens have a join captcha without actually joining a server.
    """
    
    TOOL_NAME = "captcha_checker"
    _JITTER_MIN = 0.05
    _JITTER_MAX = 0.3
    _MAX_TOOL_RETRIES = 2

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        proxy = kwargs.get('proxy')
        token = token_entry.token
        token_line = token_entry.raw_line
        tok_preview = f"{token[:20]}..."
        
        api = DiscordAPI(token=token, proxy=proxy, max_retries=3)
        
        # 1. Basic Validation
        check_resp = api.get_user_info()
        if not check_resp.success:
            if check_resp.is_rate_limited():
                retry_after = check_resp.retry_after or 5
                self.log(token, f"[{tok_preview}] Rate limited, retry after {retry_after}s", "WARNING")
                return {"success": False, "retry_later": True, "status": "rate_limited", "message": f"Rate limited ({retry_after}s)"}
            
            if check_resp.error_type == ApiErrorType.UNAUTHORIZED:
                self.log(token, f"[{tok_preview}] Invalid — 401 Unauthorized", "ERROR")
                self.append_to_file("INVALID", token_line, "Result")
                return {"success": False, "status": "invalid", "message": "Unauthorized (401)"}
            
            self.log(token, f"[{tok_preview}] Error — {check_resp.error_message}", "ERROR")
            return {"success": False, "retry_later": True, "status": "error", "message": check_resp.error_message}

        # 2. Probe for Captcha
        # We try to join a "permanent" server like midjourney to see if it triggers captcha
        invite_code = kwargs.get('invite_code', 'midjourney')
        
        time.sleep(random.uniform(self._JITTER_MIN, self._JITTER_MAX))
        
        response = api.join_guild(invite_code)
        
        if not response.success:
            if response.error_type == ApiErrorType.RATE_LIMITED:
                self.log(token, f"[{tok_preview}] Rate limited on invite — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "rate_limited", "message": "Invite rate limited"}
            
            if response.error_type == ApiErrorType.CAPTCHA_REQUIRED:
                self.log(token, f"[{tok_preview}] Captcha Detected", "WARNING")
                self.append_to_file("CAPTCHA", token_line, "Result")
                return {"success": True, "status": "captcha_detected", "is_captcha": True, "message": "Captcha Required"}
            
            if response.error_type == ApiErrorType.FORBIDDEN:
                self.log(token, f"[{tok_preview}] Locked — Verification Required", "ERROR")
                self.append_to_file("LOCKED", token_line, "Result")
                return {"success": False, "status": "locked", "message": "Verification Required"}

            if response.error_type == ApiErrorType.UNAUTHORIZED:
                self.log(token, f"[{tok_preview}] Invalid Token", "ERROR")
                self.append_to_file("INVALID", token_line, "Result")
                return {"success": False, "status": "invalid", "message": "Token Revoked"}

            self.log(token, f"[{tok_preview}] Error — {response.error_message}", "ERROR")
            return {"success": False, "retry_later": True, "status": "error", "message": response.error_message}

        # 3. Success means no captcha (or already joined)
        # Check if it was already joined (code 40005 / 40002 etc)
        error_data = response.data or {}
        discord_code = error_data.get("code", 0)
        
        self.append_to_file("NO_CAPTCHA", token_line, "Result")
        msg = "No Captcha (Already joined)" if discord_code == 40005 else "No Captcha"
        return {"success": True, "status": "no_captcha", "is_captcha": False, "message": msg}

    def reset(self):
        self.clear_output()

