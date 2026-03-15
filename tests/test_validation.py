from __future__ import annotations

from pathlib import Path

from agent_benchmark.benchmark import BenchmarkService


def test_validate_sample_tasks(project_copy: Path) -> None:
    service = BenchmarkService(project_copy)
    for task_dir in sorted((project_copy / "tasks").iterdir()):
        report = service.validate_task(task_dir)
        assert report.valid, report.errors


def test_validate_rejects_unknown_tools(project_copy: Path) -> None:
    task_dir = project_copy / "tasks" / "task_001_bugfix_csv"
    task_yaml = task_dir / "task.yaml"
    text = task_yaml.read_text(encoding="utf-8")
    task_yaml.write_text(text.replace("- terminal", "- nonexistent_tool"), encoding="utf-8")

    service = BenchmarkService(project_copy)
    report = service.validate_task(task_dir)
    assert not report.valid
    assert any("Unknown allowed_tools" in error for error in report.errors)
