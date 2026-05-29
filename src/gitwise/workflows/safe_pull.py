"""Guided safe pull: stash → fetch → merge → conflict help → restore stash."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from gitwise.models import RepoState
from gitwise.output import format_whereami
from gitwise.repo.git_runner import GitResult, run_git_result
from gitwise.repo.inspector import RepoInspector
from gitwise.repo import merge_state

_STASH_MESSAGE = "gitwise: safe pull backup"


@dataclass
class SafePullContext:
    cwd: Path
    state: RepoState
    stash_ref: str | None = None
    stashed: bool = False
    merge_completed: bool = False
    stash_applied: bool = False
    notes: list[str] = field(default_factory=list)


def run_safe_pull(
    *,
    cwd: Path | str | None = None,
    dry_run: bool = False,
    skip_confirm: bool = False,
) -> int:
    """Run the full safe-pull workflow interactively."""
    work = Path(cwd) if cwd else Path.cwd()
    state = RepoInspector(cwd=work).inspect()
    ctx = SafePullContext(cwd=work, state=state)

    err = _preflight(state)
    if err:
        print(err, file=sys.stderr)
        return 1

    _print_overview(ctx)

    if dry_run:
        _print_dry_run_steps(ctx)
        return 0

    if not skip_confirm and not _confirm("Proceed with safe pull?"):
        print("Cancelled.")
        return 0

    if state.merge_in_progress:
        print("\nMerge already in progress — opening conflict guide.\n")
        if not _guide_merge_conflicts(ctx):
            return 1
    else:
        if not _run_pull_steps(ctx):
            return 1

    if ctx.stash_ref and ctx.merge_completed:
        _reapply_stash(ctx)

    _print_finish(ctx)
    return 0


def _preflight(state: RepoState) -> str | None:
    if not state.in_repo:
        return "Not inside a git repository."
    if not state.branch:
        return "You are not on a branch (detached HEAD). Switch to a branch before pulling."
    if not state.has_upstream or not state.upstream_ref:
        return (
            f"Branch '{state.branch}' has no upstream. "
            f'Run: gw do "push"  # sets upstream on first push'
        )
    if state.rebase_in_progress:
        return "A rebase is in progress. Finish or abort it before pulling."
    return None


def _print_overview(ctx: SafePullContext) -> None:
    s = ctx.state
    print("=== Safe pull ===\n")
    print(f"Branch:   {s.branch}")
    print(f"Upstream: {s.upstream}")
    print(f"Remote:   {s.remote}")
    if s.behind:
        print(f"Behind:   {s.behind} commit(s) on remote")
    else:
        print("Behind:   up to date with remote (fetch will still run)")
    if s.dirty_tree:
        print(
            f"Working tree: dirty "
            f"({s.modified_count} modified, {s.staged_count} staged, "
            f"{s.untracked_count} untracked) — will stash before merge"
        )
    else:
        print("Working tree: clean")
    if s.merge_in_progress:
        print("Note: merge in progress — will resume conflict resolution")
    print()


def _print_dry_run_steps(ctx: SafePullContext) -> None:
    s = ctx.state
    steps = []
    n = 1
    if s.dirty_tree and not s.merge_in_progress:
        steps.append(f"{n}. git stash push --include-untracked -m \"{_STASH_MESSAGE}\"")
        n += 1
    if not s.merge_in_progress:
        steps.append(f"{n}. git fetch {s.remote}")
        n += 1
        steps.append(f"{n}. git merge {s.upstream_ref} --no-edit")
        n += 1
    steps.append(f"{n}. (if conflicts) guided merge resolution")
    n += 1
    if s.dirty_tree:
        steps.append(f"{n}. git stash apply (keep stash until you confirm drop)")
    print("(dry-run — steps that would run)\n")
    for step in steps:
        print(f"  {step}")
    print()


def _run_pull_steps(ctx: SafePullContext) -> bool:
    if ctx.state.dirty_tree:
        if not _create_safe_stash(ctx):
            return False

    remote = ctx.state.remote or "origin"
    upstream = ctx.state.upstream_ref
    assert upstream

    print(f"\n--- Fetching from {remote} ---")
    fetch = run_git_result(["fetch", remote], cwd=ctx.cwd)
    _echo_git(fetch)
    if fetch.returncode != 0:
        print("Fetch failed.", file=sys.stderr)
        return False

    print(f"\n--- Merging {upstream} (no rebase) ---")
    merge = run_git_result(["merge", upstream, "--no-edit"], cwd=ctx.cwd)
    _echo_git(merge)

    ctx.state = RepoInspector(cwd=ctx.cwd).inspect()

    if merge.returncode == 0:
        ctx.merge_completed = True
        print("\nMerge completed successfully.")
        return True

    if ctx.state.merge_in_progress:
        print("\nMerge stopped due to conflicts.")
        return _guide_merge_conflicts(ctx)

    print("Merge failed.", file=sys.stderr)
    if merge.stderr.strip():
        print(merge.stderr.strip(), file=sys.stderr)
    return False


def _create_safe_stash(ctx: SafePullContext) -> bool:
    print("\n--- Stashing uncommitted changes ---")
    stash = run_git_result(
        ["stash", "push", "--include-untracked", "-m", _STASH_MESSAGE],
        cwd=ctx.cwd,
    )
    _echo_git(stash)
    if stash.returncode != 0:
        print("Could not stash changes. Commit or stash manually, then retry.", file=sys.stderr)
        return False
    ctx.stashed = True
    ctx.stash_ref = merge_state.latest_stash_ref(cwd=ctx.cwd)
    ctx.notes.append(f"Your work is saved in {ctx.stash_ref or 'stash'}.")
    return True


def _guide_merge_conflicts(ctx: SafePullContext) -> bool:
    while True:
        ctx.state = RepoInspector(cwd=ctx.cwd).inspect()
        if not ctx.state.merge_in_progress:
            ctx.merge_completed = True
            print("\nMerge complete.")
            return True

        conflicts = merge_state.unmerged_files(cwd=ctx.cwd)
        _print_conflict_header(ctx, conflicts)

        if not conflicts:
            print("All conflicts appear resolved. Completing merge commit...")
            commit = run_git_result(["commit", "--no-edit"], cwd=ctx.cwd)
            _echo_git(commit)
            if commit.returncode == 0:
                ctx.merge_completed = True
                print("\nMerge commit created.")
                return True
            print("Could not create merge commit. Stage resolved files and try again.", file=sys.stderr)
            continue

        choice = _prompt_conflict_action(len(conflicts))
        if choice == "quit":
            print("\nStopped. Merge still in progress.")
            print("Resume anytime with: gw pull   or   gw do 'pull latest'")
            if ctx.stash_ref:
                print(f"Your pre-pull stash is kept at {ctx.stash_ref}.")
            return False
        if choice == "abort":
            if _confirm("Abort merge and return to pre-merge state?"):
                abort = run_git_result(["merge", "--abort"], cwd=ctx.cwd)
                _echo_git(abort)
                print("Merge aborted.")
                if ctx.stash_ref:
                    print(f"Re-apply your stash when ready: git stash apply {ctx.stash_ref}")
                return False
            continue
        if choice == "status":
            continue
        if choice == "complete":
            print("Resolve and stage every conflicted file first (option 'a').")
            continue
        if choice.startswith("open:"):
            idx = int(choice.split(":")[1])
            _open_file(ctx, conflicts[idx - 1])
            continue
        if choice.startswith("diff:"):
            idx = int(choice.split(":")[1])
            _show_file_diff(ctx, conflicts[idx - 1])
            continue
        if choice.startswith("add:"):
            idx = int(choice.split(":")[1])
            path = conflicts[idx - 1]
            add = run_git_result(["add", path], cwd=ctx.cwd)
            _echo_git(add)
            if add.returncode == 0:
                print(f"Staged {path!r} — marked as resolved.")
            continue


def _print_conflict_header(ctx: SafePullContext, conflicts: list[str]) -> None:
    print("\n=== Merge conflicts ===\n")
    print(f"Branch: {ctx.state.branch}")
    merging = merge_state.merge_head_branch(cwd=ctx.cwd)
    if merging:
        print(f"Merging in: {merging}")
    print()
    if conflicts:
        print(f"Conflicted files ({len(conflicts)}):")
        for i, path in enumerate(conflicts, 1):
            print(f"  {i}. {path}")
    else:
        print("No unmerged files listed — checking if merge can be completed...")
    print()
    print("Working tree:")
    for line in merge_state.short_status(cwd=ctx.cwd).splitlines():
        print(f"  {line}")
    print()


def _prompt_conflict_action(num_files: int) -> str:
    print("What next?")
    print("  [1-N]  Open file in editor")
    print("  [d1-dN] Show diff for file")
    print("  [a1-aN] Mark file resolved (git add)")
    print("  [s]      Show status again")
    print("  [c]      Complete merge (commit) — when all conflicts are resolved")
    print("  [x]      Abort merge")
    print("  [q]      Quit for now (merge stays in progress)")
    try:
        raw = input("\nChoice: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return "quit"

    if raw in ("q", "quit"):
        return "quit"
    if raw in ("x", "abort"):
        return "abort"
    if raw in ("s", "status"):
        return "status"
    if raw in ("c", "commit", "complete"):
        return "complete"

    if raw.startswith("d") and raw[1:].isdigit():
        return f"diff:{raw[1:]}"
    if raw.startswith("a") and raw[1:].isdigit():
        return f"add:{raw[1:]}"
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= num_files:
            return f"open:{idx}"
    print("Unrecognized choice.")
    return "status"


def _open_file(ctx: SafePullContext, rel_path: str) -> None:
    full = ctx.cwd / rel_path
    if not full.exists():
        print(f"File not found: {rel_path}")
        return
    print(f"Opening {rel_path} ...")
    print("Remove conflict markers (<<<<<<<, =======, >>>>>>>), save, then mark resolved with 'a'.")
    _launch_editor(full, ctx.cwd)


def _show_file_diff(ctx: SafePullContext, rel_path: str) -> None:
    diff = merge_state.file_diff(rel_path, cwd=ctx.cwd)
    print(f"\n--- diff {rel_path} ---")
    print(diff if diff.strip() else "(no diff output)")
    print("--- end diff ---\n")


def _launch_editor(path: Path, cwd: Path) -> None:
    env_editor = (
        os.environ.get("GIT_EDITOR")
        or os.environ.get("EDITOR")
        or os.environ.get("VISUAL")
    )
    if env_editor:
        parts = shlex.split(env_editor)
        subprocess.run([*parts, str(path)], cwd=cwd)
        return

    if sys.platform == "win32":
        for cmd in (["code", "--wait", str(path)], ["notepad", str(path)]):
            try:
                subprocess.run(cmd, cwd=cwd, check=False)
                return
            except FileNotFoundError:
                continue
    else:
        for editor in ("nano", "vim", "vi"):
            if shutil.which(editor):
                subprocess.run([editor, str(path)], cwd=cwd)
                return

    print(f"Set EDITOR or GIT_EDITOR to open files. Edit manually: {path}")


def _reapply_stash(ctx: SafePullContext) -> None:
    assert ctx.stash_ref
    print(f"\n--- Restoring stashed changes ({ctx.stash_ref}) ---")
    print("Using 'stash apply' so your backup stays until you confirm it is safe to drop.\n")

    apply = run_git_result(["stash", "apply", ctx.stash_ref], cwd=ctx.cwd)
    _echo_git(apply)

    if apply.returncode != 0:
        print("\n=== Stash apply conflict ===")
        print("Your merge succeeded, but re-applying the stash caused conflicts.")
        _guide_stash_conflicts(ctx)
        return

    ctx.stash_applied = True
    conflicts = merge_state.unmerged_files(cwd=ctx.cwd)
    if conflicts:
        print("\nStash apply left conflicts:")
        _guide_stash_conflicts(ctx)
        return

    print("\nStash applied cleanly.")
    if _confirm(f"Drop {ctx.stash_ref} now? (your working tree looks good)"):
        drop = run_git_result(["stash", "drop", ctx.stash_ref], cwd=ctx.cwd)
        _echo_git(drop)
        if drop.returncode == 0:
            ctx.stash_ref = None
            print("Stash dropped.")
    else:
        print(f"Kept {ctx.stash_ref}. Drop later with: git stash drop {ctx.stash_ref}")


def _guide_stash_conflicts(ctx: SafePullContext) -> None:
    while True:
        conflicts = merge_state.unmerged_files(cwd=ctx.cwd)
        print("\n=== Stash restore conflicts ===\n")
        if conflicts:
            for i, path in enumerate(conflicts, 1):
                print(f"  {i}. {path}")
        print()
        for line in merge_state.short_status(cwd=ctx.cwd).splitlines():
            print(f"  {line}")
        print()
        print("Fix conflicts, then stage files (git add). Options:")
        print("  [1-N] open  [dN] diff  [aN] stage  [s] status  [q] quit")
        try:
            raw = input("\nChoice: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if raw in ("q", "quit"):
            break
        if raw.isdigit() and conflicts:
            _open_file(ctx, conflicts[int(raw) - 1])
        elif raw.startswith("d") and raw[1:].isdigit() and conflicts:
            _show_file_diff(ctx, conflicts[int(raw[1:]) - 1])
        elif raw.startswith("a") and raw[1:].isdigit() and conflicts:
            path = conflicts[int(raw[1:]) - 1]
            run_git_result(["add", path], cwd=ctx.cwd)
            print(f"Staged {path!r}")
        if not merge_state.unmerged_files(cwd=ctx.cwd):
            print("\nStash conflicts resolved.")
            if ctx.stash_ref and _confirm(f"Drop {ctx.stash_ref}?"):
                run_git_result(["stash", "drop", ctx.stash_ref], cwd=ctx.cwd)
                ctx.stash_ref = None
            break

    if ctx.stash_ref:
        print(f"\nStash kept at {ctx.stash_ref} until you are satisfied.")


def _print_finish(ctx: SafePullContext) -> None:
    ctx.state = RepoInspector(cwd=ctx.cwd).inspect()
    print("\n=== Done ===\n")
    for note in ctx.notes:
        print(f"  • {note}")
    if ctx.stash_ref:
        print(f"  • Stash backup still available: {ctx.stash_ref}")
    print()
    print(format_whereami(ctx.state))


def _echo_git(result: GitResult) -> None:
    if result.stdout.strip():
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr.strip():
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False
    return answer in ("y", "yes")
