from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_benchmark.config.schemas import LoadedTask


@dataclass(slots=True)
class StrategyArtifacts:
    model: str
    temperature: float
    final_output_text: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    agent_steps: list[dict[str, Any]] = field(default_factory=list)
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    selected_route: str | None = None
    route_reason: str | None = None
    route_confidence: float | None = None


@dataclass(slots=True)
class StrategyContext:
    task: LoadedTask
    workspace_path: Path | None
    repetition_index: int | None
    model_override: str | None = None


class BaseStrategyRunner:
    strategy_name: str

    def run(self, context: StrategyContext) -> StrategyArtifacts:  # pragma: no cover - interface
        raise NotImplementedError
