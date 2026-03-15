from __future__ import annotations

from pathlib import Path

from agent_benchmark.config.loader import ConfigLoader


def test_tasks_inherit_global_repetitions(project_copy: Path) -> None:
    loader = ConfigLoader(project_copy)
    for task_dir in sorted((project_copy / "tasks").iterdir()):
        config = loader.load_task_config(task_dir)
        assert config.repetitions == 4
