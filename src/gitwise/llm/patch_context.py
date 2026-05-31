"""Build redacted code patches for LLM context."""

from __future__ import annotations

from pathlib import Path

from gitwise.llm.sanitize import redact_secrets
from gitwise.repo.git_runner import run_git_optional

_SENSITIVE = (".env", "gemini_api_key", ".pem", "id_rsa", "credentials", "secrets/")
_MAX_FILES = 20
_CONTEXT_LINES = 5


def is_sensitive_path(path: str) -> bool:
    lower = path.lower()
    return any(s in lower for s in _SENSITIVE)


def list_changed_files(
    from_ref: str,
    to_ref: str,
    *,
    worktree: bool,
    cwd: Path | str | None,
) -> list[str]:
    args = ["diff", "--name-only", from_ref]
    if not worktree:
        args.append(to_ref)
    out = run_git_optional(args, cwd=cwd) or ""
    return [n for n in out.splitlines() if n.strip() and not is_sensitive_path(n)]


def build_safe_patch(
    from_ref: str,
    to_ref: str,
    *,
    worktree: bool,
    cwd: Path | str | None,
    max_chars: int = 20_000,
    max_files: int = _MAX_FILES,
) -> str:
    """Unified diff with added/removed code lines; skips sensitive and binary-only files."""
    names = list_changed_files(from_ref, to_ref, worktree=worktree, cwd=cwd)
    parts: list[str] = []
    used = 0

    for path in names[:max_files]:
        args = ["diff", f"-U{_CONTEXT_LINES}", "--no-color", "--no-ext-diff", from_ref]
        if not worktree:
            args.append(to_ref)
        args.extend(["--", path])
        chunk = run_git_optional(args, cwd=cwd) or ""
        if not chunk.strip() or "Binary files" in chunk:
            continue
        chunk = redact_secrets(chunk)
        remaining = max_chars - used
        if remaining <= 0:
            parts.append("... (remaining files omitted — patch size limit)")
            break
        if len(chunk) > remaining:
            parts.append(chunk[:remaining] + "\n... (patch truncated)")
            break
        parts.append(chunk)
        used += len(chunk)

    if len(names) > max_files:
        parts.append(f"... ({len(names) - max_files} more files not included in patch)")

    return "\n".join(parts)
