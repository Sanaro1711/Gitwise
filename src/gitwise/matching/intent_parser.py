"""
Parse natural-language intent for gw do.

Extracts branch names, paths, URLs, messages, and primary action hints so
rapidfuzz can match recipe families while repo state fills in git flags (-u, etc.).
"""

from __future__ import annotations

import re

from gitwise.models import ParsedIntent

# Order matters: longer / more specific actions first
_ACTION_PATTERNS: list[tuple[str, list[str]]] = [
    ("force_push", ["force push", "force-with-lease", "force with lease", "safe force push"]),
    ("abort", ["abort merge", "abort rebase", "cancel merge", "cancel rebase", "stop merge", "stop rebase"]),
    ("fetch", ["fetch and prune", "fetch prune", "git fetch", "fetch"]),
    ("pull", ["pull latest", "pull changes", "git pull", "pull"]),
    ("push", ["push to", "push this", "upload", "publish", "git push", "push"]),
    ("stash_untracked", ["stash untracked", "stash including untracked", "stash all", "stash everything"]),
    ("stash", ["git stash", "stash pop", "stash apply", "unstash", "stash"]),
    ("undo_commit", ["uncommit", "undo commit", "undo last commit", "soft reset", "remove last commit"]),
    ("commit", ["git commit", "commit changes", "commit with", "commit"]),
    ("unstage", ["unstage", "undo staged", "remove from staging"]),
    ("discard_all", ["discard all", "throw away all", "wipe local", "clean all"]),
    ("discard_file", ["discard file", "discard changes", "revert file", "restore file", "undo file"]),
    ("merge", ["merge into", "merge to", "merge branch"]),
    ("rebase", ["rebase onto", "rebase on", "rebase"]),
    ("clone", ["clone repo", "git clone", "clone"]),
    ("branch_create", ["create branch", "new branch", "make branch", "branch off"]),
    ("branch_switch", ["switch branch", "switch to", "checkout branch", "go to branch", "change branch"]),
    ("branch_delete", ["delete branch", "remove branch"]),
    ("remote", ["set remote", "add origin", "remote url", "change origin"]),
    ("stage", ["stage all", "add all", "git add"]),
    ("log", ["git log", "commit history", "show history", "git history"]),
    ("status", ["git status", "show status"]),
    ("diff", ["git diff", "show diff", "staged diff"]),
    ("tag", ["create tag", "git tag", "new tag"]),
    ("pr", ["pull request", "open pr", "create pr"]),
]

_BRANCH_PATTERNS = [
    re.compile(r'\b(?:to|onto|on)\s+["\']?([a-zA-Z0-9._/-]+)["\']?\b', re.I),
    re.compile(r'\bpush\s+["\']?([a-zA-Z0-9._/-]+)["\']?\b', re.I),
    re.compile(r'\b(?:branch|called|named)\s+["\']?([a-zA-Z0-9._/-]+)["\']?\b', re.I),
    re.compile(r'\b(?:switch|checkout|merge|delete|rename)\s+(?:to\s+)?["\']?([a-zA-Z0-9._/-]+)["\']?\b', re.I),
    re.compile(r'\b(main|master|develop|development|staging|production)\b', re.I),
]

_URL = re.compile(
    r"(https?://[^\s\"']+\.git[^\s\"']*|git@[^\s\"']+:[^\s\"']+)",
    re.I,
)
_PATH = re.compile(
    r"(?:^|\s)([\w./\\-]+\.(?:py|ts|tsx|js|jsx|md|json|yaml|yml|txt|csv|html|css|go|rs|java|kt|xml|toml|cfg|ini|env))(?:\s|$)",
    re.I,
)
_PATH_EXPLICIT = re.compile(
    r'\b(?:file\s+)?["\']([^"\']+)["\']|'
    r'\bin\s+([\w./\\-]+\.\w+)\b|'
    r'\b(?:discard|restore|revert)\s+(?:changes\s+in\s+)?([\w./\\-]+\.\w+)',
    re.I,
)
_MESSAGE_PATTERNS = [
    re.compile(r'[-]m\s+["\']([^"\']+)["\']', re.I),
    re.compile(r'\bcommit\s+(?:with\s+)?(?:message\s+)?["\']([^"\']+)["\']', re.I),
    re.compile(r'\bmessage\s+["\']([^"\']+)["\']', re.I),
    re.compile(r'\bstash\s+(?:with\s+)?(?:message\s+)?["\']([^"\']+)["\']', re.I),
    re.compile(r'\bwith\s+message\s+["\']([^"\']+)["\']', re.I),
]
_QUOTED = re.compile(r'"([^"]+)"|\'([^\']+)\'')
_REMOTE_NAME = re.compile(r"\b(origin|upstream)\b", re.I)
_FORCE_DELETE = re.compile(r"\b(force|forced)\s+delete\b|\bdelete\s+.*\bforce", re.I)


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s/@.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _detect_action(normalized: str, raw: str) -> str | None:
    lowered = raw.lower()
    for action, phrases in _ACTION_PATTERNS:
        for phrase in phrases:
            if " " in phrase or len(phrase) > 6:
                if phrase in normalized or phrase in lowered:
                    return action
            elif re.search(rf"\b{re.escape(phrase)}\b", normalized) or re.search(
                rf"\b{re.escape(phrase)}\b", lowered
            ):
                return action
    return None


