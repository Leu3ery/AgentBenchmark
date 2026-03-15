from __future__ import annotations

import csv
from pathlib import Path

from agent_benchmark.benchmark import BenchmarkService
from agent_benchmark.execution.openai_client import AgentExecutionResult
from agent_benchmark.strategies.router import RouterDecision


class FakeExecutor:
    def run_agent(self, spec):
        if spec.output_type is RouterDecision:
            output = RouterDecision(
                selected_route="multi",
                reason="Task benefits from decomposition.",
                confidence=0.88,
            )
            text = output.model_dump_json(indent=2)
        else:
            output = f"done: {spec.name}"
            text = output
        return AgentExecutionResult(
            final_output=output,
            final_output_text=text,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            tool_calls=[{"tool_name": "read_file", "agent_id": spec.name}],
            agent_steps=[{"agent_id": spec.name, "event_type": "agent_end", "timestamp": "2026-01-01T00:00:00+00:00"}],
            trace_events=[{"agent_id": spec.name, "event_type": "agent_end"}],
            response_ids=["resp_test"],
        )


def test_aggregate_outputs_csv_and_jsonl(project_copy: Path) -> None:
    service = BenchmarkService(project_copy, executor=FakeExecutor())
    service.run_task(project_copy / "tasks" / "task_001_bugfix_csv", strategy="single", batch_id="batch_a")
    service.run_task(project_copy / "tasks" / "task_001_bugfix_csv", strategy="router", batch_id="batch_b")

    written = service.aggregate(project_copy / "runs")
    assert "csv" in written
    assert "jsonl" in written

    csv_path = Path(written["csv"])
    assert csv_path.exists()
    with csv_path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert {row["strategy"] for row in rows} == {"single", "router"}
