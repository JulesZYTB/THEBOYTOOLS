import time
import random
from typing import Optional, Any, List

from core.token_parser import TokenEntry
from core.proxy_manager import ProxyEntry
from core.discord_api import DiscordAPI, ApiErrorType
from tools.base_tool import BaseTool

class TokenCleaner(BaseTool):
    """
    TokenCleaner — Leave all servers & close all DMs to make tokens look fresh.
    """
    
    TOOL_NAME = "token_cleaner"

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        proxy = kwargs.get('proxy')
        leave_servers = kwargs.get('leave_servers', True)
        close_dms = kwargs.get('close_dms', True)
        target_guild_id = kwargs.get('target_guild_id', "")
        
        token = token_entry.token
        token_line = token_entry.raw_line
        tok_preview = f"{token[:20]}..."
        
        api = DiscordAPI(token=token, proxy=proxy, max_retries=3)
        
        # 1. Validation
        user_resp = api.get_user_info()
        if not user_resp.success:
            if user_resp.error_type == ApiErrorType.RATE_LIMITED:
                self.log(token, f"[{tok_preview}] Rate limited on validation — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "rate_limited"}
            if user_resp.error_type == ApiErrorType.UNAUTHORIZED:
                self.log(token, f"[{tok_preview}] Invalid — 401 Unauthorized", "ERROR")
                self.append_to_file("INVALID", token_line, "Result")
                return {"success": False, "status": "invalid"}
            
            self.log(token, f"[{tok_preview}] Error on validation — {user_resp.error_message}", "ERROR")
            return {"success": False, "retry_later": True, "status": "error"}

        guilds_left = 0
        dms_closed = 0

        # 2. Leave Servers
        if leave_servers:
            if target_guild_id:
                leave_resp = api.leave_guild(target_guild_id)
                if leave_resp.success:
                    self.log(token, f"[{tok_preview}] Left guild {target_guild_id}", "INFO")
                    guilds_left = 1
                elif leave_resp.error_type == ApiErrorType.NOT_FOUND:
                    self.log(token, f"[{tok_preview}] Not in guild {target_guild_id}", "WARNING")
                elif leave_resp.is_rate_limited():
                    return {"success": False, "retry_later": True, "status": "rate_limited", "message": "Rate limited leaving guild"}
            else:
                guilds_resp = api.get_guilds()
                if guilds_resp.success:
                    guilds = guilds_resp.data
                    self.log(token, f"[{tok_preview}] Found {len(guilds)} guilds to leave", "INFO")
                    for guild in guilds:
                        gid = guild.get("id")
                        gname = guild.get("name", "Unknown")
                        if guild.get("owner"):
                            self.log(token, f"[{tok_preview}] Skipped {gname} (owner)", "INFO")
                            continue
                        
                        time.sleep(random.uniform(0.3, 0.8))
                        leave_resp = api.leave_guild(gid)
                        if leave_resp.success:
                            guilds_left += 1
                        elif leave_resp.is_rate_limited():
                            self.log(token, f"[{tok_preview}] Rate limited leaving servers — requeuing...", "WARNING")
                            return {"success": False, "retry_later": True, "status": "rate_limited"}
                else:
                    self.log(token, f"[{tok_preview}] Could not fetch guilds: {guilds_resp.error_message}", "ERROR")

        # 3. Close DMs
        if close_dms:
            dms_resp = api.get_dm_channels()
            if dms_resp.success:
                channels = dms_resp.data
                self.log(token, f"[{tok_preview}] Found {len(channels)} DM channels to close", "INFO")
                for ch in channels:
                    ch_id = ch.get("id")
                    time.sleep(random.uniform(0.1, 0.4))
                    close_resp = api.close_dm_channel(ch_id)
                    if close_resp.success:
                        dms_closed += 1
                    elif close_resp.is_rate_limited():
                        self.log(token, f"[{tok_preview}] Rate limited closing DMs — requeuing...", "WARNING")
                        return {"success": False, "retry_later": True, "status": "rate_limited"}
            else:
                self.log(token, f"[{tok_preview}] Could not fetch DMs: {dms_resp.error_message}", "ERROR")

        # 4. Finalize
        msg = f"[{tok_preview}] Cleaned — Left {guilds_left} servers, Closed {dms_closed} DMs"
        self.log(token, msg, "SUCCESS")
        self.append_to_file("CLEANED", f"{token_line} | {msg}", "Result")
        return {"success": True, "status": "cleaned", "guilds_left": guilds_left, "dms_closed": dms_closed}

    def reset(self):
        """Clear output files for a fresh run."""
        self.clear_output()

