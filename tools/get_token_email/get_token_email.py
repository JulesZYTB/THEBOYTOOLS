import time
import random
from typing import Optional, Any

from core.token_parser import TokenEntry
from core.proxy_manager import ProxyEntry
from core.discord_api import DiscordAPI, ApiErrorType
from tools.base_tool import BaseTool

class GetTokenEmail(BaseTool):
    """
    Get Token Email — Fetches the email associated with a Discord token.
    """
    
    TOOL_NAME = "get_token_email"

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        proxy = kwargs.get('proxy')
        token = token_entry.token
        
        # 1. Check if we already have it
        if token_entry.email and token_entry.email != "N/A":
            self.log(token, f"Already has email — skipped", "INFO")
            self.append_to_file("SKIPPED", token_entry.raw_line, "Result")
            return {"success": True, "status": "skipped", "message": "Already has email"}

        api = DiscordAPI(token=token, proxy=proxy, max_retries=3)
        
        # 2. Fetch User Info
        response = api.get_user_info()
        
        if not response.success:
            if response.error_type == ApiErrorType.RATE_LIMITED:
                self.log(token, "Rate Limited — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "rate_limited"}
            
            if response.error_type == ApiErrorType.UNAUTHORIZED:
                self.log(token, "Invalid — 401 Unauthorized", "ERROR")
                self.append_to_file("INVALID", token_entry.raw_line, "Result")
                return {"success": False, "status": "invalid"}
            
            self.log(token, f"Error — {response.error_message}", "ERROR")
            return {"success": False, "retry_later": True, "status": "error"}

        # 3. Extract Email
        data = response.data
        email = data.get("email", "").strip()
        
        if not email:
            self.log(token, "No email on this account", "WARNING")
            self.append_to_file("NO_EMAIL", token_entry.raw_line, "Result")
            return {"success": True, "status": "no_email"}

        # 4. Build output line
        # Logic: email:token OR email:pass:token
        if token_entry.password:
            output_line = f"{email}:{token_entry.password}:{token}"
        else:
            output_line = f"{email}:{token}"

        self.log(token, f"Got email → {email}", "SUCCESS")
        self.append_to_file("GOT_EMAIL", output_line, "Result")
        
        return {"success": True, "status": "got_email", "email": email}

    def reset(self):
        self.clear_output()

