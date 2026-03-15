from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class WorkspaceHandle:
    workspace_path: Path
    relative_workspace_path: str


def create_workspace(
    batch_dir: Path,
    task_id: str,
    input_dir: Path,
    strategy: str,
    repetition_index: int | None = None,
) -> WorkspaceHandle:
    task_workspace_root = batch_dir / "workspaces" / task_id
    suffix = strategy if repetition_index is None else f"{strategy}_rep_{repetition_index}"
    workspace_path = task_workspace_root / suffix
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    shutil.copytree(input_dir, workspace_path)
    relative_path = str(workspace_path.relative_to(batch_dir))
    return WorkspaceHandle(workspace_path=workspace_path, relative_workspace_path=relative_path)


def cleanup_workspace(workspace_path: Path) -> None:
    if workspace_path.exists():
        shutil.rmtree(workspace_path)


def compute_changed_files(source_dir: Path, workspace_dir: Path) -> list[str]:
    changed: list[str] = []
    source_files = {path.relative_to(source_dir) for path in source_dir.rglob("*") if path.is_file()}
    workspace_files = {path.relative_to(workspace_dir) for path in workspace_dir.rglob("*") if path.is_file()}

    for relative_path in sorted(source_files | workspace_files):
        source_path = source_dir / relative_path
        workspace_path = workspace_dir / relative_path
        if not source_path.exists() or not workspace_path.exists():
            changed.append(relative_path.as_posix())
            continue
        if source_path.read_bytes() != workspace_path.read_bytes():
            changed.append(relative_path.as_posix())
    return changed
