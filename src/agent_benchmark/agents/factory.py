from __future__ import annotations

from typing import Any

from agents import Agent, ModelSettings


def _supports_temperature(model: str) -> bool:
    normalized = model.lower()
    return not normalized.startswith("gpt-5")


def build_agent(
    *,
    name: str,
    instructions: str,
    model: str,
    temperature: float,
    tools: list[Any],
    output_type: type[Any] | None = None,
) -> Agent:
    model_settings = ModelSettings(include_usage=True)
    if _supports_temperature(model):
        model_settings.temperature = temperature
    return Agent(
        name=name,
        instructions=instructions,
        model=model,
        tools=tools,
        output_type=output_type,
        model_settings=model_settings,
    )
