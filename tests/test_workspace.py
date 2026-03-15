from __future__ import annotations

from pathlib import Path

from agent_benchmark.tasks.workspace import compute_changed_files, create_workspace


def test_workspace_copy_and_changed_files(project_copy: Path) -> None:
    batch_dir = project_copy / "runs" / "batch_test"
    input_dir = project_copy / "tasks" / "task_001_bugfix_csv" / "input"
    handle = create_workspace(batch_dir, "task_001_bugfix_csv", input_dir, "single", 1)

    parser_file = handle.workspace_path / "repo" / "parser.py"
    parser_file.write_text(parser_file.read_text(encoding="utf-8") + "\n# modified\n", encoding="utf-8")

    changed = compute_changed_files(input_dir, handle.workspace_path)
    assert changed == ["repo/parser.py"]
