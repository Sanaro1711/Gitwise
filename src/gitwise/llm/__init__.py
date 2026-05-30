"""LLM integration for gw ask and gw explain-state."""

from __future__ import annotations

from gitwise.llm.config import load_api_key, require_api_key
from gitwise.llm.context import build_repo_context
from gitwise.llm.gemini import GeminiError, generate
from gitwise.llm.response import AskResponse, parse_ask_response
from gitwise.llm.validator import ValidationResult, validate_llm_plan

__all__ = [
    "AskResponse",
    "GeminiError",
    "ValidationResult",
    "build_repo_context",
    "generate",
    "load_api_key",
    "parse_ask_response",
    "require_api_key",
    "validate_llm_plan",
]
