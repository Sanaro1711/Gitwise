"""Shared data models for repo state and command planning."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RepoState:
    """Snapshot of the current git repository (read-only inspection)."""

    in_repo: bool
    root: str | None
    repo_name: str | None
    branch: str | None
    remote: str | None
    remote_url: str | None  # e.g. https://github.com/user/repo.git
    upstream: str | None  # e.g. origin/main
    upstream_ref: str | None  # e.g. origin/main for rev-list
    default_branch: str | None
    modified_count: int = 0
    staged_count: int = 0
    untracked_count: int = 0
    ahead: int = 0
    behind: int = 0
    has_upstream: bool = False
    has_remote: bool = False
    has_stash: bool = False
    merge_in_progress: bool = False
    rebase_in_progress: bool = False

    @property
    def dirty_tree(self) -> bool:
        return self.modified_count + self.staged_count + self.untracked_count > 0

    @property
    def clean_tree(self) -> bool:
        return self.in_repo and not self.dirty_tree

    @property
    def has_uncommitted(self) -> bool:
        return self.modified_count > 0 or self.untracked_count > 0

    @property
    def has_staged(self) -> bool:
        return self.staged_count > 0

    @property
    def merge_or_rebase_in_progress(self) -> bool:
        return self.merge_in_progress or self.rebase_in_progress


@dataclass
class ParsedIntent:
    """Values extracted from natural-language intent."""

    raw: str
    name: str | None = None  # branch, tag, etc.
    branch: str | None = None  # explicit target branch (e.g. main)
    remote: str | None = None
    path: str | None = None
    url: str | None = None
    message: str | None = None
    wants_upstream: bool = False
    keywords: list[str] = field(default_factory=list)
    primary_action: str | None = None
    wants_staged_diff: bool = False
    wants_force_push: bool = False
    wants_untracked_stash: bool = False
    wants_force_delete: bool = False


@dataclass
class MatchResult:
    """A recipe match with score metadata."""

    recipe_id: str
    score: float
    phrase: str


@dataclass
class CommandPlan:
    """Resolved recipe ready for user confirmation."""

    recipe_id: str
    category: str
    explanation: str
    commands: list[str]
    danger: bool = False
    confirmation_level: str = "standard"
    match_score: float = 0.0
    matched_phrase: str = ""
    warnings: list[str] = field(default_factory=list)
