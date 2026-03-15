from __future__ import annotations

import shutil
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def project_copy(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    shutil.copytree(PROJECT_ROOT / "configs", target / "configs")
    shutil.copytree(PROJECT_ROOT / "tasks", target / "tasks")
    return target
