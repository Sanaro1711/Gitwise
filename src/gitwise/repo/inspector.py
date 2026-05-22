"""Inspect local git repository state via read-only git commands."""

from __future__ import annotations

from pathlib import Path

from gitwise.models import RepoState
from gitwise.repo.git_runner import run_git, run_git_optional

_NOT_IN_REPO = RepoState(
    in_repo=False,
    root=None,
    repo_name=None,
    branch=None,
    remote=None,
    remote_url=None,
    upstream=None,
    upstream_ref=None,
    default_branch=None,
)


class RepoInspector:
    """Build a RepoState from the repository at cwd (or a given path)."""

    def __init__(self, cwd: Path | str | None = None) -> None:
        self._cwd = Path(cwd) if cwd else Path.cwd()

    def inspect(self) -> RepoState:
        if not self._inside_work_tree():
            return _NOT_IN_REPO

        root = run_git(["rev-parse", "--show-toplevel"], cwd=self._cwd)
        root_path = Path(root)
        branch = run_git_optional(["branch", "--show-current"], cwd=self._cwd) or None
        remote = self._primary_remote()
        remote_url = self._remote_url(remote)
        upstream, upstream_ref = self._upstream(branch, remote)
        default_branch = self._default_branch(remote)
        modified, staged, untracked = self._status_counts()
        ahead, behind = self._ahead_behind(upstream_ref)
        repo_name = self._repo_name(root_path, remote)

        return RepoState(
            in_repo=True,
            root=root,
            repo_name=repo_name,
            branch=branch,
            remote=remote,
            remote_url=remote_url,
            upstream=upstream,
            upstream_ref=upstream_ref,
            default_branch=default_branch,
            modified_count=modified,
            staged_count=staged,
            untracked_count=untracked,
            ahead=ahead,
            behind=behind,
            has_upstream=upstream_ref is not None,
            has_remote=remote is not None,
            has_stash=self._has_stash(),
            merge_in_progress=(root_path / ".git" / "MERGE_HEAD").exists(),
            rebase_in_progress=self._rebase_in_progress(root_path),
        )

    def _inside_work_tree(self) -> bool:
        value = run_git_optional(["rev-parse", "--is-inside-work-tree"], cwd=self._cwd)
        return value == "true"

    def _primary_remote(self) -> str | None:
        remotes = run_git_optional(["remote"], cwd=self._cwd)
        if not remotes:
            return None
        names = remotes.splitlines()
        return "origin" if "origin" in names else names[0]

    def _remote_url(self, remote: str | None) -> str | None:
        if not remote:
            return None
        return run_git_optional(["remote", "get-url", remote], cwd=self._cwd)

    def _upstream(
        self, branch: str | None, remote: str | None
    ) -> tuple[str | None, str | None]:
        if not branch:
            return None, None
        merge = run_git_optional(
            ["config", "--get", f"branch.{branch}.merge"], cwd=self._cwd
        )
        upstream_remote = run_git_optional(
            ["config", "--get", f"branch.{branch}.remote"], cwd=self._cwd
        ) or remote
        if not merge or not upstream_remote:
            return None, None
        # refs/heads/feature -> feature
        short = merge.removeprefix("refs/heads/")
        upstream_display = f"{upstream_remote}/{short}"
        upstream_ref = f"{upstream_remote}/{short}"
        return upstream_display, upstream_ref

    def _default_branch(self, remote: str | None) -> str | None:
        if remote:
            sym = run_git_optional(
                ["symbolic-ref", f"refs/remotes/{remote}/HEAD"], cwd=self._cwd
            )
            if sym:
                # refs/remotes/origin/main -> main
                return sym.split("/")[-1]
        for candidate in ("main", "master"):
            if run_git_optional(["rev-parse", "--verify", f"refs/heads/{candidate}"], cwd=self._cwd):
                return candidate
            if remote and run_git_optional(
                ["rev-parse", "--verify", f"refs/remotes/{remote}/{candidate}"],
                cwd=self._cwd,
            ):
                return candidate
        return None

    def _status_counts(self) -> tuple[int, int, int]:
        porcelain = run_git_optional(["status", "--porcelain"], cwd=self._cwd) or ""
        modified = staged = untracked = 0
        for line in porcelain.splitlines():
            if len(line) < 4:
                continue
            x, y = line[0], line[1]
            if x == "?" and y == "?":
                untracked += 1
                continue
            if x != " " and x != "?":
                staged += 1
            if y != " " and y != "?":
                modified += 1
        return modified, staged, untracked

    def _ahead_behind(self, upstream_ref: str | None) -> tuple[int, int]:
        if not upstream_ref:
            return 0, 0
        counts = run_git_optional(
            ["rev-list", "--left-right", "--count", f"{upstream_ref}...HEAD"],
            cwd=self._cwd,
        )
        if not counts:
            return 0, 0
        parts = counts.split()
        if len(parts) != 2:
            return 0, 0
        behind, ahead = int(parts[0]), int(parts[1])
        return ahead, behind

    def _has_stash(self) -> bool:
        stash_list = run_git_optional(["stash", "list"], cwd=self._cwd)
        return bool(stash_list and stash_list.strip())

    def _rebase_in_progress(self, root: Path) -> bool:
        git_dir = root / ".git"
        if (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
            return True
        head = run_git_optional(["rev-parse", "--git-path", "rebase-merge"], cwd=self._cwd)
        return bool(head and Path(root / head).exists())

    def _repo_name(self, root: Path, remote: str | None) -> str:
        if remote:
            url = run_git_optional(["remote", "get-url", remote], cwd=self._cwd)
            if url:
                # git@github.com:user/repo.git or https://github.com/user/repo
                name = url.rstrip("/").split("/")[-1]
                if name.endswith(".git"):
                    name = name[:-4]
                if name:
                    return name
        return root.name
