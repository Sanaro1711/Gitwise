"""Minimal Gemini REST client (stdlib only, free-tier model)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from gitwise.llm.prompts import DEFAULT_MODEL, SYSTEM_PROMPT
from gitwise.llm.sanitize import redact_secrets, sanitize_http_error_detail

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass
class GeminiResponse:
    text: str
    model: str


class GeminiError(Exception):
    """Gemini API call failed."""


def generate(
    *,
    api_key: str,
    user_message: str,
    repo_context: str = "",
    system_prompt: str | None = None,
    model: str = DEFAULT_MODEL,
    timeout: float = 60.0,
    max_output_tokens: int = 1024,
) -> GeminiResponse:
    """Call Gemini generateContent with JSON response mode."""
    system = system_prompt or SYSTEM_PROMPT
    user_text = user_message
    if repo_context:
        user_text = f"Repository context:\n\n{repo_context}\n\n{user_message}"

    url = f"{_API_BASE}/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
            "maxOutputTokens": max_output_tokens,
        },
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = sanitize_http_error_detail(exc.read().decode("utf-8", errors="replace"))
        raise GeminiError(_format_http_error(exc.code, detail)) from exc
    except urllib.error.URLError as exc:
        raise GeminiError(f"Network error calling Gemini: {exc.reason}") from exc
    except TimeoutError as exc:
        raise GeminiError("Gemini request timed out.") from exc

    text = _extract_text(payload)
    if not text:
        raise GeminiError("Gemini returned an empty response.")
    return GeminiResponse(text=text, model=model)


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()


def _format_http_error(code: int, detail: str) -> str:
    if code == 400 and "API key not valid" in detail:
        return "Invalid Gemini API key. Check GEMINI_API_KEY or ~/.gitwise/gemini_api_key."
    if code == 429:
        return "Gemini rate limit reached (free tier). Wait a minute and try again."
    if code == 403:
        return "Gemini API access denied. Verify your API key at https://aistudio.google.com/apikey"
    snippet = sanitize_http_error_detail(detail).replace("\n", " ")
    return f"Gemini API error ({code}): {snippet[:200]}"
