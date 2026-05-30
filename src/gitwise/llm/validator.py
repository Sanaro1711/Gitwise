"""Validate LLM-suggested git commands against Gitwise plans."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from gitwise.matching.intent_parser import parse_intent
from gitwise.matching.push_resolver import resolve_push
from gitwise.models import CommandPlan, ParsedIntent, RepoState
from gitwise.recipes.planner import plan_from_intent
from gitwise.workflows.save import build_save_plan, preflight_save


@dataclass
class ValidationResult:
    status: str  # validated | partial | unverified | unsafe
    message: str
    gitwise_plan: CommandPlan | None = None
    llm_commands: list[str] | None = None
    gitwise_commands: list[str] | None = None


_BLOCKED_SUBSTRINGS = (
    "git config",
    "credential",
    "filter-branch",
    "update-ref -d",
    "push --force",
    "push -f ",
    "push --force-with-lease",  # must go through gitwise recipe
)


def validate_llm_plan(
    llm_commands: list[str],
    *,
    question: str,
    state: RepoState,
    gitwise_intent: str | None = None,
    cwd: Path | str | None = None,
) -> ValidationResult:
    """Compare LLM commands with what Gitwise would recommend."""
    safe, reason = _commands_are_safe(llm_commands)
    if not safe:
        return ValidationResult(
            status="unsafe",
            message=reason,
            llm_commands=llm_commands,
        )

    gitwise_plan = _resolve_gitwise_plan(question, state, gitwise_intent, cwd=cwd)

    # Save workflows: rebuild gitwise plan using the LLM's commit message when possible.
    save_from_llm = _save_plan_from_llm_commands(llm_commands, state)
    if save_from_llm is not None:
        gitwise_plan = save_from_llm

    push_plan = _push_plan_for_current_branch(question, state, llm_commands)
    if push_plan is not None:
        gitwise_plan = push_plan

    if gitwise_plan is None:
        return ValidationResult(
            status="unverified",
            message=(
                "Gitwise could not match this to a known workflow. "
                "Review the commands carefully before running."
            ),
            llm_commands=llm_commands,
        )

    gw_cmds = gitwise_plan.commands
    if _commands_equivalent(llm_commands, gw_cmds, state):
        return ValidationResult(
            status="validated",
            message="Validated — Gitwise would run the same commands.",
            gitwise_plan=gitwise_plan,
            llm_commands=llm_commands,
            gitwise_commands=gw_cmds,
        )

    return ValidationResult(
        status="partial",
        message=(
            "Gitwise found a related workflow but the commands differ. "
            "Prefer the Gitwise plan unless you understand the difference."
        ),
        gitwise_plan=gitwise_plan,
        llm_commands=llm_commands,
        gitwise_commands=gw_cmds,
    )


def _resolve_gitwise_plan(
    question: str,
    state: RepoState,
    gitwise_intent: str | None,
    *,
    cwd: Path | str | None,
) -> CommandPlan | None:
    candidates = [question.strip()]
    if gitwise_intent and gitwise_intent.strip() not in candidates:
        candidates.append(gitwise_intent.strip())

    for text in candidates:
        plan, _, _, err = plan_from_intent(text, cwd=cwd)
        if plan and not err:
            return plan

    save_plan = _try_save_plan(question, state)
    if save_plan:
        return save_plan

    return None


def _try_save_plan(question: str, state: RepoState) -> CommandPlan | None:
    if not _looks_like_save(question):
        return None
    if preflight_save(state):
        return None
    intent = parse_intent(question)
    message = intent.message or _default_save_message(question)
    try:
        sp = build_save_plan(state, message)
    except ValueError:
        return None
    return CommandPlan(
        recipe_id="save",
        category="Commit",
        explanation=sp.explanation,
        commands=sp.commands,
        confirmation_level="standard",
    )


def _looks_like_save(text: str) -> bool:
    lower = text.lower()
    hits = sum(
        1
        for word in (
            "save",
            "publish",
            "commit and push",
            "push my",
            "push all",
            "backup",
            "upload",
        )
        if word in lower
    )
    return hits >= 1 and "pull" not in lower


def _default_save_message(question: str) -> str:
    intent = parse_intent(question)
    if intent.message:
        return intent.message
    return "update"


def _commands_are_safe(commands: list[str]) -> tuple[bool, str]:
    if not commands:
        return False, "No commands to run."
    for cmd in commands:
        stripped = cmd.strip()
        lower = stripped.lower()
        if not lower.startswith("git "):
            return False, f"Only git commands are allowed, got: {cmd!r}"
        if any(b in lower for b in _BLOCKED_SUBSTRINGS):
            return False, f"Blocked command for safety: {cmd}"
        if re.search(r"[;&|`$]", stripped):
            return False, f"Shell operators are not allowed: {cmd!r}"
    return True, ""


def _commands_equivalent(
    llm_cmds: list[str],
    gw_cmds: list[str],
    state: RepoState,
) -> bool:
    llm_norm = [_normalize_command(c) for c in _expand_commands(llm_cmds)]
    gw_norm = [_normalize_command(c) for c in _expand_commands(gw_cmds)]
    if llm_norm == gw_norm:
        return True
    # Push may differ only by -u flag when upstream unset
    if _same_except_push_upstream(llm_norm, gw_norm, state):
        return True
    return False


def _expand_commands(commands: list[str]) -> list[str]:
    out: list[str] = []
    for cmd in commands:
        for part in re.split(r"\s*&&\s*", cmd):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _normalize_command(cmd: str) -> tuple[str, ...]:
    """Tokenize for comparison; collapse whitespace in -m messages."""
    try:
        tokens = shlex.split(cmd, posix=False)
    except ValueError:
        tokens = cmd.split()
    if not tokens:
        return tuple()
    if tokens[0].lower() == "git":
        tokens = tokens[1:]
    normalized: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i].lower()
        if t in ("-m", "--message") and i + 1 < len(tokens):
            normalized.extend(["-m", _strip_quotes(tokens[i + 1])])
            i += 2
            continue
        normalized.append(t)
        i += 1
    return tuple(normalized)


def _same_except_push_upstream(
    a: list[tuple[str, ...]],
    b: list[tuple[str, ...]],
    state: RepoState,
) -> bool:
    if len(a) != len(b):
        return False
    for ta, tb in zip(a, b, strict=True):
        if ta == tb:
            continue
        if _is_push_tokens(ta) and _is_push_tokens(tb):
            if _push_without_u(ta) == _push_without_u(tb):
                continue
        return False
    return True


def _is_push_tokens(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and tokens[0] == "push"


def _push_without_u(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(t for t in tokens if t not in ("-u", "--set-upstream"))


def _push_plan_for_current_branch(
    question: str,
    state: RepoState,
    llm_commands: list[str],
) -> CommandPlan | None:
    expanded = _expand_commands(llm_commands)
    if len(expanded) != 1 or _command_kind(expanded[0]) != "push":
        return None
    if _has_explicit_push_target(question):
        return None
    intent = ParsedIntent(raw=question, primary_action="push")
    try:
        push = resolve_push(state, intent)
    except ValueError:
        return None
    return CommandPlan(
        recipe_id="push_auto",
        category="Sync",
        explanation=push.explanation,
        commands=push.commands,
        confirmation_level="standard",
    )


def _has_explicit_push_target(text: str) -> bool:
    lower = text.lower()
    if "push to" in lower or "push this to" in lower:
        return True
    return bool(re.search(r"\bpush\s+(?:to\s+)?(?:origin/)?[a-z0-9._/-]+\b", lower))


def _save_plan_from_llm_commands(
    llm_commands: list[str],
    state: RepoState,
) -> CommandPlan | None:
    expanded = _expand_commands(llm_commands)
    if not _is_save_shape(expanded):
        return None
    message = _extract_commit_message(expanded)
    if not message or preflight_save(state):
        return None
    try:
        sp = build_save_plan(state, message)
    except ValueError:
        return None
    return CommandPlan(
        recipe_id="save",
        category="Commit",
        explanation=sp.explanation,
        commands=sp.commands,
        confirmation_level="standard",
    )


def _is_save_shape(commands: list[str]) -> bool:
    kinds = [_command_kind(c) for c in commands]
    return kinds.count("add") >= 1 and "commit" in kinds and "push" in kinds


def _command_kind(cmd: str) -> str:
    tokens = _normalize_command(cmd)
    if not tokens:
        return "other"
    if tokens[0] == "add":
        return "add"
    if tokens[0] == "commit":
        return "commit"
    if tokens[0] == "push":
        return "push"
    return "other"


def _extract_commit_message(commands: list[str]) -> str | None:
    for cmd in commands:
        tokens = _normalize_command(cmd)
        if not tokens or tokens[0] != "commit":
            continue
        if "-m" in tokens:
            idx = tokens.index("-m")
            if idx + 1 < len(tokens):
                return tokens[idx + 1]
    return None


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value
