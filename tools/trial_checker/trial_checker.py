import time
import random
from datetime import datetime, timezone
from typing import Optional, Any

from core.token_parser import TokenEntry
from core.proxy_manager import ProxyEntry
from core.discord_api import DiscordAPI, ApiErrorType
from tools.base_tool import BaseTool

class TrialChecker(BaseTool):
    """
    TrialChecker — Checks Discord tokens for active Nitro trial offers.
    """
    
    TOOL_NAME = "trial_checker"
    
    TRIAL_30D_ID = "520373071933079552"
    TRIAL_14D_ID = "983601860436819969"

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)

    def _parse_expires(self, raw: str) -> str:
        """
        Parse an ISO-8601 expiry timestamp and return a human-friendly string like '10 days'.
        """
        if not raw or raw == "?": return "N/A"
        
        cleaned = raw.strip().replace('Z', '+00:00')
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d'
        ]
        
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(cleaned, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                break
            except (ValueError, OSError):
                continue
                
        if not dt:
            return raw[:10] # Fallback to start of string
            
        now = datetime.now(timezone.utc)
        delta = dt - now
        days = max(0, int(delta.total_seconds() / 86400))
        
        if days == 1:
            return "1 day"
        return f"{days} days"

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        proxy = kwargs.get('proxy')
        token = token_entry.token
        token_line = token_entry.raw_line
        tok_preview = f"{token[:20]}..."
        
        api = DiscordAPI(token=token, proxy=proxy, max_retries=3)
        
        # 1. Fetch Trial Offer
        response = api.check_trial_offer()
        
        if not response.success:
            if response.error_type == ApiErrorType.RATE_LIMITED:
                self.log(token, f"[{tok_preview}] Rate Limited — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "rate_limited"}
            
            if response.error_type == ApiErrorType.UNAUTHORIZED:
                self.log(token, f"[{tok_preview}] Invalid — 401 Unauthorized", "ERROR")
                self.append_to_file("INVALID", token_line, "Result")
                return {"success": False, "status": "invalid"}
            
            if response.error_type == ApiErrorType.FORBIDDEN:
                self.log(token, f"[{tok_preview}] Locked — 403 Forbidden", "ERROR")
                self.append_to_file("LOCKED", token_line, "Result")
                return {"success": False, "status": "locked"}
                
            self.log(token, f"[{tok_preview}] Error — {response.error_message}", "ERROR")
            return {"success": False, "retry_later": True, "status": "error"}

        data = response.data
        trial_offer = data.get("user_trial_offer")
        
        if not trial_offer:
            self.log(token, f"[{tok_preview}] No Trial", "INFO")
            self.append_to_file("NO_TRIAL", token_line, "Result")
            return {"success": True, "status": "no_trial"}

        # 2. Extract Details
        trial_id = str(trial_offer.get("trial_id", ""))
        raw_expires = trial_offer.get("expires_at", "?")
        expires_str = self._parse_expires(raw_expires)
        
        status = "trial_other"
        label = "Trial"
        output_file = "trial_other"

        if trial_id == self.TRIAL_30D_ID:
            status = "trial_30d"
            label = "30-Day Trial"
            output_file = "trial_30d"
        elif trial_id == self.TRIAL_14D_ID:
            status = "trial_14d"
            label = "14-Day Trial"
            output_file = "trial_14d"

        msg = f"[{tok_preview}] FOUND → {label} | Expires: {expires_str} | ID: {trial_id}"
        self.log(token, msg, "SUCCESS")
        self.append_to_file(output_file, f"{token_line} | {expires_str} | {trial_id}", "Result")
        
        return {
            "success": True, 
            "status": status, 
            "trial_id": trial_id, 
            "expires_at": expires_str
        }

    def reset(self):
        self.clear_output()

