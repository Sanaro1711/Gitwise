"""gw diff — git diff + Gemini summary report."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from gitwise.llm.config import MissingApiKeyError, require_api_key
from gitwise.llm.diff_prompts import DIFF_SYSTEM_PROMPT
from gitwise.llm.gemini import GeminiError, generate
from gitwise.llm.sanitize import redact_secrets
from gitwise.repo.git_runner import GitError, run_git, run_git_optional
from gitwise.repo.inspector import RepoInspector

_WORKTREE = ("worktree", ".", "WORKTREE")
_MAX_PATCH = 12_000
_SENSITIVE = (".env", "gemini_api_key", ".pem", "id_rsa", "credentials")


@dataclass
class DiffStats:
    files: int
    insertions: int
    deletions: int


@dataclass
class RefLabel:
    display: str
    detail: str


@dataclass
class DiffSummary:
    overview: str
    files: list[dict[str, str]]
    main_changes: list[str]
    risk_level: str
    risk_areas: list[str]
    suggested_next_step: str


def run_diff(
    from_ref: str,
    to_ref: str | None = None,
    *,
    cwd: Path | str | None = None,
    dry_run: bool = False,
) -> int:
    work = Path(cwd) if cwd else Path.cwd()
    if not RepoInspector(cwd=work).inspect().in_repo:
        print("Not inside a git repository.", file=sys.stderr)
        return 1

    from_ref = from_ref.strip()
    to_ref = (to_ref or "worktree").strip()
    to_worktree = to_ref.lower() in _WORKTREE

    try:
        from_label = _ref_label(from_ref, cwd=work)
        to_label = (
            RefLabel("Current working tree", "includes staged and unstaged changes")
            if to_worktree
            else _ref_label(to_ref, cwd=work)
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    stats = _diff_stats(from_ref, to_ref, worktree=to_worktree, cwd=work)
    names = _diff_names(from_ref, to_ref, worktree=to_worktree, cwd=work)
    patch = _diff_patch(from_ref, to_ref, worktree=to_worktree, cwd=work)

    if dry_run:
        _print_dry_run(from_label, to_label, stats, names)
        return 0

    try:
        api_key = require_api_key(cwd=work)
    except MissingApiKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if stats.files == 0 and not names:
        print("No differences between the selected refs.", file=sys.stderr)
        return 0

    try:
        summary = _summarize(api_key, from_label, to_label, stats, names, patch)
    except GeminiError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Could not parse LLM response: {exc}", file=sys.stderr)
        return 1

    print(_format_report(from_label, to_label, stats, summary))
    return 0


def _ref_label(ref: str, *, cwd: Path) -> RefLabel:
    try:
        short = run_git(["rev-parse", "--short", ref], cwd=cwd)
        subject = run_git(["log", "-1", "--format=%s", ref], cwd=cwd)
    except GitError as exc:
        raise ValueError(f"Invalid git ref: {ref!r} ({exc})") from exc
    return RefLabel(short, subject)


def _diff_stats(from_ref: str, to_ref: str, *, worktree: bool, cwd: Path) -> DiffStats:
    args = ["diff", "--shortstat", from_ref]
    if not worktree:
        args.append(to_ref)
    out = run_git_optional(args, cwd=cwd) or ""
    return _parse_shortstat(out)


def _parse_shortstat(text: str) -> DiffStats:
    files = ins = dels = 0
    if m := re.search(r"(\d+)\s+files?\s+changed", text):
        files = int(m.group(1))
    if m := re.search(r"(\d+)\s+insertions?", text):
        ins = int(m.group(1))
    if m := re.search(r"(\d+)\s+deletions?", text):
        dels = int(m.group(1))
    return DiffStats(files=files, insertions=ins, deletions=dels)


def _diff_names(from_ref: str, to_ref: str, *, worktree: bool, cwd: Path) -> list[str]:
    args = ["diff", "--name-only", from_ref]
    if not worktree:
        args.append(to_ref)
    out = run_git_optional(args, cwd=cwd) or ""
    return [n for n in out.splitlines() if n.strip() and not _is_sensitive(n)]


def _diff_patch(from_ref: str, to_ref: str, *, worktree: bool, cwd: Path) -> str:
    args = ["diff", from_ref]
    if not worktree:
        args.append(to_ref)
    out = run_git_optional(args, cwd=cwd) or ""
    out = redact_secrets(out)
    if len(out) > _MAX_PATCH:
        out = out[:_MAX_PATCH] + "\n... (patch truncated for LLM)"
    return out


def _is_sensitive(path: str) -> bool:
    lower = path.lower()
    return any(s in lower for s in _SENSITIVE)


def _summarize(
    api_key: str,
    from_label: RefLabel,
    to_label: RefLabel,
    stats: DiffStats,
    names: list[str],
    patch: str,
) -> DiffSummary:
    prompt = (
        f"From: {from_label.display} - {from_label.detail}\n"
        f"To: {to_label.display}"
        + (f" - {to_label.detail}" if to_label.detail else "")
        + f"\n\nStats: {stats.files} files, +{stats.insertions}/-{stats.deletions}\n"
        f"Files:\n" + "\n".join(names[:40])
        + (f"\n... and {len(names) - 40} more" if len(names) > 40 else "")
        + f"\n\nPatch:\n{patch or '(empty)'}"
    )
    raw = generate(
        api_key=api_key,
        user_message=prompt,
        system_prompt=DIFF_SYSTEM_PROMPT,
        max_output_tokens=1536,
    )
    return _parse_summary(raw.text, names)


def _parse_summary(raw: str, fallback_names: list[str]) -> DiffSummary:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    files = data.get("files") or []
    if not files and fallback_names:
        files = [{"path": n, "summary": "Changed."} for n in fallback_names[:20]]
    return DiffSummary(
        overview=str(data.get("overview", "")).strip(),
        files=[{"path": str(f.get("path", "")), "summary": str(f.get("summary", ""))} for f in files],
        main_changes=[str(c).strip() for c in (data.get("main_changes") or []) if str(c).strip()],
        risk_level=str(data.get("risk_level", "Medium")).strip(),
        risk_areas=[str(r).strip() for r in (data.get("risk_areas") or []) if str(r).strip()],
        suggested_next_step=str(data.get("suggested_next_step", "")).strip(),
    )


def _format_report(
    from_label: RefLabel,
    to_label: RefLabel,
    stats: DiffStats,
    summary: DiffSummary,
) -> str:
    lines = [
        "Gitwise Diff Report",
        "===================",
        "",
        "Comparing:",
        f"  From: {from_label.display} - {from_label.detail}",
        f"  To:   {to_label.display}"
        + (f" - {to_label.detail}" if to_label.detail else ""),
        "",
        "Overview:",
        f"  {summary.overview}",
        "",
        "Stats:",
        f"  {stats.files} files changed",
        f"  +{stats.insertions} additions",
        f"  -{stats.deletions} deletions",
        "",
        "Changed files:",
    ]
    for f in summary.files:
        path = f.get("path", "")
        desc = f.get("summary", "")
        if path:
            lines.append(f"  {path}")
            if desc:
                lines.append(f"    {desc}")
            lines.append("")

    if summary.main_changes:
        lines.extend(["Main changes:"])
        for i, change in enumerate(summary.main_changes, 1):
            lines.append(f"  {i}. {change}")
        lines.append("")

    lines.extend(["Risk level:", f"  {summary.risk_level}", ""])
    if summary.risk_areas:
        lines.append("Risk areas:")
        for r in summary.risk_areas:
            lines.append(f"  - {r}")
        lines.append("")

    if summary.suggested_next_step:
        lines.extend(["Suggested next step:", f"  {summary.suggested_next_step}"])

    return "\n".join(lines)


def _print_dry_run(
    from_label: RefLabel,
    to_label: RefLabel,
    stats: DiffStats,
    names: list[str],
) -> None:
    print("=== gw diff (dry-run) ===\n")
    print(f"From: {from_label.display} - {from_label.detail}")
    print(f"To:   {to_label.display}")
    print(f"\nStats: {stats.files} files, +{stats.insertions}/-{stats.deletions}")
    if names:
        print("\nFiles:")
        for n in names[:20]:
            print(f"  {n}")
        if len(names) > 20:
            print(f"  ... and {len(names) - 20} more")
    print("\n(dry-run — LLM summary not requested)")
