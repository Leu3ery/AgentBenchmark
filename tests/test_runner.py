from __future__ import annotations

import json
from pathlib import Path

from agent_benchmark.benchmark import BenchmarkService
from agent_benchmark.execution.openai_client import AgentExecutionResult
from agent_benchmark.strategies.router import RouterDecision


class StatefulFakeExecutor:
    def __init__(self, fail_on_name: str | None = None) -> None:
        self.fail_on_name = fail_on_name
        self.calls: list[str] = []

    def run_agent(self, spec):
        self.calls.append(spec.name)
        if self.fail_on_name and spec.name == self.fail_on_name:
            raise RuntimeError(f"forced failure for {spec.name}")
        if spec.output_type is RouterDecision:
            output = RouterDecision(selected_route="single", reason="Simple enough", confidence=0.6)
            text = output.model_dump_json(indent=2)
        else:
            output = f"finished {spec.name}"
            text = output
        return AgentExecutionResult(
            final_output=output,
            final_output_text=text,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            tool_calls=[],
            agent_steps=[],
            trace_events=[],
            response_ids=["resp_x"],
        )


def test_run_task_single_and_router(project_copy: Path) -> None:
    service = BenchmarkService(project_copy, executor=StatefulFakeExecutor())
    single_results = service.run_task(
        project_copy / "tasks" / "task_003_data_analysis",
        strategy="single",
        batch_id="batch_single",
    )
    router_results = service.run_task(
        project_copy / "tasks" / "task_003_data_analysis",
        strategy="router",
        batch_id="batch_router",
    )
    assert len(single_results) == 4
    assert single_results[0].strategy == "single"
    assert len(router_results) == 1
    assert router_results[0].strategy == "router"


def test_run_all_aborts_on_first_failed_run(project_copy: Path) -> None:
    tasks_root = project_copy / "tasks"
    service = BenchmarkService(project_copy, executor=StatefulFakeExecutor(fail_on_name="planner"))

    try:
        service.run_all(tasks_root, strategy="multi", batch_id="batch_fail")
    except RuntimeError:
        pass
    else:
        raise AssertionError("run_all should have raised after the forced failure")

    manifest_path = project_copy / "runs" / "batch_fail" / "batch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["aborted"] is True
    assert manifest["status"] == "failed"
    assert manifest["failed_run_id"] is not None

    raw_dir = project_copy / "runs" / "batch_fail" / "raw"
    assert any(path.name.endswith(".json") for path in raw_dir.iterdir())
