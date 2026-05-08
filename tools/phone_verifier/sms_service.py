import time
import requests
import re
from typing import Optional, Any, List, Tuple

_DEFAULT_URLS = {
    '5sim': 'https://5sim.net/v1',
    'smsbower': 'https://smsbower.app/stubs/handler_api.php',
    'herosms': 'https://hero-sms.com/stubs/handler_api.php',
    'tigersms': 'https://api.tiger-sms.com/stubs/handler_api.php'
}

_SMSACTIVATE_ERRORS = {
    'BAD_KEY': 'Invalid API key',
    'BAD_ACTION': 'Incorrect API action',
    'BAD_SERVICE': 'Incorrect service name',
    'BAD_COUNTRY': 'Incorrect country code',
    'NO_NUMBERS': 'No numbers available for this country/service',
    'NO_BALANCE': 'Insufficient balance on SMS account',
    'NO_ACTIVATION': 'Incorrect activation ID',
    'BAD_STATUS': 'Incorrect activation status',
    'EARLY_CANCEL_DENIED': 'Too early to cancel — wait 2 min after purchase',
    'BANNED:': 'Account banned',
    'ERROR': 'Server error'
}

_5SIM_ERRORS = {
    'no free phones': 'No available numbers for this country/operator',
    'not enough user balance': 'Insufficient 5sim balance',
    'not enough rating': '5sim account rating too low',
    'bad country': 'Invalid country name',
    'bad operator': 'Invalid operator name',
    'no product': 'Product (discord) not available',
    'server offline': '5sim server offline — try again later'
}

def _make_log(log_func):
    def _log(msg, level="INFO"):
        if log_func:
            log_func(msg, level)
    return _log

def fetch_countries(service: str, api_key: str) -> List[dict]:
    name = service.lower().strip()
    base = _DEFAULT_URLS.get(name)
    if not base: return []

    try:
        if name == '5sim':
            # 5sim needs cross-ref with prices for stock
            r = requests.get(f"{base}/guest/countries", timeout=15)
            c_data = r.json()
            r2 = requests.get(f"{base}/guest/prices?product=discord", timeout=25)
            p_data = r2.json()
            
            result = []
            for cid, info in c_data.items():
                cname = info.get('text_en', cid)
                # find stock in p_data
                stock_info = p_data.get(cid, {}).get('discord', {})
                total = sum(op.get('count', 0) for op in stock_info.values())
                min_p = min((op.get('cost', 999) for op in stock_info.values()), default=0)
                
                if total > 0:
                    result.append({
                        "id": cid,
                        "name": cname,
                        "count": total,
                        "price": min_p
                    })
            return sorted(result, key=lambda x: x['name'])

        else:
            # sms-activate compatible
            r = requests.get(f"{base}?api_key={api_key}&action=getCountries", timeout=15)
            # Some providers return JSON, some return flat text or weird HTML
            try:
                data = r.json()
                result = []
                # Map to standard format
                if isinstance(data, dict):
                    for cid, info in data.items():
                        result.append({"id": cid, "name": info.get('eng', cid), "count": info.get('count', 0), "price": 0})
                return sorted(result, key=lambda x: x['name'])
            except:
                return []

    except Exception:
        return []

def fetch_operators(service: str, api_key: str, country_id: str) -> List[dict]:
    name = service.lower().strip()
    base = _DEFAULT_URLS.get(name)
    if not base: return []

    try:
        if name == '5sim':
            r = requests.get(f"{base}/guest/prices?product=discord&country={country_id}", timeout=15)
            data = r.json().get(country_id, {}).get('discord', {})
            result = []
            for op_name, op_info in data.items():
                result.append({
                    "id": op_name,
                    "name": op_name.title(),
                    "count": op_info.get('count', 0),
                    "price": op_info.get('cost', 0),
                    "extra": f"Rate: {op_info.get('rate', 0)}%"
                })
            return sorted(result, key=lambda x: x['price'])
        else:
            # Aggregate from getPrices
            r = requests.get(f"{base}?api_key={api_key}&action=getPrices&country={country_id}&service=ds", timeout=15)
            data = r.json().get(country_id, {}).get('ds', {})
            result = []
            for op_id, op_info in data.items():
                result.append({
                    "id": op_id,
                    "name": f"Provider {op_id}",
                    "count": op_info.get('count', 0),
                    "price": op_info.get('cost', 0),
                    "currency": "₽"
                })
            return sorted(result, key=lambda x: x['price'])
    except:
        return []

