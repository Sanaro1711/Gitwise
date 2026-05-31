"""Redact secrets before data leaves the machine or appears in errors."""

from __future__ import annotations

import re

# Google API keys typically start with AIza
_API_KEY_PATTERN = re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b")

# user:password@ in URLs
_URL_CREDENTIALS = re.compile(r"https?://[^/\s:@]+:[^/\s@]+@", re.I)

# Bearer / token-like assignments in text
_TOKEN_ASSIGNMENT = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|credential)\s*[=:]\s*\S+"
)

# PEM private keys
_PEM_BLOCK = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)


def redact_secrets(text: str) -> str:
    """Remove common secret patterns from text."""
    if not text:
        return text
    out = _PEM_BLOCK.sub("[REDACTED PRIVATE KEY]", text)
    out = _API_KEY_PATTERN.sub("[REDACTED API KEY]", out)
    out = _URL_CREDENTIALS.sub("https://", out)
    out = _TOKEN_ASSIGNMENT.sub(r"\1=[REDACTED]", out)
    return out


def redact_remote_url(url: str) -> str:
    """Strip embedded credentials from a remote URL."""
    if not url or url == "(none)":
        return url or "(none)"
    return _URL_CREDENTIALS.sub("https://", url)


def sanitize_http_error_detail(detail: str) -> str:
    """Sanitize API error bodies before showing the user."""
    return redact_secrets(detail[:500])
