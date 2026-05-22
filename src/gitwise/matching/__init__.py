"""Intent matching (rapidfuzz) — used by gw do in a later milestone."""

from gitwise.matching.intent_parser import parse_intent
from gitwise.matching.push_resolver import needs_upstream_flag, resolve_push

__all__ = ["parse_intent", "needs_upstream_flag", "resolve_push"]
