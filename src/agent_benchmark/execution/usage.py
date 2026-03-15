from __future__ import annotations

from agent_benchmark.config.schemas import ModelsConfig
from agent_benchmark.storage.models import UsageTotals


def estimate_cost(model_name: str, models_config: ModelsConfig, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = models_config.models.get(model_name)
    if not pricing:
        return 0.0
    return round(
        (prompt_tokens / 1_000_000) * pricing.prompt_cost_per_1m
        + (completion_tokens / 1_000_000) * pricing.completion_cost_per_1m,
        6,
    )


def build_usage_totals(
    model_name: str,
    models_config: ModelsConfig,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> UsageTotals:
    return UsageTotals(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimate_cost(model_name, models_config, prompt_tokens, completion_tokens),
    )
