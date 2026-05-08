import requests
import re
import time
from typing import List, Any, Optional

class EmailProvider:
    def __init__(self, api_key: str, email_category: str):
        self.api_key = api_key
        self.email_category = email_category

    def get_email(self) -> dict:
        raise NotImplementedError("Subclasses must implement get_email")

class ZeusProvider(EmailProvider):
    def get_email(self) -> dict:
        url = f"https://api.zeus-x.ru/purchase?apikey={self.api_key}&accountcode={self.email_category}"
        try:
            resp = requests.get(url, timeout=15)
            data = resp.json()
            
            # Zeus sometimes returns success: false or an error code
            if data.get("Code") != 0 and data.get("code") != 0:
                return {"success": False, "message": data.get("Message") or data.get("message") or "Unknown error"}

            # Accounts are usually in Data.Accounts or similar
            accounts = data.get("Data", {}).get("Accounts", [])
            if not accounts:
                # Try fallback parsing from raw text if possible, or handle empty list
                return {"success": False, "message": "No accounts in response"}

            acc = accounts[0]
            email = acc.get("Email") or acc.get("email")
            password = acc.get("Password") or acc.get("password") or acc.get("pass", "")
            refresh_token = acc.get("RefreshToken") or acc.get("graph_refresh_token") or acc.get("refresh_token", "")
            client_id = acc.get("ClientId") or acc.get("thunderbird_client_id") or acc.get("client_id", "")

            if not email:
                # Try regex on raw response as last resort
                match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', resp.text)
                if match:
                    email = match.group(1)
                else:
                    return {"success": False, "message": f"No email found in Zeus response. Raw: {resp.text[:200]}"}

            full_acc = f"{email}:{password}"
            if refresh_token:
                full_acc += f":{refresh_token}"
                if client_id:
                    full_acc += f":{client_id}"

            return {
                "success": True,
                "email": email,
                "full_account": full_acc,
                "metadata": {
                    "password": password,
                    "refresh_token": refresh_token,
                    "client_id": client_id
                }
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

class Hotmail007Provider(EmailProvider):
    def get_email(self) -> dict:
        url = f"https://gapi.hotmail007.com/api/mail/getMail?clientKey={self.api_key}&mailType={self.email_category}&quantity=1"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            if not data.get("success"):
                return {"success": False, "message": data.get("message") or "Unknown error"}

            acc_list = data.get("data", [])
            if not acc_list:
                return {"success": False, "message": "No accounts available"}

            raw = acc_list[0] # email:pass or email:pass:refresh:clientid
            parts = raw.split(":")
            email = parts[0]
            password = parts[1] if len(parts) > 1 else ""
            refresh_tok = parts[2] if len(parts) > 2 else ""
            cid = parts[3] if len(parts) > 3 else ""

            return {
                "success": True,
                "email": email,
                "full_account": raw,
                "metadata": {
                    "password": password,
                    "refresh_token": refresh_tok,
                    "client_id": cid
                }
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

class LutionProvider(EmailProvider):
    def get_email(self) -> dict:
        url = f"https://api.lution.ee/v2/email/buy?apikey={self.api_key}"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "category": self.email_category,
            "quantity": 1
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            data = resp.json()

            if not data.get("success"):
                return {"success": False, "message": data.get("message") or "Unknown error"}

            emails = data.get("emails", [])
            if not emails:
                return {"success": False, "message": "No emails in response"}

            acc_info = emails[0]
            email = acc_info.get("email")
            password = acc_info.get("password", "")
            refresh_token = acc_info.get("refresh_token", "")
            client_id = acc_info.get("client_id", "")

            full_acc = f"{email}:{password}"
            if refresh_token:
                full_acc += f":{refresh_token}:{client_id}"

            return {
                "success": True,
                "email": email,
                "full_account": full_acc,
                "metadata": {
                    "password": password,
                    "refresh_token": refresh_token,
                    "client_id": client_id
                }
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

EMAIL_CATALOGS = {
    "zeus": [
        {'display': 'Hotmail New', 'api_param': 'HOTMAIL', 'price': 0.002, 'lifetime': '1-5h'},
        {'display': 'Outlook New', 'api_param': 'OUTLOOK', 'price': 0.002, 'lifetime': '1-5h'},
        {'display': 'Hotmail Trusted (Graph)', 'api_param': 'HOTMAIL_TRUSTED_GRAPH_API', 'price': 0.01, 'lifetime': '3-6 months'},
        {'display': 'Outlook Trusted (Graph)', 'api_param': 'OUTLOOK_TRUSTED_GRAPH_API', 'price': 0.01, 'lifetime': '3-6 months'},
        {'display': 'Hotmail Trusted (IMAP)', 'api_param': 'HOTMAIL_TRUSTED', 'price': 0.01, 'lifetime': '3-6 months'},
        {'display': 'Outlook Trusted (IMAP)', 'api_param': 'OUTLOOK_TRUSTED', 'price': 0.01, 'lifetime': '3-6 months'}
    ],
    "lution": [
        {'display': 'Hotmail', 'api_param': 'hotmail', 'price': 0.0015, 'lifetime': '1-5h'},
        {'display': 'Outlook', 'api_param': 'outlook', 'price': 0.0015, 'lifetime': '1-5h'},
        {'display': 'Hotmail Trusted (IMAP+Graph)', 'api_param': 'hotmail.trusted', 'price': 0.015, 'lifetime': '3-6 months'},
        {'display': 'Outlook Trusted (IMAP+Graph)', 'api_param': 'outlook.trusted', 'price': 0.015, 'lifetime': '3-6 months'},
        {'display': 'Hotmail Trusted (Graph)', 'api_param': 'hotmail.trusted.graph', 'price': 0.015, 'lifetime': '3-6 months'},
        {'display': 'Outlook Trusted (Graph)', 'api_param': 'outlook.trusted.graph', 'price': 0.015, 'lifetime': '3-6 months'},
        {'display': 'Hotmail Priority $5', 'api_param': 'hotmail5', 'price': 0.005, 'lifetime': '1-5h'},
        {'display': 'Hotmail Priority $4', 'api_param': 'hotmail4', 'price': 0.004, 'lifetime': '1-5h'},
        {'display': 'Hotmail Priority $3', 'api_param': 'hotmail3', 'price': 0.003, 'lifetime': '1-5h'},
        {'display': 'Hotmail Priority $2', 'api_param': 'hotmail2', 'price': 0.002, 'lifetime': '1-5h'},
        {'display': 'Outlook Priority $5', 'api_param': 'outlook5', 'price': 0.005, 'lifetime': '1-5h'},
        {'display': 'Outlook Priority $4', 'api_param': 'outlook4', 'price': 0.004, 'lifetime': '1-5h'},
        {'display': 'Outlook Priority $3', 'api_param': 'outlook3', 'price': 0.003, 'lifetime': '1-5h'},
        {'display': 'Outlook Priority $2', 'api_param': 'outlook2', 'price': 0.002, 'lifetime': '1-5h'}
    ],
    "007hotmail": [
        {'display': 'Hotmail', 'api_param': 'hotmail', 'price': 0.002, 'lifetime': '1-3h'},
        {'display': 'Outlook', 'api_param': 'outlook', 'price': 0.002, 'lifetime': '1-3h'},
        {'display': 'Hotmail Premium', 'api_param': 'hotmail-premium', 'price': 0.003, 'lifetime': '1-3h'},
        {'display': 'Outlook Premium', 'api_param': 'outlook-premium', 'price': 0.003, 'lifetime': '1-3h'},
        {'display': 'Hotmail Trusted', 'api_param': 'hotmail Trusted', 'price': 0.02, 'lifetime': '3-6 months'},
        {'display': 'Outlook Trusted', 'api_param': 'outlook Trusted', 'price': 0.02, 'lifetime': '3-6 months'},
        {'display': 'Hotmail Trusted (Graph)', 'api_param': 'hotmail Trusted Graph', 'price': 0.02, 'lifetime': '3-6 months'},
        {'display': 'Outlook Trusted (Graph)', 'api_param': 'outlook Trusted Graph', 'price': 0.02, 'lifetime': '3-6 months'}
    ]
}

def get_catalog(service_name: str) -> list:
    return EMAIL_CATALOGS.get(service_name.lower(), [])

def get_default_category(service_name: str) -> str:
    cat = get_catalog(service_name)
    return cat[0]['api_param'] if cat else ""

def get_email_provider(service_name: str, api_key: str, email_category: str) -> Optional[EmailProvider]:
    name = service_name.lower()
    if name == "zeus":
        return ZeusProvider(api_key, email_category)
    elif name == "007hotmail":
        return Hotmail007Provider(api_key, email_category)
    elif name == "lution":
        return LutionProvider(api_key, email_category)
    return None

def fetch_stock(service_name: str, api_key: str) -> dict:
    """Fetch live stock counts (stub for now, can be implemented per provider)."""
    return {}

