"""Tests for gw diff report."""

from __future__ import annotations

import json

from gitwise.workflows.diff_report import (
    DiffStats,
    DiffSummary,
    RefLabel,
    _format_report,
    _parse_shortstat,
    _parse_summary,
)


def test_parse_shortstat() -> None:
    stats = _parse_shortstat(" 4 files changed, 126 insertions(+), 32 deletions(-)")
    assert stats.files == 4
    assert stats.insertions == 126
    assert stats.deletions == 32


def test_parse_shortstat_empty() -> None:
    stats = _parse_shortstat("")
    assert stats.files == 0


def test_parse_summary_json() -> None:
    raw = json.dumps(
        {
            "overview": "Adds push workflow.",
            "files": [{"path": "a.py", "summary": "New command."}],
            "main_changes": ["Added push", "Added tests"],
            "risk_level": "Medium",
            "risk_areas": ["Upstream detection"],
            "suggested_next_step": "pytest tests/test_push.py",
        }
    )
    s = _parse_summary(raw, [])
    assert s.overview == "Adds push workflow."
    assert s.risk_level == "Medium"
    assert len(s.main_changes) == 2


def test_format_report_shape() -> None:
    text = _format_report(
        RefLabel("abc1234", "Added pull feature"),
        RefLabel("Current working tree", "includes staged and unstaged changes"),
        DiffStats(4, 126, 32),
        DiffSummary(
            overview="Adds guided push.",
            files=[{"path": "push.py", "summary": "New command."}],
            main_changes=["Added push workflow"],
            risk_level="Medium",
            risk_areas=["Remote ahead check"],
            suggested_next_step="pytest tests/test_push.py",
        ),
    )
    assert "Gitwise Diff Report" in text
    assert "From: abc1234" in text
    assert "Current working tree" in text
    assert "4 files changed" in text
    assert "Risk level:" in text
    assert "pytest tests/test_push.py" in text
