"""
Parse natural-language intent for gw do (future).

Matching strategy (accuracy-first):
1. rapidfuzz scores intent against recipe phrase lists → recipe family (e.g. push).
2. RepoState decides flags like -u (has_upstream vs no_upstream).
3. Regex/keywords extract targets: branch names, remotes, paths, messages.

Example: "push this to main"
  - Fuzzy match → push (not an exact phrase required).
  - Target branch extracted: main
  - If current branch is feature-x and user wants main on origin:
      git push origin main (set upstream on that branch if needed)
  - If current branch IS main and upstream exists:
      git push origin main
  - If no upstream on current branch:
      git push -u origin <current-branch>
"""

from __future__ import annotations

import re

from gitwise.models import ParsedIntent

_BRANCH_TARGET = re.compile(
    r"\b(?:to|onto|on)\s+([a-zA-Z0-9._/-]+)\b|"
    r"\b(?:branch\s+)([a-zA-Z0-9._/-]+)\b",
    re.IGNORECASE,
)
_REMOTE = re.compile(r"\b(?:origin|upstream)\b", re.IGNORECASE)
_QUOTED = re.compile(r'"([^"]+)"|\'([^\']+)\'')


def parse_intent(text: str) -> ParsedIntent:
    """Extract structured hints from user intent text."""
    raw = text.strip()
    lowered = raw.lower()
    keywords: list[str] = []

    for token in (
        "push",
        "pull",
        "stash",
        "commit",
        "merge",
        "rebase",
        "branch",
        "main",
        "master",
        "force",
        "upstream",
        "uncommit",
        "undo",
    ):
        if token in lowered:
            keywords.append(token)

    branch = None
    match = _BRANCH_TARGET.search(raw)
    if match:
        branch = match.group(1) or match.group(2)

    remote = "origin" if _REMOTE.search(raw) else None
    wants_upstream = any(
        p in lowered
        for p in ("-u", "upstream", "set upstream", "first push", "track")
    )

    message = None
    q = _QUOTED.search(raw)
    if q:
        message = q.group(1) or q.group(2)

    name = branch  # alias for branch/tag names until tag parsing is added

    return ParsedIntent(
        raw=raw,
        name=name,
        branch=branch,
        remote=remote,
        message=message,
        wants_upstream=wants_upstream,
        keywords=keywords,
    )
