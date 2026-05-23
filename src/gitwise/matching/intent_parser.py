"""
Parse natural-language intent for gw do.

Convention: text inside **single quotes** is the value (message, branch name, file, URL).
Wrap the whole intent in double quotes for the shell:

  gw do "commit 'fix login bug'"
  gw do "create branch 'feature/login'"
  gw do "delete branch 'old-stuff'"
"""

from __future__ import annotations

import re

from gitwise.models import ParsedIntent

_SINGLE_QUOTED = re.compile(r"'([^']+)'")

# Which ParsedIntent field a single-quoted value maps to, by primary action
_QUOTED_FIELD_BY_ACTION: dict[str, str] = {
    "commit": "message",
    "stash": "message",
    "stash_untracked": "message",
    "branch_create": "name",
    "branch_switch": "name",
    "branch_delete": "name",
    "tag": "name",
    "merge": "name",
    "rebase": "name",
    "push": "branch",
    "discard_file": "path",
    "clone": "url",
    "remote": "url",
}

_ACTION_PATTERNS: list[tuple[str, list[str]]] = [
    ("force_push", ["force push", "force-with-lease", "force with lease", "safe force push"]),
    ("abort", ["abort merge", "abort rebase", "cancel merge", "cancel rebase", "stop merge", "stop rebase"]),
    ("fetch", ["fetch and prune", "fetch prune", "git fetch", "fetch"]),
    ("pull", ["pull latest", "pull changes", "git pull", "pull"]),
    ("push", ["push to", "push this", "upload", "publish", "git push", "push"]),
    ("stash_untracked", ["stash untracked", "stash including untracked", "stash all", "stash everything"]),
    ("stash", ["git stash", "stash pop", "stash apply", "unstash", "stash"]),
    ("undo_commit", ["uncommit", "undo commit", "undo last commit", "soft reset", "remove last commit"]),
    ("commit", ["git commit", "commit changes", "commit with", "commit this", "commit"]),
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
_DOUBLE_QUOTED = re.compile(r'"([^"]+)"')
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


def _extract_single_quoted(raw: str) -> str | None:
    m = _SINGLE_QUOTED.search(raw)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return None


def _infer_field_for_quoted(action: str | None, quoted: str) -> str:
    """Pick field when action is unknown or ambiguous."""
    if action and action in _QUOTED_FIELD_BY_ACTION:
        return _QUOTED_FIELD_BY_ACTION[action]
    lower = quoted.lower()
    if "://" in quoted or quoted.startswith("git@"):
        return "url"
    if re.search(r"\.[a-zA-Z0-9]+$", quoted) and ("/" in quoted or "\\" in quoted):
        return "path"
    if action in ("commit", "stash", "stash_untracked") or "message" in (action or ""):
        return "message"
    return "name"


def _apply_quoted_value(
    action: str | None,
    quoted: str,
    *,
    message: str | None,
    branch: str | None,
    name: str | None,
    path: str | None,
    url: str | None,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    field = _infer_field_for_quoted(action, quoted)
    if field == "message":
        message = quoted
    elif field == "branch":
        branch = quoted
        name = name or quoted
    elif field == "name":
        name = quoted
        branch = branch or quoted
    elif field == "path":
        path = quoted
    elif field == "url":
        url = quoted
    return message, branch, name, path, url


def _extract_path_fallback(raw: str) -> str | None:
    m = re.search(r"\bin\s+([\w./\\-]+\.\w+)\b", raw, re.I)
    if m:
        return m.group(1)
    m = _PATH.search(raw)
    return m.group(1) if m else None


def _extract_branch_fallback(raw: str) -> str | None:
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
            if name.lower() in skip or name.startswith("http"):
                continue
            return name
    return None


def _extract_message_fallback(raw: str) -> str | None:
    m = _DOUBLE_QUOTED.search(raw)
    if m and any(ctx in raw.lower() for ctx in ("commit", "stash", "message", "tag")):
        return m.group(1)
    return None


def parse_intent(text: str) -> ParsedIntent:
    """Extract structured hints from user intent text."""
    raw = text.strip()
    if not raw:
        return ParsedIntent(raw="")

    normalized = _normalize(raw)
    action = _detect_action(normalized, raw)

    message: str | None = None
    branch: str | None = None
    name: str | None = None
    path: str | None = None
    url: str | None = None

    quoted = _extract_single_quoted(raw)
    if quoted:
        message, branch, name, path, url = _apply_quoted_value(
            action, quoted, message=message, branch=branch, name=name, path=path, url=url
        )

    if not branch:
        branch = _extract_branch_fallback(raw)
    if not name:
        name = branch
    if not message:
        message = _extract_message_fallback(raw)
    if not path:
        path = _extract_path_fallback(raw)
    if not url:
        url_match = _URL.search(raw)
        url = url_match.group(1) if url_match else None

    remote_m = _REMOTE_NAME.search(raw)
    remote = remote_m.group(1).lower() if remote_m else None

    lowered = raw.lower()
    wants_upstream = any(
        p in lowered
        for p in ("-u", "set upstream", "upstream", "first push", "initial push", "track", "publish new branch")
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
    for token in ("push", "pull", "fetch", "stash", "commit", "merge", "rebase", "branch", "clone", "force", "main", "master"):
        if token in lowered and token not in keywords:
            keywords.append(token)

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
