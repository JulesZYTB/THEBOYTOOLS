import re
import random
import time
from typing import Optional, Any

from core.token_parser import TokenEntry
from core.proxy_manager import ProxyEntry
from core.discord_api import DiscordAPI, ApiErrorType
from tools.base_tool import BaseTool

class Joiner(BaseTool):
    """
    Joiner Tool — Join Discord tokens to servers via invite code.
    """
    
    TOOL_NAME = "joiner"

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)

    def _extract_invite_code(self, raw: str) -> str:
        """Extract invite code from any URL format or plain code."""
        raw = raw.strip()
        prefixes = (
            'https://discord.gg/', 'http://discord.gg/', 
            'https://discord.com/invite/', 'http://discord.com/invite/',
            'discord.gg/', 'discord.com/invite/'
        )
        for p in prefixes:
            if raw.startswith(p):
                raw = raw.replace(p, "")
        
        # Remove any trailing path/params (?, #, /)
        raw = re.split(r'[?#/]', raw)[0]
        return raw

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        proxy = kwargs.get('proxy')
        invite_raw = kwargs.get('invite_code', "")
        change_name = kwargs.get('change_name', False)
        new_name = kwargs.get('new_name', "")
        
        invite_code = self._extract_invite_code(invite_raw)
        if not invite_code:
            return {"success": False, "status": "failed", "message": "No invite code provided", "reason": "no_invite"}

        api = DiscordAPI(token=token_entry.token, proxy=proxy)
        token_line = token_entry.raw_line
        
        # 1. Pre-flight check (is token valid?)
        check_resp = api.get_user_info()
        if not check_resp.success:
            if check_resp.error_type == ApiErrorType.RATE_LIMITED or check_resp.error_type == ApiErrorType.NETWORK_ERROR:
                self.log(token_entry.token, "Rate limit or Network error on pre-flight — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "rate_limited" if check_resp.is_rate_limited() else "network_error"}
            
            if check_resp.error_type == ApiErrorType.UNAUTHORIZED:
                self.append_to_file("INVALID", token_line, "Result")
                self.log(token_entry.token, "Invalid — 401 Unauthorized", "ERROR")
                return {"success": False, "status": "invalid", "message": "Invalid — Token expired or revoked"}
            
            reason = check_resp.error_message or "Invalid Token (or WAF Block)"
            self.log(token_entry.token, f"Error — {reason}", "ERROR")
            return {"success": False, "status": "error", "message": f"Error — {reason}"}

        # 2. Join Server
        response = api.join_guild(invite_code)
        
        if response.success:
            guild_name = response.data.get("guild", {}).get("name", "Unknown Server")
            name_msg = ""
            
            # 3. Optional Name Change
            if change_name and new_name:
                name_resp = api.update_profile(display_name=new_name)
                if name_resp.success:
                    name_msg = f" | Name changed to: {new_name}"
                else:
                    name_msg = f" | Failed to change name"
            
            self.append_to_file("JOINED", token_line, "Result")
            msg = f"Joined — {guild_name}{name_msg}"
            self.log(token_entry.token, msg, "SUCCESS")
            return {"success": True, "status": "joined", "message": msg, "guild_name": guild_name}
        
        # 4. Handle Failure
        if response.error_type == ApiErrorType.RATE_LIMITED:
            retry = response.retry_after or "?"
            self.log(token_entry.token, f"Rate Limited — retry after {retry}s", "WARNING")
            return {"success": False, "retry_later": True, "status": "rate_limited", "message": f"Rate limited — will be retried on next run"}
        
        reason = self._get_failure_reason(response)
        self.append_to_file("FAILED", f"{token_line} | Reason: {reason}", "Result")
        msg = f"Failed — {reason}"
        self.log(token_entry.token, msg, "ERROR")
        return {"success": False, "status": "failed", "message": msg, "reason": reason}

    def _get_failure_reason(self, response) -> str:
        """Get a human-readable failure reason."""
        if response.error_type == ApiErrorType.UNAUTHORIZED:
            return "Invalid token (401)"
        if response.error_type == ApiErrorType.CAPTCHA_REQUIRED:
            return "Captcha required"
        
        if response.error_type == ApiErrorType.FORBIDDEN:
            code = response.data.get("code") if isinstance(response.data, dict) else 0
            reason_map = {
                40007: "User banned from this server",
                50009: "Cannot send to this user",
                30001: "Maximum number of guilds reached",
                50001: "Missing access",
                50013: "Missing permissions",
                40001: "Unauthorized",
                40002: "Phone verification required",
                10008: "Unknown Message (Invite source missing)"
            }
            return reason_map.get(code, f"Forbidden: {response.error_message or code}")
            
        if response.error_type == ApiErrorType.NOT_FOUND:
            return "Invalid invite code or expired"
            
        if response.error_type == ApiErrorType.RATE_LIMITED:
            retry = response.retry_after or "?"
            return f"Rate limited (retry after {retry}s)"
            
        if response.error_type == ApiErrorType.NETWORK_ERROR:
            return "Network error — check proxy/connection"
            
        return response.error_message or "Unknown error"

    def reset(self):
        """Clear output files for a fresh run."""
        self.clear_output()


