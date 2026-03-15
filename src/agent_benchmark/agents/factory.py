from __future__ import annotations

from typing import Any

from agents import Agent, ModelSettings


def build_agent(
    *,
    name: str,
    instructions: str,
    model: str,
    temperature: float,
    tools: list[Any],
    output_type: type[Any] | None = None,
) -> Agent:
    return Agent(
        name=name,
        instructions=instructions,
        model=model,
        tools=tools,
        output_type=output_type,
        model_settings=ModelSettings(temperature=temperature, include_usage=True),
    )
