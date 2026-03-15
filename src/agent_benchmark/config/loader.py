from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_benchmark.config.schemas import (
    ConfigBundle,
    GlobalConfig,
    ModelsConfig,
    TaskConfig,
    ToolsConfig,
    deep_merge,
)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


class ConfigLoader:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self.config_dir = self.root_dir / "configs"

    def load_bundle(self) -> ConfigBundle:
        global_data = _load_yaml_file(self.config_dir / "global.yaml")
        models_data = _load_yaml_file(self.config_dir / "models.yaml")
        tools_data = _load_yaml_file(self.config_dir / "tools.yaml")
        return ConfigBundle(
            root_dir=self.root_dir,
            global_config=GlobalConfig.model_validate(global_data or {}),
            models_config=ModelsConfig.model_validate(models_data or {}),
            tools_config=ToolsConfig.model_validate(tools_data or {}),
        )

    def load_task_config(self, task_dir: Path) -> TaskConfig:
        bundle = self.load_bundle()
        task_path = task_dir / "task.yaml"
        task_data = _load_yaml_file(task_path)

        merged = deep_merge(
            {
                "repetitions": bundle.global_config.default_repetitions,
                "timeout_sec": bundle.global_config.default_timeout_sec,
                "single_strategy": {"model": bundle.models_config.default_model},
                "multi_strategy": {"model": bundle.models_config.default_model},
                "router_strategy": {"model": bundle.models_config.router_model},
            },
            task_data,
        )
        return TaskConfig.model_validate(merged)
