from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from agent_benchmark.storage.models import BatchManifest


class RawResultWriter:
    def __init__(self, batch_dir: Path) -> None:
        self.batch_dir = batch_dir
        self.raw_dir = batch_dir / "raw"
        self.outputs_dir = batch_dir / "outputs"
        self.traces_dir = batch_dir / "traces"
        self.aggregated_dir = batch_dir / "aggregated"
        self.reports_dir = batch_dir / "reports"
        for path in (
            self.raw_dir,
            self.outputs_dir,
            self.traces_dir,
            self.aggregated_dir,
            self.reports_dir,
            self.batch_dir / "workspaces",
        ):
            path.mkdir(parents=True, exist_ok=True)

    def write_output(self, run_id: str, text: str) -> str:
        path = self.outputs_dir / f"{run_id}.txt"
        path.write_text(text, encoding="utf-8")
        return str(path.relative_to(self.batch_dir))

    def write_trace(self, run_id: str, trace_events: list[dict[str, Any]]) -> str:
        path = self.traces_dir / f"{run_id}.json"
        path.write_text(json.dumps(trace_events, indent=2, ensure_ascii=True), encoding="utf-8")
        return str(path.relative_to(self.batch_dir))

    def write_raw_result(self, result: BaseModel) -> str:
        path = self.raw_dir / f"{result.run_id}.json"
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return str(path.relative_to(self.batch_dir))

    def write_manifest(self, manifest: BatchManifest) -> None:
        path = self.batch_dir / "batch_manifest.json"
        path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
