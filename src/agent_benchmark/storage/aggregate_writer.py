from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from agent_benchmark.aggregate.export_csv import flatten_result
from agent_benchmark.storage.models import RouterRunResult, SingleMultiRunResult


class AggregateWriter:
    def write(
        self,
        output_dir: Path,
        results: list[SingleMultiRunResult | RouterRunResult],
        formats: set[str],
    ) -> dict[str, str]:
        rows = [flatten_result(result).model_dump(mode="json") for result in results]
        output_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, str] = {}

        if "jsonl" in formats:
            jsonl_path = output_dir / "all_results.jsonl"
            with jsonl_path.open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=True) + "\n")
            written["jsonl"] = str(jsonl_path)

        frame = pd.DataFrame(rows)
        if "csv" in formats:
            csv_path = output_dir / "all_results.csv"
            frame.to_csv(csv_path, index=False)
            written["csv"] = str(csv_path)
        if "parquet" in formats:
            parquet_path = output_dir / "all_results.parquet"
            frame.to_parquet(parquet_path, index=False)
            written["parquet"] = str(parquet_path)
        return written
