"""gw ask — LLM-guided git help with validated command plans."""

from __future__ import annotations

import sys
from pathlib import Path

from gitwise.execution.failures import format_pre_check_block
from gitwise.execution.pipeline import execute_plan, run_pre_checks_for_plan
from gitwise.llm.config import MissingApiKeyError, require_api_key
from gitwise.llm.context import build_repo_context
from gitwise.llm.gemini import GeminiError, generate
from gitwise.llm.response import AskResponse, parse_ask_response
from gitwise.llm.validator import ValidationResult, validate_llm_plan
from gitwise.matching.intent_parser import parse_intent
from gitwise.workflows.save import run_save


def run_ask(
    question: str,
    *,
    cwd: Path | str | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> int:
    work = Path(cwd) if cwd else Path.cwd()
    question = question.strip()
    if not question:
        print("Provide a question, e.g. gw ask \"how do I undo my last commit?\"", file=sys.stderr)
        return 1

    try:
        api_key = require_api_key(cwd=work)
    except MissingApiKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    state, repo_context = build_repo_context(cwd=work)

    print("=== gw ask ===\n")
    print(f"Question: {question}\n")

    try:
        raw = generate(api_key=api_key, user_message=question, repo_context=repo_context)
        parsed = parse_ask_response(raw.text)
    except GeminiError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (ValueError, KeyError) as exc:
        print(f"Could not parse LLM response: {exc}", file=sys.stderr)
        return 1

    _print_answer(parsed)

    if parsed.mode != "plan" or not parsed.plan or not parsed.plan.commands:
        return 0

    validation = validate_llm_plan(
        parsed.plan.commands,
        question=question,
        state=state,
        gitwise_intent=parsed.plan.gitwise_intent,
        cwd=work,
    )
    _print_validation(validation)

    if dry_run:
        print("\n(dry-run — no commands executed)")
        return 0

    if validation.status == "unsafe":
        print("\nCommands blocked for safety.", file=sys.stderr)
        return 1

    if validation.gitwise_plan is None:
        return _offer_run_unverified(parsed, work, yes=yes)

    return _offer_run_gitwise(
        parsed,
        validation,
        state,
        work,
        yes=yes,
    )


def _print_answer(parsed: AskResponse) -> None:
    print("Answer:")
    for line in parsed.answer.splitlines():
        print(f"  {line}")
    print()

    if parsed.mode == "plan" and parsed.plan:
        print("Suggested plan:")
        if parsed.plan.summary:
            print(f"  {parsed.plan.summary}")
        print()
        print("Commands:")
        for cmd in parsed.plan.commands:
            print(f"  $ {cmd}")
        print()


def _print_validation(validation: ValidationResult) -> None:
    print(f"Validation: {validation.status}")
    print(f"  {validation.message}")
    if validation.status == "partial" and validation.gitwise_commands:
        print()
        print("Gitwise would run:")
        for cmd in validation.gitwise_commands:
            print(f"  $ {cmd}")
    print()


def _offer_run_gitwise(
    parsed: AskResponse,
    validation: ValidationResult,
    state,
    cwd: Path,
    *,
    yes: bool,
) -> int:
    plan = validation.gitwise_plan
    assert plan is not None
    intent = parse_intent(parsed.plan.gitwise_intent if parsed.plan else "")

    if validation.status == "validated":
        print("Gitwise validated this plan. You can run it safely.")
    else:
        print("Gitwise recommends its own plan over the LLM suggestion.")

    if not yes and not _confirm("Run the Gitwise plan?"):
        print("Cancelled.")
        return 0

    pre = run_pre_checks_for_plan(plan, state, intent, cwd=cwd)
    if not pre.ok:
        print(format_pre_check_block(pre), file=sys.stderr)
        return 1

    if plan.recipe_id == "pull_latest":
        from gitwise.workflows.safe_pull import run_safe_pull

        return run_safe_pull(cwd=cwd, intent=intent, skip_confirm=True)

    if plan.recipe_id == "save":
        message = intent.message or _message_from_plan(plan)
        return run_save(message, cwd=cwd, yes=True)

    result = execute_plan(plan, state, intent, cwd=cwd)
    if result.exit_code == 0:
        print("\nDone.")
    return result.exit_code


def _offer_run_unverified(
    parsed: AskResponse,
    cwd: Path,
    *,
    yes: bool,
) -> int:
    print(
        "Gitwise could not verify these commands against a known workflow.\n"
        "Running unverified LLM commands is disabled for safety.\n"
        "Try rephrasing as gw do \"...\" or ask a clarifying question.",
        file=sys.stderr,
    )
    return 1


def _message_from_plan(plan) -> str:
    for cmd in plan.commands:
        if "commit -m" in cmd:
            import shlex

            try:
                parts = shlex.split(cmd, posix=False)
                idx = parts.index("-m") if "-m" in parts else parts.index("--message")
                return parts[idx + 1]
            except (ValueError, IndexError):
                pass
    return "update"


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False
    return answer in ("y", "yes")
