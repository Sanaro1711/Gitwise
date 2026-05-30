"""gw save — stage all, commit, and push the current branch."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from gitwise.execution.failures import classify_failure, format_failure_report
from gitwise.matching.push_resolver import resolve_push
from gitwise.models import ParsedIntent, RepoState
from gitwise.repo.git_runner import GitResult, run_git_result
from gitwise.repo.inspector import RepoInspector


@dataclass(frozen=True)
class SavePlan:
    message: str
    commands: list[str]
    explanation: str
    warnings: list[str]


def build_save_plan(state: RepoState, message: str) -> SavePlan:
    """Build add → commit → push commands for the current branch."""
    message = message.strip()
    if not message:
        raise ValueError("Commit message cannot be empty.")

    push = resolve_push(state, ParsedIntent(raw="push"))
    commands = ["git add .", f'git commit -m "{_shell_quote(message)}"', *push.commands]

    explanation = (
        "Stages every change in the working tree, creates a commit with your message, "
        f"then pushes branch '{state.branch}' to the remote."
    )
    warnings: list[str] = []
    if push.uses_upstream_flag:
        warnings.append(push.explanation.split(". Note:")[0].strip() + ".")
    if state.behind > 0:
        warnings.append(
            f"You are {state.behind} commit(s) behind the remote — push may be rejected until you pull."
        )

    return SavePlan(
        message=message,
        commands=commands,
        explanation=explanation,
        warnings=[w.strip() for w in warnings if w.strip()],
    )


def preflight_save(state: RepoState) -> str | None:
    if not state.in_repo:
        return "Not inside a git repository."
    if not state.branch:
        return "You are not on a branch (detached HEAD). Switch to a branch before saving."
    if not state.has_remote and not state.remote:
        return "No remote configured — cannot push after commit."
    if state.merge_or_rebase_in_progress:
        return "A merge or rebase is in progress. Finish or abort it before saving."
    if state.clean_tree:
        if state.ahead > 0:
            return (
                "Nothing to commit — working tree is clean. "
                'Use gw do "push" to publish your existing local commits.'
            )
        return "Nothing to save — working tree is clean and there are no unpushed commits."
    return None


def run_save(
    message: str,
    *,
    cwd: Path | str | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> int:
    work = Path(cwd) if cwd else Path.cwd()
    state = RepoInspector(cwd=work).inspect()

    err = preflight_save(state)
    if err:
        print(err, file=sys.stderr)
        return 1

    try:
        plan = build_save_plan(state, message)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    _print_overview(state, plan)

    if dry_run:
        print("(dry-run — no commands executed)")
        return 0

    if not yes and not _confirm():
        print("Cancelled.")
        return 0

    return _execute_save(plan, work, state)


def _print_overview(state: RepoState, plan: SavePlan) -> None:
    print("=== Save ===\n")
    print(f"Branch:  {state.branch}")
    print(f"Remote:  {state.remote or 'origin'}")
    print(f"Message: {plan.message!r}")
    print()
    print("Why:")
    print(f"  {plan.explanation}")
    if plan.warnings:
        print()
        print("Warnings:")
        for w in plan.warnings:
            print(f"  ! {w}")
    print()
    print("Commands:")
    for cmd in plan.commands:
        print(f"  $ {cmd}")
    print()


def _confirm() -> bool:
    try:
        answer = input("Proceed? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False
    return answer in ("y", "yes")


def _execute_save(plan: SavePlan, cwd: Path, state_before: RepoState) -> int:
    message = plan.message

    add = run_git_result(["add", "."], cwd=cwd)
    _echo_git(add)
    if add.returncode != 0:
        return add.returncode

    commit = run_git_result(["commit", "-m", message], cwd=cwd)
    _echo_git(commit)
    if commit.returncode != 0:
        if "nothing to commit" in (commit.stdout + commit.stderr).lower():
            print("Nothing to commit after staging.", file=sys.stderr)
        else:
            state_after = RepoInspector(cwd=cwd).inspect()
            report = classify_failure(
                stderr=commit.stderr,
                stdout=commit.stdout,
                command=f'git commit -m "{message}"',
                recipe_id="save",
                state=state_after,
            )
            print(format_failure_report(report, state_after), file=sys.stderr)
        return commit.returncode

    push_cmd = plan.commands[-1]
    push_args = _parse_push_args(push_cmd)
    push = run_git_result(push_args, cwd=cwd)
    _echo_git(push)
    if push.returncode != 0:
        state_after = RepoInspector(cwd=cwd).inspect()
        report = classify_failure(
            stderr=push.stderr,
            stdout=push.stdout,
            command=push_cmd,
            recipe_id="save",
            state=state_after,
        )
        print(format_failure_report(report, state_after), file=sys.stderr)
        return push.returncode

    print("\nSaved and pushed.")
    return 0


def _parse_push_args(push_cmd: str) -> list[str]:
    """Turn 'git push -u origin branch' into argument list for run_git_result."""
    parts = push_cmd.split()
    if not parts or parts[0] != "git":
        raise ValueError(f"Invalid push command: {push_cmd}")
    return parts[1:]


def _shell_quote(text: str) -> str:
    """Escape double quotes for display in command strings."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _echo_git(result: GitResult) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "", file=sys.stderr)
