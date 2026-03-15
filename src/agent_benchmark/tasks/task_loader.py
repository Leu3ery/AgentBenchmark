from __future__ import annotations

from pathlib import Path

from agent_benchmark.config.loader import ConfigLoader
from agent_benchmark.config.schemas import LoadedTask
from agent_benchmark.tasks.checksums import sha256_directory, sha256_file, sha256_text


class TaskLoader:
    def __init__(self, config_loader: ConfigLoader) -> None:
        self.config_loader = config_loader

    def load(self, task_dir: Path) -> LoadedTask:
        task_dir = task_dir.resolve()
        config = self.config_loader.load_task_config(task_dir)
        prompt_path = task_dir / config.prompt_file
        input_dir = task_dir / config.input_dir
        evaluation_dir = task_dir / config.evaluation_dir
        prompt_text = prompt_path.read_text(encoding="utf-8")

        return LoadedTask(
            root_dir=task_dir,
            prompt_text=prompt_text,
            config=config,
            input_dir=input_dir,
            evaluation_dir=evaluation_dir,
            prompt_path=prompt_path,
            prompt_checksum=sha256_text(prompt_text),
            input_checksum=sha256_directory(input_dir),
            task_config_checksum=sha256_file(task_dir / "task.yaml"),
        )
