import re
import random
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

class ProxyType(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

@dataclass
class ProxyEntry:
    """Represents a parsed proxy."""
    host: str
    port: int
    proxy_type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None

    def to_url(self) -> str:
        """Convert to a URL string for requests/httpx."""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"

    def to_dict(self) -> dict:
        """Convert to a dict suitable for proxy parameters."""
        url = self.to_url()
        return {
            "http": url,
            "https": url
        }

# Regex for parsing: [type://][user:pass@]host:port
PROXY_LINE_PATTERN = re.compile(
    r'^(?:(?P<type>https?|socks[45])://)?(?:(?P<user>[^:@]+):(?P<pass>[^@]+)@)?(?P<host>[^:@\s]+):(?P<port>\d+)$',
    re.IGNORECASE
)

# Regex for alternate format: host:port:user:pass
PROXY_ALT_PATTERN = re.compile(
    r'^(?P<host>[^:\s]+):(?P<port>\d+):(?P<user>[^:]+):(?P<pass>.+)$'
)

def parse_proxy_line(line: str, default_type: ProxyType = ProxyType.HTTP) -> Optional[ProxyEntry]:
    """Parse a single proxy line."""
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    match = PROXY_LINE_PATTERN.match(line)
    if match:
        p_type_str = match.group('type')
        p_type = ProxyType(p_type_str.lower()) if p_type_str else default_type
        return ProxyEntry(
            host=match.group('host'),
            port=int(match.group('port')),
            proxy_type=p_type,
            username=match.group('user'),
            password=match.group('pass')
        )

    match = PROXY_ALT_PATTERN.match(line)
    if match:
        return ProxyEntry(
            host=match.group('host'),
            port=int(match.group('port')),
            proxy_type=default_type,
            username=match.group('user'),
            password=match.group('pass')
        )
        
    return None

def parse_proxies(text: str, default_type: ProxyType = ProxyType.HTTP) -> List[ProxyEntry]:
    """Parse multiple lines of proxies."""
    proxies = []
    for line in text.splitlines():
        proxy = parse_proxy_line(line, default_type)
        if proxy:
            proxies.append(proxy)
    return proxies

def parse_proxy_file(filepath: str, default_type: ProxyType = ProxyType.HTTP) -> List[ProxyEntry]:
    """Parse a proxy file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return parse_proxies(f.read(), default_type)
    except Exception:
        return []

class ProxyRotator:
    """Thread-safe round-robin proxy rotation with optional random mode."""

    def __init__(self, proxies: Optional[List[ProxyEntry]] = None):
        self._proxies = proxies or []
        self._index = 0
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        return len(self._proxies)

    def is_empty(self) -> bool:
        return not self._proxies

    def set_proxies(self, proxies: List[ProxyEntry]):
        """Update the proxy list."""
        with self._lock:
            self._proxies = proxies
            self._index = 0

    def next(self) -> Optional[ProxyEntry]:
        """Get the next proxy in round-robin order (thread-safe)."""
        with self._lock:
            if not self._proxies:
                return None
            proxy = self._proxies[self._index]
            self._index = (self._index + 1) % len(self._proxies)
            return proxy

    def random(self) -> Optional[ProxyEntry]:
        """Get a random proxy."""
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    def get_proxy_dict(self) -> Optional[dict]:
        """Get the next proxy as a dict for requests, or None if no proxies."""
        proxy = self.next()
        return proxy.to_dict() if proxy else None

