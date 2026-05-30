"""Minimal Gemini REST client (stdlib only, free-tier model)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from gitwise.llm.prompts import DEFAULT_MODEL, SYSTEM_PROMPT

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
    repo_context: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 60.0,
) -> GeminiResponse:
    """Call Gemini generateContent with JSON response mode."""
    url = f"{_API_BASE}/{model}:generateContent?key={api_key}"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"Repository context:\n\n{repo_context}\n\n"
                            f"User question:\n{user_message}"
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
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
    snippet = detail[:300].replace("\n", " ")
    return f"Gemini API error ({code}): {snippet}"
