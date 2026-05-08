import time
import requests
import re
from typing import Optional, Any

_URLS = {
    'onyx': 'https://onyxsolver.io',
    'hcaptchasolver': 'https://hcaptchasolver.com/api',
    'voidsolver': 'https://api.voidsolver.tech',
    'anysolver': 'https://api.anysolver.com',
    'nopecha': 'https://api.nopecha.com',
    'yescaptcha': 'https://api.yescaptcha.com'
}

def _safe_json(resp, provider_name: str):
    try:
        return resp.json()
    except:
        return {"error": True, "message": f"[{provider_name}] Invalid JSON response (HTTP {resp.status_code})"}

def _strip_scheme(proxy: str) -> str:
    if not proxy: return ""
    p = proxy.replace("http://", "").replace("https://", "")
    return p

def _add_proxy_fields(task: dict, proxy: str):
    """Parse proxy string into structured fields for YesCaptcha/AntiCaptcha format."""
    if not proxy:
        task["proxyType"] = "http" # dummy or just skip
        return
    
    # format: user:pass@host:port or host:port
    p_clean = _strip_scheme(proxy)
    task["proxyType"] = "http"
    
    if "@" in p_clean:
        auth, addr = p_clean.rsplit("@", 1)
        user, pwd = auth.split(":", 1) if ":" in auth else (auth, "")
        host, port = addr.split(":", 1) if ":" in addr else (addr, "80")
        task["proxyAddress"] = host
        task["proxyPort"] = int(port)
        task["proxyLogin"] = user
        task["proxyPassword"] = pwd
    else:
        host, port = p_clean.split(":", 1) if ":" in p_clean else (p_clean, "80")
        task["proxyAddress"] = host
        task["proxyPort"] = int(port)

def _extract_token(data: Any) -> Optional[str]:
    if isinstance(data, str):
        return data
    if not data:
        return None
    
    # Try common fields
    for field in ["solution", "token", "gRecaptchaResponse", "answer", "solvedToken"]:
        if isinstance(data, dict) and field in data:
            val = data[field]
            if isinstance(val, dict) and "token" in val:
                return val["token"]
            return val
    return None

def solve_hcaptcha(solver_name: str, api_key: str, sitekey: str, site_url: str = "https://discord.com", 
                    rqdata: str = "", proxy: str = "", user_agent: str = "", 
                    timeout: int = 120, max_attempts: int = 3, log_func=None) -> Optional[str]:
    
    def _log(msg, level="INFO"):
        if log_func:
            log_func(msg, level)

    name = solver_name.lower().strip()
    if name not in _URLS:
        _log(f"Unknown captcha solver: {solver_name}", "ERROR")
        return None

    for attempt in range(1, max_attempts + 1):
        try:
            token = None
            if name == "onyx":
                token = _solve_onyx(api_key, sitekey, site_url, rqdata, proxy, user_agent, timeout, _log)
            elif name == "hcaptchasolver":
                token = _solve_hcaptchasolver(api_key, sitekey, site_url, rqdata, proxy, user_agent, timeout, _log)
            elif name == "voidsolver":
                token = _solve_voidsolver(api_key, sitekey, site_url, rqdata, proxy, user_agent, timeout, _log)
            elif name == "anysolver":
                token = _solve_anysolver(api_key, sitekey, site_url, rqdata, proxy, user_agent, timeout, _log)
            elif name == "nopecha":
                token = _solve_nopecha(api_key, sitekey, site_url, rqdata, proxy, user_agent, timeout, _log)
            elif name == "yescaptcha":
                token = _solve_yescaptcha(api_key, sitekey, site_url, rqdata, proxy, user_agent, timeout, _log)

            if token:
                _log(f"[{name}] Captcha solved successfully", "SUCCESS")
                return token
            
            _log(f"[{name}] Solver returned empty result (attempt {attempt}/{max_attempts})", "WARNING")
            
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                _log(f"[{name}] Rate limited, retrying in 3s (attempt {attempt})...", "WARNING")
                time.sleep(3)
            else:
                _log(f"[{name}] Captcha error (attempt {attempt}): {err_str}", "ERROR")
        
        time.sleep(1)

    _log(f"[{name}] All {max_attempts} captcha attempts failed", "ERROR")
    return None

def _solve_onyx(api_key, sitekey, site_url, rqdata, proxy, ua, timeout, _log):
    base_url = _URLS['onyx']
    task = {
        "clientKey": api_key,
        "task": {
            "type": "HCaptchaTask" if proxy else "HCaptchaTaskProxyless",
            "websiteURL": site_url,
            "websiteKey": sitekey,
            "userAgent": ua,
            "rqdata": rqdata
        }
    }
    if proxy: _add_proxy_fields(task["task"], proxy)

    r = requests.post(f"{base_url}/api/createTask", json=task, timeout=30)
    data = _safe_json(r, "onyx")
    if data.get("errorId") != 0:
        _log(f"[onyx] API error: {data.get('errorDescription') or data.get('errorCode')}", "ERROR")
        return None
    
    task_id = data.get("taskId")
    if not task_id: return None

    start = time.time()
    poll_count = 0
    while time.time() - start < timeout:
        poll_count += 1
        r = requests.post(f"{base_url}/api/getTaskResult", json={"clientKey": api_key, "taskId": task_id}, timeout=10)
        data = _safe_json(r, "onyx")
        status = data.get("status")
        if status in ["ready", "completed", "solved"]:
            token = _extract_token(data.get("solution"))
            if token: return token
            _log(f"[onyx] Status '{status}' but no token: {data}", "WARNING")
        elif status in ["failed", "error"]:
            _log(f"[onyx] Task failed: {data.get('errorDescription')}", "ERROR")
            return None
        time.sleep(3)
    
    _log(f"[onyx] Timeout after {timeout}s ({poll_count} polls)", "WARNING")
    return None

