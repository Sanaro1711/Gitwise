"""Execution pipeline result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PreCheckResult:
    ok: bool
    title: str = ""
    message: str = ""
    suggestions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PostCheckResult:
    ok: bool
    title: str = ""
    message: str = ""
    suggestions: list[str] = field(default_factory=list)


@dataclass
class FailureReport:
    kind: str
    title: str
    explanation: str
    suggestions: list[str] = field(default_factory=list)
    git_output: str = ""