def _extract_path(raw: str) -> str | None:
    m = _PATH_EXPLICIT.search(raw)
    if m:
        for group in m.groups():
            if group:
                return group
    m = _PATH.search(raw)
    if m:
        return m.group(1)
    return None


def _extract_branch(raw: str, normalized: str) -> str | None:
    skip = {
        "origin",
        "upstream",
        "remote",
        "branch",
        "repo",
        "repository",
        "changes",
        "commits",
        "latest",
        "all",
        "everything",
        "file",
        "files",
        # push phrasing noise (not branch names)
        "to",
        "my",
        "this",
        "current",
        "work",
        "code",
        "github",
        "gitlab",
    }
    for pattern in _BRANCH_PATTERNS:
        for match in pattern.finditer(raw):
            name = (match.group(1) if match.lastindex else match.group(0)) or ""
            name = name.strip("\"'")
            if name.lower() in skip:
                continue
            if "/" in name and name.startswith("http"):
                continue
            return name
    return None


def _extract_message(raw: str) -> str | None:
    for pattern in _MESSAGE_PATTERNS:
        m = pattern.search(raw)
        if m:
            return m.group(1)
    q = _QUOTED.search(raw)
    if q:
        text = q.group(1) or q.group(2)
        lower = raw.lower()
        if any(
            ctx in lower
            for ctx in ("commit", "stash", "message", "tag", "-m")
        ):
            return text
    return None


def parse_intent(text: str) -> ParsedIntent:
    """Extract structured hints from user intent text."""
    raw = text.strip()
    if not raw:
        return ParsedIntent(raw="")

    normalized = _normalize(raw)
    action = _detect_action(normalized, raw)
    path = _extract_path(raw)
    branch = _extract_branch(raw, normalized)
    message = _extract_message(raw)
    url_match = _URL.search(raw)
    url = url_match.group(1) if url_match else None

    remote_m = _REMOTE_NAME.search(raw)
    remote = remote_m.group(1).lower() if remote_m else None

    lowered = raw.lower()
    wants_upstream = any(
        p in lowered
        for p in (
            "-u",
            "set upstream",
            "upstream",
            "first push",
            "initial push",
            "track",
            "publish new branch",
        )
    )
    wants_staged_diff = any(
        p in lowered for p in ("staged diff", "diff staged", "diff --staged", "cached diff", "staged changes")
    )
    wants_force = action == "force_push" or "force push" in lowered
    wants_untracked_stash = action == "stash_untracked" or any(
        p in lowered for p in ("untracked", "including untracked", "stash all", "stash everything")
    )

    keywords: list[str] = []
    if action:
        keywords.append(action)
    for token in (
        "push",
        "pull",
        "fetch",
        "stash",
        "commit",
        "merge",
        "rebase",
        "branch",
        "clone",
        "force",
        "main",
        "master",
    ):
        if token in lowered and token not in keywords:
            keywords.append(token)

    name = branch

    return ParsedIntent(
        raw=raw,
        name=name,
        branch=branch,
        remote=remote,
        path=path,
        url=url,
        message=message,
        wants_upstream=wants_upstream,
        keywords=keywords,
        primary_action=action,
        wants_staged_diff=wants_staged_diff,
        wants_force_push=wants_force,
        wants_untracked_stash=wants_untracked_stash,
        wants_force_delete=bool(_FORCE_DELETE.search(raw)),
    )