def _solve_hcaptchasolver(api_key, sitekey, site_url, rqdata, proxy, ua, timeout, _log):
    base_url = _URLS['hcaptchasolver']
    payload = {
        "api_key": api_key,
        "sitekey": sitekey,
        "site_url": site_url,
        "rqdata": rqdata,
        "proxy": proxy,
        "user_agent": ua
    }
    r = requests.post(f"{base_url}/createTask", json=payload, timeout=30)
    data = _safe_json(r, "hcaptchasolver")
    if not data.get("success"):
        _log(f"[hcaptchasolver] API error: {data.get('message')}", "ERROR")
        return None
    
    task_id = data.get("task_id")
    if not task_id: return None

    start = time.time()
    while time.time() - start < timeout:
        r = requests.post(f"{base_url}/getTaskResult", json={"api_key": api_key, "task_id": task_id}, timeout=10)
        data = _safe_json(r, "hcaptchasolver")
        if data.get("status") in ["completed", "solved"]:
            return data.get("token")
        elif data.get("status") == "failed":
            return None
        time.sleep(3)
    return None

def _solve_voidsolver(api_key, sitekey, site_url, rqdata, proxy, ua, timeout, _log):
    base_url = _URLS['voidsolver']
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "site_key": sitekey,
        "site_url": site_url,
        "rqdata": rqdata,
        "proxy": proxy,
        "user_agent": ua,
        "pow_type": "hsw"
    }
    r = requests.post(f"{base_url}/createtask", json=payload, headers=headers, timeout=30)
    data = _safe_json(r, "voidsolver")
    task_id = data.get("task_id") or data.get("id")
    if not task_id:
        _log(f"[voidsolver] No taskId: {data}", "ERROR")
        return None

    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{base_url}/gettaskresult", params={"taskid": task_id}, headers=headers, timeout=10)
        data = _safe_json(r, "voidsolver")
        if data.get("success") and data.get("status") in ["completed", "ready"]:
            return data.get("solvedToken") or data.get("token")
        elif data.get("status") == "failed":
            return None
        time.sleep(3)
    return None

def _solve_anysolver(api_key, sitekey, site_url, rqdata, proxy, ua, timeout, _log):
    base_url = _URLS['anysolver']
    task = {
        "clientKey": api_key,
        "task": {
            "type": "HCaptchaTask" if proxy else "HCaptchaTaskProxyless",
            "websiteURL": site_url,
            "websiteKey": sitekey,
            "userAgent": ua,
            "rqdata": rqdata
        }
    }
    if proxy: _add_proxy_fields(task["task"], proxy)

    r = requests.post(f"{base_url}/createTask", json=task, timeout=30)
    data = _safe_json(r, "anysolver")
    task_id = data.get("taskId")
    if not task_id:
        _log(f"[anysolver] No taskId: {data}", "ERROR")
        return None

    start = time.time()
    while time.time() - start < timeout:
        r = requests.post(f"{base_url}/getTaskResult", json={"clientKey": api_key, "taskId": task_id}, timeout=10)
        data = _safe_json(r, "anysolver")
        if data.get("status") == "ready":
            return _extract_token(data.get("solution"))
        elif data.get("status") == "failed":
            return None
        time.sleep(3)
    return None

def _solve_nopecha(api_key, sitekey, site_url, rqdata, proxy, ua, timeout, _log):
    base_url = _URLS['nopecha']
    payload = {
        "key": api_key,
        "type": "hcaptcha",
        "sitekey": sitekey,
        "url": site_url,
        "rqdata": rqdata,
        "useragent": ua
    }
    r = requests.post(f"{base_url}/token/", json=payload, timeout=30)
    data = _safe_json(r, "nopecha")
    if "error" in data:
        _log(f"[nopecha] Error {data.get('error')}: {data.get('message')}", "ERROR")
        return None
    
    poll_id = data.get("data") or data.get("id")
    if not poll_id: return None

    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{base_url}/token/", params={"key": api_key, "id": poll_id}, timeout=10)
        data = _safe_json(r, "nopecha")
        if "data" in data and data["data"] != "Incomplete job":
            return data["data"]
        elif "error" in data:
            return None
        time.sleep(3)
    return None

def _solve_yescaptcha(api_key, sitekey, site_url, rqdata, proxy, ua, timeout, _log):
    base_url = _URLS['yescaptcha']
    task = {
        "clientKey": api_key,
        "task": {
            "type": "HCaptchaTask" if proxy else "HCaptchaTaskProxyless",
            "websiteURL": site_url,
            "websiteKey": sitekey,
            "userAgent": ua,
            "rqdata": rqdata
        }
    }
    if proxy: _add_proxy_fields(task["task"], proxy)

    r = requests.post(f"{base_url}/createTask", json=task, timeout=30)
    data = _safe_json(r, "yescaptcha")
    task_id = data.get("taskId")
    if not task_id: return None

    start = time.time()
    while time.time() - start < timeout:
        r = requests.post(f"{base_url}/getTaskResult", json={"clientKey": api_key, "taskId": task_id}, timeout=10)
        data = _safe_json(r, "yescaptcha")
        if data.get("status") == "ready":
            return _extract_token(data.get("solution"))
        elif data.get("status") == "error":
            return None
        time.sleep(3)
    return None