def purchase_phone(service: str, api_key: str, country: str, operator: str, 
                   proxy: str = "", max_attempts: int = 3, log_func=None) -> Tuple[Optional[str], Optional[str]]:
    _log = _make_log(log_func)
    name = service.lower().strip()
    base = _DEFAULT_URLS.get(name)
    if not base: return None, None

    for attempt in range(1, max_attempts + 1):
        try:
            if name == '5sim':
                headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
                url = f"{base}/user/buy/activation/{country}/{operator}/discord"
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    _log(f"[5sim] Purchased: {data['phone']}", "INFO")
                    return str(data['id']), str(data['phone'])
                elif r.status_code == 400:
                    err = r.text.lower()
                    friendly = _5SIM_ERRORS.get(err, f"Error: {err}")
                    _log(f"[5sim] Purchase error: {friendly}", "ERROR")
                    return None, None
            else:
                params = {
                    "api_key": api_key,
                    "action": "getNumber",
                    "service": "ds",
                    "country": country
                }
                if operator and operator != "0": params["providerIds"] = operator
                r = requests.get(base, params=params, timeout=20)
                text = r.text
                if text.startswith("ACCESS_NUMBER"):
                    parts = text.split(":")
                    _log(f"[{name}] Purchased: {parts[2]}", "INFO")
                    return parts[1], parts[2]
                else:
                    friendly = _SMSACTIVATE_ERRORS.get(text, f"Error: {text}")
                    _log(f"[{name}] Purchase error: {friendly}", "ERROR")
                    return None, None

        except Exception as e:
            _log(f"[{name}] Request timeout (attempt {attempt})", "WARNING")
        
        time.sleep(2)
    
    _log(f"[{name}] Failed to purchase after {max_attempts} attempts", "ERROR")
    return None, None

def fetch_otp(service: str, api_key: str, order_id: str, 
              proxy: str = "", timeout: int = 180, log_func=None) -> Optional[str]:
    _log = _make_log(log_func)
    name = service.lower().strip()
    base = _DEFAULT_URLS.get(name)
    
    start = time.time()
    poll_count = 0
    while time.time() - start < timeout:
        poll_count += 1
        try:
            if name == '5sim':
                headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
                r = requests.get(f"{base}/user/check/{order_id}", headers=headers, timeout=10)
                data = r.json()
                if data.get("status") == "RECEIVED" and data.get("sms"):
                    sms_text = data["sms"][0].get("text", "")
                    m = re.search(r'\b\d{4,8}\b', sms_text)
                    code = m.group(0) if m else None
                    if code:
                        _log(f"[5sim] OTP received: {code} (poll #{poll_count})", "SUCCESS")
                        return code
                elif data.get("status") in ["CANCELED", "BANNED", "TIMEOUT"]:
                    return None
            else:
                r = requests.get(base, params={"api_key": api_key, "action": "getStatus", "id": order_id}, timeout=10)
                text = r.text
                if text.startswith("STATUS_OK") or text.startswith("STATUS_WAIT_RETRY"):
                    parts = text.split(":")
                    if len(parts) > 1:
                        _log(f"[{name}] OTP received: {parts[1]}", "SUCCESS")
                        return parts[1]
                elif "STATUS_CANCEL" in text or "ACCESS_CANCEL" in text:
                    return None
        except:
            pass
        time.sleep(5)
    
    _log(f"[{name}] OTP timeout", "ERROR")
    return None

def manage_order(service: str, api_key: str, order_id: str, action: str, 
                 proxy: str = "", log_func=None):
    _log = _make_log(log_func)
    name = service.lower().strip()
    base = _DEFAULT_URLS.get(name)
    
    try:
        if name == '5sim':
            # actions: finish, cancel, ban
            headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
            requests.get(f"{base}/user/{action}/{order_id}", headers=headers, timeout=10)
            _log(f"[5sim] Order {action}ed", "INFO")
        else:
            # 1 = ready, 3 = retry, 6 = success, 8 = cancel/ban
            status_map = {"finish": "6", "cancel": "8", "ban": "8", "ready": "1", "retry": "3"}
            status_val = status_map.get(action.lower(), "8")
            requests.get(base, params={"api_key": api_key, "action": "setStatus", "id": order_id, "status": status_val}, timeout=10)
            _log(f"[{name}] Order {action}ed", "INFO")
    except:
        pass


