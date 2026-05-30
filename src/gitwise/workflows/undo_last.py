"""gw undo last — explain undo options and help pick the safest one."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from gitwise.models import RepoState
from gitwise.repo import probes
from gitwise.repo.git_runner import GitResult, run_git_result
from gitwise.repo.inspector import RepoInspector


@dataclass(frozen=True)
class UndoOption:
    key: str
    title: str
    summary: str
    best_when: str
    caution: str
    commands: list[str]
    danger: bool = False


def build_undo_options(state: RepoState, *, cwd: Path | str | None = None) -> list[UndoOption]:
    """Return undo choices that apply to the current repository state."""
    options: list[UndoOption] = []

    if state.merge_in_progress:
        options.append(
            UndoOption(
                key="abort_merge",
                title="Abort merge",
                summary="Cancel the in-progress merge and return to the state before it started.",
                best_when="You started a merge (often from pull) and want to back out entirely.",
                caution="Discards merge progress. Uncommitted conflict resolutions are lost.",
                commands=["git merge --abort"],
                danger=True,
            )
        )

    if state.rebase_in_progress:
        options.append(
            UndoOption(
                key="abort_rebase",
                title="Abort rebase",
                summary="Cancel the in-progress rebase and restore the branch to its pre-rebase state.",
                best_when="A rebase went wrong or you changed your mind mid-rebase.",
                caution="Discards rebase progress. Resolve conflicts manually if you continue instead.",
                commands=["git rebase --abort"],
                danger=True,
            )
        )

    if probes.parent_commit_exists(cwd=cwd):
        options.extend(
            [
                UndoOption(
                    key="soft_reset",
                    title="Undo last commit, keep changes staged",
                    summary="Moves HEAD back one commit. Your files stay exactly as they were, still staged.",
                    best_when="You need to fix the commit message, combine commits, or add forgotten files.",
                    caution=(
                        "Safe locally. If the commit was already pushed, resetting rewrites history — "
                        "use 'Revert last commit' instead for shared branches."
                    ),
                    commands=["git reset --soft HEAD~1"],
                ),
                UndoOption(
                    key="mixed_reset",
                    title="Undo last commit, keep changes unstaged",
                    summary="Moves HEAD back one commit and unstages everything, but keeps file edits.",
                    best_when="You want to uncommit and re-stage only part of the work.",
                    caution="Same push warning as soft reset — avoid on commits others already pulled.",
                    commands=["git reset HEAD~1"],
                ),
                UndoOption(
                    key="revert_commit",
                    title="Revert last commit (safe for shared branches)",
                    summary="Creates a new commit that undoes the last commit's changes.",
                    best_when="The commit is already on a shared remote and others may have pulled it.",
                    caution="History stays intact. You may need to resolve conflicts if files changed since.",
                    commands=["git revert HEAD --no-edit"],
                ),
                UndoOption(
                    key="hard_reset",
                    title="Undo last commit and discard its changes",
                    summary="Moves HEAD back one commit and permanently deletes those file changes.",
                    best_when="The last commit was a mistake and you want everything from it gone.",
                    caution="Destructive and cannot be undone. Never use on pushed commits unless you know the cost.",
                    commands=["git reset --hard HEAD~1"],
                    danger=True,
                ),
            ]
        )

    if state.has_staged:
        options.append(
            UndoOption(
                key="unstage",
                title="Unstage everything (keep file edits)",
                summary="Removes all files from the staging area without changing your working tree.",
                best_when="You ran git add too eagerly and have not committed yet.",
                caution="Does not undo a commit — only clears the index.",
                commands=["git restore --staged ."],
            )
        )

    if state.dirty_tree:
        options.append(
            UndoOption(
                key="discard_all",
                title="Discard all uncommitted changes",
                summary="Restores tracked files to HEAD and removes untracked files and directories.",
                best_when="You want a completely clean working tree and do not need any local edits.",
                caution="Permanent data loss for uncommitted work. Stash first if you might need anything back.",
                commands=["git restore .", "git clean -fd"],
                danger=True,
            )
        )

    return options


def preflight_undo(state: RepoState, *, cwd: Path | str | None = None) -> str | None:
    if not state.in_repo:
        return "Not inside a git repository."
    options = build_undo_options(state, cwd=cwd)
    if not options:
        return "Nothing to undo — no commits to reset, nothing staged, and working tree is clean."
    return None


def run_undo_last(
    *,
    cwd: Path | str | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> int:
    work = Path(cwd) if cwd else Path.cwd()
    state = RepoInspector(cwd=work).inspect()

    err = preflight_undo(state, cwd=work)
    if err:
        print(err, file=sys.stderr)
        return 1

    options = build_undo_options(state, cwd=work)
    _print_menu(state, options)

    if dry_run:
        print("(dry-run — no commands executed)")
        return 0

    choice = _prompt_choice(len(options))
    if choice is None:
        print("Cancelled.")
        return 0

    option = options[choice - 1]

    print()
    print(f"Selected: {option.title}")
    print(f"  {option.summary}")
    print()
    print("Commands:")
    for cmd in option.commands:
        print(f"  $ {cmd}")
    print()

    if not yes and not _confirm_option(option):
        print("Cancelled.")
        return 0

    return _execute_option(option, work)


def _print_menu(state: RepoState, options: list[UndoOption]) -> None:
    print("=== Undo last ===\n")
    print(f"Branch: {state.branch or '(detached HEAD)'}")
    if state.merge_in_progress:
        print("State:  merge in progress")
    elif state.rebase_in_progress:
        print("State:  rebase in progress")
    elif state.dirty_tree:
        print("State:  uncommitted changes present")
    else:
        print("State:  clean working tree")
    print()
    print("Pick the option that matches what you want to undo:\n")

    for i, opt in enumerate(options, 1):
        tag = " [destructive]" if opt.danger else ""
        print(f"  [{i}] {opt.title}{tag}")
        print(f"      {opt.summary}")
        print(f"      Best when: {opt.best_when}")
        print(f"      Note: {opt.caution}")
        print()

    print("  [q] Quit without doing anything")
    print()


def _prompt_choice(num_options: int) -> int | None:
    try:
        raw = input("Choice: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if raw in ("q", "quit", ""):
        return None
    if raw.isdigit():
        n = int(raw)
        if 1 <= n <= num_options:
            return n
    print("Invalid choice.", file=sys.stderr)
    return None


def _confirm_option(option: UndoOption) -> bool:
    if option.danger:
        try:
            answer = input("Type 'yes' to confirm you understand the risk: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return False
        return answer == "yes"

    try:
        answer = input("Proceed? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False
    return answer in ("y", "yes")


def _execute_option(option: UndoOption, cwd: Path) -> int:
    for cmd in option.commands:
        args = _git_args(cmd)
        result = run_git_result(args, cwd=cwd)
        _echo_git(result)
        if result.returncode != 0:
            print(f"Command failed: {cmd}", file=sys.stderr)
            return result.returncode

    print("\nDone.")
    return 0


def _git_args(command: str) -> list[str]:
    parts = command.split()
    if not parts or parts[0] != "git":
        raise ValueError(f"Invalid git command: {command}")
    return parts[1:]


def _echo_git(result: GitResult) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "", file=sys.stderr)
