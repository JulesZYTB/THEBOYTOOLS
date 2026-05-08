import string
import random
import time
from typing import Optional, Any

from core.token_parser import TokenEntry
from core.proxy_manager import ProxyEntry
from core.discord_api import DiscordAPI, ApiErrorType
from tools.base_tool import BaseTool

class Changer(BaseTool):
    """
    Password Changer Tool — Change passwords on Discord tokens.
    """
    
    TOOL_NAME = "changer"

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)

    def _generate_random_password(self, length: int = 16) -> str:
        """Generate a strong random password (unique per call)."""
        chars = string.ascii_letters + string.digits + "!@#$%&*"
        password = "".join(random.choice(chars) for _ in range(length))
        # Ensure at least one of each for "strength"
        # (Though simple random usually hits them all at length 16)
        return password

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        proxy = kwargs.get('proxy')
        new_password = kwargs.get('new_password', "")
        use_random_password = kwargs.get('use_random_password', False)
        
        if use_random_password:
            new_password = self._generate_random_password()
            
        if not new_password:
            return {"success": False, "status": "failed", "message": "No new password provided", "reason": "no_password"}

        old_pw = token_entry.password
        if not old_pw:
            self.log(token_entry.token, "Token has no current password — use email:pass:token format", "ERROR")
            return {"success": False, "status": "failed", "message": "Token has no current password", "reason": "no_current_password"}

        api = DiscordAPI(token=token_entry.token, proxy=proxy)
        token_line = token_entry.raw_line
        
        # Jitter sleep to avoid simultaneous hits
        time.sleep(random.uniform(0.1, 0.5))
        
        try:
            response = api.change_password(old_pw, new_password)
            
            if response.success:
                new_token = response.data.get("token", token_entry.token)
                email = token_entry.email or "N/A"
                new_line = f"{email}:{new_password}:{new_token}"
                
                self.append_to_file("CHANGED", new_line, "Result")
                self.log(token_entry.token, f"Password changed | old={old_pw}, New={new_password}", "SUCCESS")
                return {"success": True, "status": "changed", "message": "Password changed successfully", "new_token": new_token}
            
            # Handle Failure Modes
            if response.error_type == ApiErrorType.CAPTCHA_REQUIRED:
                self.log(token_entry.token, "Captcha required — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "captcha"}
                
            if response.error_type == ApiErrorType.RATE_LIMITED:
                retry = response.retry_after or "?"
                self.log(token_entry.token, f"Rate Limited — retry after {retry}s — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "rate_limited"}

            if response.error_type == ApiErrorType.UNAUTHORIZED:
                # Could be wrong pass or token invalid
                err_msg = response.error_message or ""
                reason = "Incorrect Pass" if "password" in err_msg.lower() else "Invalid Token"
                self.append_to_file("INVALID", f"{token_line} | Reason: {reason}", "Result")
                self.log(token_entry.token, f"Invalid — {reason}", "ERROR")
                return {"success": False, "status": "invalid", "message": f"Invalid — {reason}"}

            if response.error_type == ApiErrorType.NETWORK_ERROR:
                self.log(token_entry.token, "Network error — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "network_error"}

            # Generic failure
            reason = response.error_message or "Unknown error"
            self.append_to_file("FAILED", f"{token_line} | Reason: {reason}", "Result")
            self.log(token_entry.token, f"Failed — {reason}", "ERROR")
            return {"success": False, "status": "failed", "message": f"Failed — {reason}"}

        except Exception as e:
            self.log(token_entry.token, f"Exception — {str(e)} — requeuing...", "ERROR")
            return {"success": False, "retry_later": True, "status": "error"}

    def reset(self):
        """Clear output files for a fresh run."""
        self.clear_output()

