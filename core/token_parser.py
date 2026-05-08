import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

@dataclass
class TokenEntry:
    """Represents a parsed token with optional email and password."""
    token: str
    email: Optional[str] = None
    password: Optional[str] = None
    raw_line: str = ""

    def format_output(self, include_all: bool = True) -> str:
        """Format the token entry for file output."""
        if not include_all:
            return self.token
        
        parts = []
        if self.email: parts.append(self.email)
        if self.password: parts.append(self.password)
        parts.append(self.token)
        return ":".join(parts)

# Discord token regex patterns
TOKEN_PATTERNS = [
    re.compile(r'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,}'), # Standard
    re.compile(r'mfa\.[A-Za-z0-9_-]{84,}'),                                 # MFA
    re.compile(r'[A-Za-z0-9_-]{58,}')                                       # Alternate/Old
]

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def _looks_like_token(value: str) -> bool:
    """Check if a string looks like a Discord token."""
    value = value.strip()
    for pattern in TOKEN_PATTERNS:
        if pattern.fullmatch(value):
            return True
    return False

def _looks_like_email(value: str) -> bool:
    """Check if a string looks like an email address."""
    return bool(EMAIL_PATTERN.match(value.strip()))

def _entry_priority(entry: TokenEntry) -> int:
    """Score how rich a token entry's format is. Higher = more complete."""
    score = 1 # Bare token
    if entry.email: score += 1
    if entry.password: score += 1
    return score

def parse_token_line(line: str) -> Optional[TokenEntry]:
    """
    Parse a single line into a TokenEntry.
    
    Supported formats (any order):
      email:pass:token
      email:token
      pass:token
      token:pass
      token
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
        
    # Standard split by colon
    parts = line.replace(' :', ':').split(':')
    
    token = None
    email = None
    password = None
    
    # 1. Identify token
    for p in parts:
        if _looks_like_token(p):
            token = p
            break
            
    if not token:
        # Try finding a token using search if it's buried
        for pattern in TOKEN_PATTERNS:
            match = pattern.search(line)
            if match:
                token = match.group(0)
                break
    
    if not token:
        return None
        
    # 2. Identify email and password from remaining parts
    remaining = [p for p in parts if p != token]
    
    for p in remaining:
        if _looks_like_email(p):
            email = p
        else:
            # Assume any other part is a password
            password = p
            
    return TokenEntry(token=token, email=email, password=password, raw_line=line)

def parse_tokens(text: str) -> Tuple[List[TokenEntry], int]:
    """
    Parse multiple lines of text into a list of TokenEntry objects.
    Deduplicates based on token value, keeping the "richest" entry.
    """
    best_entry = {} # token -> TokenEntry
    insertion_order = []
    skipped_duplicates = 0
    
    for line in text.splitlines():
        entry = parse_token_line(line)
        if not entry:
            continue
            
        if entry.token in best_entry:
            skipped_duplicates += 1
            # Keep the one with more info
            if _entry_priority(entry) > _entry_priority(best_entry[entry.token]):
                best_entry[entry.token] = entry
        else:
            best_entry[entry.token] = entry
            insertion_order.append(entry.token)
            
    return [best_entry[t] for t in insertion_order], skipped_duplicates

def parse_token_file(filepath: str) -> Tuple[List[TokenEntry], int]:
    """Parse a token file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return parse_tokens(f.read())
    except Exception:
        return [], 0

