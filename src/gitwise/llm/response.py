"""Parse structured JSON from gw ask LLM responses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass
class AskPlan:
    summary: str
    commands: list[str]
    gitwise_intent: str | None = None


@dataclass
class AskResponse:
    mode: str  # explain | plan
    answer: str
    plan: AskPlan | None = None


def parse_ask_response(raw: str) -> AskResponse:
    """Parse JSON from Gemini (tolerates accidental markdown fences)."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    data = json.loads(text)
    mode = str(data.get("mode", "explain")).lower()
    answer = str(data.get("answer", "")).strip()

    plan_data = data.get("plan")
    plan = None
    if isinstance(plan_data, dict) and mode == "plan":
        commands = plan_data.get("commands") or []
        if not isinstance(commands, list):
            raise ValueError("plan.commands must be a list")
        plan = AskPlan(
            summary=str(plan_data.get("summary", "")).strip(),
            commands=[str(c).strip() for c in commands if str(c).strip()],
            gitwise_intent=(plan_data.get("gitwise_intent") or None),
        )

    return AskResponse(mode=mode, answer=answer, plan=plan)
