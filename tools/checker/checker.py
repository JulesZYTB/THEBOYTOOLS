import time
import random
from datetime import datetime, timezone
from math import ceil
from typing import Optional, Any

from core.token_parser import TokenEntry
from core.proxy_manager import ProxyEntry
from core.discord_api import DiscordAPI, ApiErrorType
from tools.base_tool import BaseTool

class Checker(BaseTool):
    """
    Checker Tool — Validates Discord tokens and classifies their status.
    """
    
    TOOL_NAME = "checker"
    DISCORD_EPOCH = 1420070400000

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        proxy = kwargs.get('proxy')
        api = DiscordAPI(token=token_entry.token, proxy=proxy)
        
        # 1. Probe for validity (GET /users/@me/guilds is a reliable check)
        # We use a raw request for the probe to handle 403/401 specifically
        headers = api._get_headers()
        proxies = api._proxy_dict
        
        guilds_status = None
        retry_after = 0
        
        for attempt in range(3):
            try:
                import requests
                resp = requests.get(
                    "https://discord.com/api/v9/users/@me/guilds",
                    headers=headers,
                    proxies=proxies,
                    timeout=10,
                    verify=False
                )
                guilds_status = resp.status_code
                if guilds_status == 429:
                    data = resp.json()
                    retry_after = data.get("retry_after", 1.0)
                    time.sleep(min(retry_after, 3.0))
                    continue
                break
            except Exception:
                if attempt == 2:
                    return {"success": False, "status": "network_error", "message": "Proxy failed or timed out"}
                time.sleep(1)

        if guilds_status == 401:
            self.log(token_entry.token, "Invalid — Token expired or revoked", "ERROR")
            self.append_to_file("INVALID", token_entry.raw_line, "Result")
            return {"success": False, "status": "invalid", "message": "Invalid — Token expired or revoked"}

        # 2. Fetch User Info for detailed classification
        user_resp = api.get_user_info()
        if not user_resp.success:
            if user_resp.error_type == ApiErrorType.UNAUTHORIZED:
                self.append_to_file("INVALID", token_entry.raw_line, "Result")
                return {"success": False, "status": "invalid", "message": "Invalid — 401 Unauthorized"}
            return {"success": False, "status": "error", "message": f"Error — {user_resp.error_message}"}

        data = user_resp.data
        username = data.get("username", "Unknown")
        email = data.get("email")
        phone = data.get("phone")
        verified = data.get("verified", False)
        mfa = data.get("mfa_enabled", False)
        premium_type = data.get("premium_type", 0)
        user_id = data.get("id", "0")
        avatar = data.get("avatar")
        flags = data.get("flags", 0)
        public_flags = data.get("public_flags", 0)
        all_flags = flags | public_flags
        
        # Classification Logic
        is_locked = (guilds_status == 403)
        status_label = "VALID"
        result_file = "VALID"
        
        if is_locked:
            if email and not phone:
                status_label = "Locked Phone"
                result_file = "LOCKED_PHONE"
            elif not email and not phone:
                status_label = "Locked Mail"
                result_file = "LOCKED_MAIL" # Unclaimed or generic lock
            else:
                status_label = "Locked Mail"
                result_file = "LOCKED_MAIL"
        else:
            if email and phone:
                status_label = "Full Verified"
                result_file = "FULL_VERIFIED"
            elif email:
                status_label = "Email Verified"
                result_file = "EMAIL_VERIFIED"
            elif phone:
                status_label = "Phone Verified"
                result_file = "PHONE_VERIFIED"
            else:
                status_label = "Unclaimed"
                result_file = "UNCLAIMED"

        # Age Calculation
        try:
            timestamp = (int(user_id) >> 22) + self.DISCORD_EPOCH
            created_dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            age_delta = datetime.now(timezone.utc) - created_dt
            account_age_days = age_delta.days
        except:
            account_age_days = 0
            created_dt = datetime.now()

        # Extra Info
        nitro_map = {0: "None", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic"}
        nitro_type = nitro_map.get(premium_type, "None")
        has_nitro = premium_type > 0
        is_spammer = bool(all_flags & (1 << 20))
        has_avatar = avatar is not None
        
        # Save results
        self.append_to_file(result_file, token_entry.raw_line, "Result")
        
        # Age Output
        age_suffix = "" if verified else "_UNVERIFIED"
        self.append_to_file(f"{account_age_days}day{age_suffix}", token_entry.raw_line, "Check_Age")
        
        # Avatar Output
        self.append_to_file("Has_Avatar" if has_avatar else "No_Avatar", token_entry.raw_line, "Check_Avatar")
        
        # Nitro Output
        nitro_file = "No_Nitro"
        if premium_type == 1: nitro_file = "Nitro_Classic"
        elif premium_type == 2: nitro_file = "Nitro"
        elif premium_type == 3: nitro_file = "Nitro_Basic"
        self.append_to_file(nitro_file, token_entry.raw_line, "Check_Nitro")
        
        # Spammer Output
        spam_suffix = "" if verified else "_UNVERIFIED"
        self.append_to_file(f"{'Spammer' if is_spammer else 'Not_Spammer'}{spam_suffix}", token_entry.raw_line, "Check_Spammer")

        # Logging
        msg = f"{status_label} | {username} | Email: {email or 'None'} | Phone: {phone or 'None'}"
        if has_nitro:
            msg += f" → Nitro: {nitro_type}"
        msg += f" → Age: {account_age_days}d"
        
        self.log(token_entry.token, msg, "SUCCESS" if not is_locked else "WARNING")
        
        return {
            "success": not is_locked,
            "status": result_file.lower(),
            "message": msg,
            "data": {
                "username": username,
                "email": email,
                "phone": phone,
                "nitro": nitro_type,
                "age_days": account_age_days,
                "is_spammer": is_spammer,
                "has_avatar": has_avatar,
                "is_locked": is_locked
            }
        }

    def reset(self):
        """Clear output for fresh run."""
        self.clear_output()

