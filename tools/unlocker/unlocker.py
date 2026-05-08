import re
import time
import random
import threading
import webbrowser
import requests
import base64
import imaplib
import email as email_lib
from typing import Optional, Any, Tuple, List
from urllib.parse import urlparse, unquote

from core.token_parser import TokenEntry
from core.discord_api import DiscordAPI, ApiErrorType
from core.logger import AppLogger
from tools.base_tool import BaseTool
from tools.unlocker.email_service import get_email_provider
from tools.phone_verifier import captcha_solver

class Unlocker(BaseTool):
    """
    Unlocker Tool — Add email to locked/unclaimed Discord tokens.
    """
    
    TOOL_NAME = "unlocker"
    THUNDERBIRD_CID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

    def __init__(self, log_callback=None):
        super().__init__(log_callback=log_callback)
        self._patch_lock = threading.Lock()
        self._last_patch_time = 0
        self._last_graph_auth_ok = {} # email -> bool

    def _is_trusted_email(self, cat: str) -> bool:
        """Check if the selected email category is a trusted/graph type."""
        c = cat.lower()
        return any(x in c for x in ['trusted', 'graph'])

    def _write_result(self, normal_file: str, out_line: str, email_category: str, **kwargs):
        """Write output to the correct file."""
        if self._is_trusted_email(email_category):
            # Format: email:pass1:token:pass2 (pass2 is email pass)
            email = kwargs.get('new_email', "")
            epass = kwargs.get('email_password', "")
            token = kwargs.get('final_token', "")
            # We use a special TRUSTED file for these
            trusted_line = f"{email}:{epass}:{token}" # simplistic format
            self.append_to_file("TRUSTED", trusted_line, "Result")
        
        self.append_to_file(normal_file, out_line, "Result")

    def _extract_verify_token(self, email_body: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract Discord verification token from email HTML body."""
        # Clean body
        body = email_body.replace('\n', '').replace('\r', '').replace(' ', '')
        
        # 1. Look for direct verify link
        # Format: https://discord.com/verify#token=...
        matches = re.findall(r'href=[\'"]([^\'"]+)[\'"]', email_body)
        for link in matches:
            if "discord.com/verify" in link or "click.discord.com" in link:
                # If it's a click.discord.com link, we might need to resolve it or it might contain the token
                if "token=" in link:
                    tk_match = re.search(r'token=([a-zA-Z0-9_\.\-]+)', link)
                    if tk_match:
                        return tk_match.group(1), link
                
                # Try to resolve click link
                if "click.discord.com" in link:
                    try:
                        r = requests.get(link, allow_redirects=False, timeout=5)
                        loc = r.headers.get("Location", "")
                        if "token=" in loc:
                            tk_match = re.search(r'token=([a-zA-Z0-9_\.\-]+)', loc)
                            if tk_match:
                                return tk_match.group(1), loc
                    except:
                        pass
        
        # 2. Look for token in JSON-like structure often in HTML
        tk_match = re.search(r'["\']token["\']\s*:\s*["\']([a-zA-Z0-9_\.\-]{20,})["\']', body)
        if tk_match:
            return tk_match.group(1), None
            
        return None, None

    def _poll_graph_api(self, email_addr: str, refresh_token: str, client_id: str, max_retries=15, cancel_event=None) -> Tuple[Optional[str], Optional[str]]:
        """Poll inbox via Microsoft Graph API."""
        TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        access_token = None
        
        # 1. Get Access Token
        payload = {
            "client_id": client_id or self.THUNDERBIRD_CID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "https://graph.microsoft.com/Mail.Read offline_access"
        }
        try:
            resp = requests.post(TOKEN_URL, data=payload, timeout=8)
            access_token = resp.json().get("access_token")
        except:
            return None, None
            
        if not access_token:
            return None, None

        # 2. Poll Messages
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        params = {
            "$select": "subject,from,body",
            "$top": "5",
            "$orderby": "receivedDateTime desc"
        }
        
        for i in range(max_retries):
            if cancel_event and cancel_event.is_set():
                break
                
            try:
                # Check Inbox and Junk
                for folder in ["messages", "mailFolders/JunkEmail/messages"]:
                    url = f"https://graph.microsoft.com/v1.0/me/{folder}"
                    r = requests.get(url, headers=headers, params=params, timeout=6)
                    if r.status_code == 200:
                        messages = r.json().get("value", [])
                        for msg in messages:
                            subject = msg.get("subject", "").lower()
                            from_email = msg.get("from", {}).get("emailAddress", {}).get("address", "").lower()
                            
                            if "discord" in from_email or "verify" in subject:
                                body = msg.get("body", {}).get("content", "")
                                tk, lnk = self._extract_verify_token(body)
                                if tk:
                                    return tk, lnk
                
            except:
                pass
            
            time.sleep(random.uniform(1.5, 2.5))
            
        return None, None

    def _poll_hotmail007_api(self, api_key: str, full_account: str, max_retries=15, cancel_event=None) -> Tuple[Optional[str], Optional[str]]:
        """Poll 007hotmail native API."""
        # full_account is email:pass:refresh:cid
        for i in range(max_retries):
            if cancel_event and cancel_event.is_set():
                break
            
            try:
                for folder in ["inbox", "junkemail"]:
                    url = f"https://gapi.hotmail007.com/v1/mail/getFirstMail?clientKey={api_key}&account={full_account}&folder={folder}"
                    resp = requests.get(url, timeout=8)
                    data = resp.json()
                    
                    if data.get("code") == 0:
                        body = data.get("data", {}).get("body", "") or data.get("data", {}).get("html", "")
                        if body:
                            tk, lnk = self._extract_verify_token(body)
                            if tk:
                                return tk, lnk
            except:
                pass
            time.sleep(random.uniform(1.5, 2.5))
            
        return None, None

    def process_token(self, token_entry: TokenEntry, **kwargs) -> dict:
        token = token_entry.token
        email_service = kwargs.get('email_service', "zeus")
        api_key = kwargs.get('api_key', "")
        email_category = kwargs.get('email_category', "")
        cancel_event = kwargs.get('worker_cancel_event')
        
        if not api_key:
            return {"success": False, "status": "config_error", "message": "Missing API Key for Email Service"}

        api = DiscordAPI(token=token, proxy=kwargs.get('proxy'))
        
        # 1. Validate
        user_info = api.get_user_info()
        if not user_info.success:
            if user_info.error_type == ApiErrorType.UNAUTHORIZED:
                self.append_to_file("INVALID", token_entry.raw_line, "Result")
                return {"success": False, "status": "invalid", "message": "Token is invalid"}
            return {"success": False, "retry_later": True, "message": "Validation failed"}

        # 2. Get Email
        self.log(token, "Getting an email...", "INFO")
        provider = get_email_provider(email_service, api_key, email_category)
        if not provider:
            return {"success": False, "message": f"Unknown email service: {email_service}"}
            
        email_res = provider.get_email()
        if not email_res.get("success"):
            return {"success": False, "message": f"Email purchase failed: {email_res.get('message')}"}
            
        new_email = email_res["email"]
        full_account = email_res["full_account"]
        metadata = email_res.get("metadata", {})
        
        self.log(token, f"Successfully got email: {new_email}", "SUCCESS")

        # 3. Patch Email
        new_password = metadata.get("password") or kwargs.get('custom_password') or "StrongPass123!"
        
        payload = {"email": new_email}
        # If it's an unclaimed token, we might need to provide a password or it might be a claim flow
        # In THEBOY TOOLS, we usually do PATCH /users/@me with {email: ...}
        
        with self._patch_lock:
            now = time.time()
            elapsed = now - self._last_patch_time
            if elapsed < 0.15:
                time.sleep(0.15 - elapsed)
            
            patch_res = api.update_profile(email=new_email)
            self._last_patch_time = time.time()

        if not patch_res.success:
            if patch_res.error_type == ApiErrorType.CAPTCHA_REQUIRED:
                # We need to solve captcha or return
                self.log(token, "Captcha required on PATCH — requeuing...", "WARNING")
                return {"success": False, "retry_later": True, "status": "captcha"}
                
            self.log(token, f"Email patch failed: {patch_res.error_message}", "ERROR")
            self.append_to_file("FAILED_UNLOCK", f"{token_entry.raw_line} | Reason: {patch_res.error_message}", "Result")
            return {"success": False, "message": f"PATCH failed: {patch_res.error_message}"}

        self.log(token, "Email patched, polling inbox...", "INFO")

        # 4. Poll Inbox
        found_tk, found_lk = None, None
        if email_service == "zeus" or email_service == "lution":
            rt = metadata.get("refresh_token")
            cid = metadata.get("client_id")
            if rt:
                found_tk, found_lk = self._poll_graph_api(new_email, rt, cid, cancel_event=cancel_event)
        
        if not found_tk and email_service == "007hotmail":
            found_tk, found_lk = self._poll_hotmail007_api(api_key, full_account, cancel_event=cancel_event)

        if not found_tk:
            self.log(token, "Timeout waiting for verification email", "ERROR")
            return {"success": False, "message": "Verification timeout"}

        self.log(token, f"Verification link found! Submitting...", "SUCCESS")

        # 5. Verify Link
        # This usually involves submitting the token to /verify
        verify_res = api.verify_email(found_tk)
        
        if verify_res.success:
            final_token = verify_res.data.get("token", token)
            out_line = f"{new_email}:{metadata.get('password')}:{final_token}"
            
            self._write_result("UNLOCKED", out_line, email_category, 
                               new_email=new_email, 
                               email_password=metadata.get('password'), 
                               final_token=final_token)
            
            self.log(token, f"Unlocked! Email: {new_email}", "SUCCESS")
            return {"success": True, "status": "unlocked", "final_token": final_token}
        else:
            if verify_res.error_type == ApiErrorType.CAPTCHA_REQUIRED:
                self.log(token, "Captcha on verify — solve in browser or solver required", "WARNING")
                # In a real scenario, we'd call captcha_solver here
                # solver_name = kwargs.get('solver_name')
                # if solver_name: ...
                return {"success": False, "message": "Captcha on verify", "status": "captcha"}
                
            self.log(token, f"Verification failed: {verify_res.error_message}", "ERROR")
            return {"success": False, "message": f"Verify failed: {verify_res.error_message}"}

    def reset(self):
        self.clear_output()
        self._last_graph_auth_ok.clear()

