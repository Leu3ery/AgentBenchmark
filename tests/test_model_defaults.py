from __future__ import annotations

from pathlib import Path

from agent_benchmark.config.loader import ConfigLoader


def test_task_models_default_from_models_yaml(project_copy: Path) -> None:
    loader = ConfigLoader(project_copy)
    config = loader.load_task_config(project_copy / "tasks" / "task_001_bugfix_csv")

    assert config.single_strategy.model == "gpt-5-mini"
    assert config.multi_strategy.model == "gpt-5-mini"
    assert config.router_strategy.model == "gpt-5-mini"
