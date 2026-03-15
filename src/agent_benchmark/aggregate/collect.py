from __future__ import annotations

import json
from pathlib import Path

from agent_benchmark.storage.models import RouterRunResult, SingleMultiRunResult


def _resolve_raw_files(path: Path) -> list[Path]:
    path = path.resolve()
    if path.is_dir() and path.name == "raw":
        return sorted(path.glob("*.json"))
    if (path / "raw").exists():
        return sorted((path / "raw").glob("*.json"))
    return sorted(path.glob("**/raw/*.json"))


def load_result_json(path: Path) -> SingleMultiRunResult | RouterRunResult:
    payload = json.loads(path.read_text(encoding="utf-8"))
    strategy = payload.get("strategy")
    if strategy == "router":
        return RouterRunResult.model_validate(payload)
    if strategy in {"single", "multi"}:
        return SingleMultiRunResult.model_validate(payload)
    raise ValueError(f"Unsupported strategy in result file {path}: {strategy}")


def collect_results(path: Path) -> list[SingleMultiRunResult | RouterRunResult]:
    raw_files = _resolve_raw_files(path)
    if not raw_files:
        raise FileNotFoundError(f"No raw result JSON files found under {path}")
    return [load_result_json(raw_file) for raw_file in raw_files]
