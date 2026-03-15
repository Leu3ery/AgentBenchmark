from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Literal

from pydantic import ValidationError

from agent_benchmark.aggregate.collect import collect_results
from agent_benchmark.config.loader import ConfigLoader
from agent_benchmark.config.schemas import LoadedTask, ValidationReport
from agent_benchmark.config.validator import validate_task_dir
from agent_benchmark.execution.openai_client import AgentExecutor, OpenAIAgentExecutor
from agent_benchmark.execution.timers import utc_now_iso
from agent_benchmark.execution.usage import build_usage_totals
from agent_benchmark.storage.aggregate_writer import AggregateWriter
from agent_benchmark.storage.models import BatchManifest, RouterRunResult, SingleMultiRunResult
from agent_benchmark.storage.raw_writer import RawResultWriter
from agent_benchmark.strategies.base import StrategyArtifacts, StrategyContext
from agent_benchmark.strategies.multi_agent import MultiAgentStrategyRunner
from agent_benchmark.strategies.router import RouterStrategyRunner
from agent_benchmark.strategies.single_agent import SingleAgentStrategyRunner
from agent_benchmark.tasks.task_loader import TaskLoader
from agent_benchmark.tasks.workspace import cleanup_workspace, compute_changed_files, create_workspace
from agent_benchmark.agents.tools import ToolRegistry


StrategySelector = Literal["single", "multi", "router"]


class StrategyName(str, Enum):
    single = "single"
    multi = "multi"
    router = "router"


def _normalize_strategy(strategy: StrategyName | str | None) -> StrategySelector | None:
    if strategy is None:
        return None
    if isinstance(strategy, StrategyName):
        return strategy.value
    return strategy


def _sdk_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _build_sdk_versions() -> dict[str, str]:
    return {
        "openai": _sdk_version("openai"),
        "openai-agents": _sdk_version("openai-agents"),
        "pydantic": _sdk_version("pydantic"),
    }


def _classify_error(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, ValidationError):
        return "invalid_config"
    if exc.__class__.__module__.startswith("openai"):
        return "model_error"
    if "tool" in exc.__class__.__name__.lower():
        return "tool_error"
    return "runtime_exception"


class BenchmarkService:
    def __init__(self, root_dir: Path, executor: AgentExecutor | None = None) -> None:
        self.root_dir = root_dir.resolve()
        self.config_loader = ConfigLoader(self.root_dir)
        self.task_loader = TaskLoader(self.config_loader)
        self.bundle = self.config_loader.load_bundle()
        self.tool_registry = ToolRegistry(self.bundle.tools_config.tools)
        self.executor = executor or OpenAIAgentExecutor()
        self.single_runner = SingleAgentStrategyRunner(self.executor, self.tool_registry)
        self.multi_runner = MultiAgentStrategyRunner(self.executor, self.tool_registry)
        self.router_runner = RouterStrategyRunner(self.executor)
        self.aggregate_writer = AggregateWriter()
        self.sdk_versions = _build_sdk_versions()

    def validate_task(self, task_dir: Path) -> ValidationReport:
        return validate_task_dir(task_dir, self.config_loader)

    def run_task(
        self,
        task_dir: Path,
        strategy: StrategyName | str | None = None,
        repetitions_override: int | None = None,
        model_override: str | None = None,
        batch_id: str | None = None,
        cleanup_workspaces: bool = False,
    ) -> list[SingleMultiRunResult | RouterRunResult]:
        report = self.validate_task(task_dir)
        if not report.valid:
            raise ValueError("\n".join(report.errors))
        task = self.task_loader.load(task_dir)
        run_batch_id = batch_id or self._generate_batch_id()
        batch_dir = self.root_dir / "runs" / run_batch_id
        writer = RawResultWriter(batch_dir)
        manifest = BatchManifest(batch_id=run_batch_id, started_at=utc_now_iso())
        writer.write_manifest(manifest)
        try:
            results = self._run_loaded_task(
                task,
                writer,
                manifest,
                strategy=_normalize_strategy(strategy),
                repetitions_override=repetitions_override,
                model_override=model_override,
                cleanup_workspaces=cleanup_workspaces,
            )
            manifest.finished_at = utc_now_iso()
            manifest.status = "completed"
            writer.write_manifest(manifest)
            return results
        except Exception:
            manifest.finished_at = utc_now_iso()
            manifest.status = "failed"
            manifest.aborted = True
            writer.write_manifest(manifest)
            raise

    def run_all(
        self,
        tasks_root: Path,
        strategy: StrategyName | str | None = None,
        repetitions_override: int | None = None,
        model_override: str | None = None,
        batch_id: str | None = None,
        cleanup_workspaces: bool = False,
    ) -> list[SingleMultiRunResult | RouterRunResult]:
        run_batch_id = batch_id or self._generate_batch_id()
        batch_dir = self.root_dir / "runs" / run_batch_id
        writer = RawResultWriter(batch_dir)
        manifest = BatchManifest(batch_id=run_batch_id, started_at=utc_now_iso())
        writer.write_manifest(manifest)

        all_results: list[SingleMultiRunResult | RouterRunResult] = []
        for task_dir in sorted(path for path in tasks_root.iterdir() if path.is_dir()):
            report = self.validate_task(task_dir)
            if not report.valid:
                manifest.aborted = True
                manifest.status = "failed"
                manifest.finished_at = utc_now_iso()
                manifest.errors.extend(report.errors)
                writer.write_manifest(manifest)
                raise ValueError("\n".join(report.errors))
            task = self.task_loader.load(task_dir)
            try:
                all_results.extend(
                    self._run_loaded_task(
                        task,
                        writer,
                        manifest,
                        strategy=_normalize_strategy(strategy),
                        repetitions_override=repetitions_override,
                        model_override=model_override,
                        cleanup_workspaces=cleanup_workspaces,
                    )
                )
            except Exception:
                manifest.aborted = True
                manifest.status = "failed"
                manifest.finished_at = utc_now_iso()
                writer.write_manifest(manifest)
                raise

        manifest.finished_at = utc_now_iso()
        manifest.status = "completed"
        writer.write_manifest(manifest)
        return all_results

    def aggregate(self, path: Path, formats: set[str] | None = None) -> dict[str, str]:
        results = collect_results(path)
        target_dir = (path if path.is_dir() else path.parent).resolve()
        if target_dir.name != "aggregated":
            target_dir = target_dir / "aggregated"
        return self.aggregate_writer.write(target_dir, results, formats or {"jsonl", "csv"})

    def _run_loaded_task(
        self,
        task: LoadedTask,
        writer: RawResultWriter,
        manifest: BatchManifest,
        strategy: StrategySelector | None,
        repetitions_override: int | None,
        model_override: str | None,
        cleanup_workspaces: bool,
    ) -> list[SingleMultiRunResult | RouterRunResult]:
        results: list[SingleMultiRunResult | RouterRunResult] = []
        for strategy_name, repetition_index in self._iter_strategy_runs(task, strategy, repetitions_override):
            run_id = self._build_run_id(task.config.id, strategy_name, repetition_index)
            workspace_handle = None
            started_at = utc_now_iso()
            started_counter = perf_counter()
            artifacts: StrategyArtifacts | None = None
            try:
                if strategy_name in {"single", "multi"}:
                    workspace_handle = create_workspace(
                        writer.batch_dir,
                        task.config.id,
                        task.input_dir,
                        strategy_name,
                        repetition_index,
                    )
                context = StrategyContext(
                    task=task,
                    workspace_path=workspace_handle.workspace_path if workspace_handle else None,
                    repetition_index=repetition_index,
                    model_override=model_override,
                )
                artifacts = self._runner_for(strategy_name).run(context)
                latency = round(perf_counter() - started_counter, 3)
                usage = build_usage_totals(
                    artifacts.model,
                    self.bundle.models_config,
                    artifacts.prompt_tokens,
                    artifacts.completion_tokens,
                    artifacts.total_tokens,
                )
                trace_file = writer.write_trace(run_id, artifacts.trace_events)
                output_file = None
                changed_files: list[str] = []
                workspace_path = None
                if strategy_name in {"single", "multi"}:
                    output_file = writer.write_output(run_id, artifacts.final_output_text or "")
                    assert workspace_handle is not None
                    workspace_path = workspace_handle.relative_workspace_path
                    changed_files = compute_changed_files(task.input_dir, workspace_handle.workspace_path)
                result_model = self._build_success_result(
                    task=task,
                    run_id=run_id,
                    batch_id=manifest.batch_id,
                    strategy_name=strategy_name,
                    repetition_index=repetition_index,
                    artifacts=artifacts,
                    started_at=started_at,
                    latency=latency,
                    usage=usage,
                    trace_file=trace_file,
                    output_file=output_file,
                    workspace_path=workspace_path,
                    changed_files=changed_files,
                )
                writer.write_raw_result(result_model)
                manifest.completed_runs.append(run_id)
                writer.write_manifest(manifest)
                results.append(result_model)
                if cleanup_workspaces and workspace_handle is not None:
                    cleanup_workspace(workspace_handle.workspace_path)
            except Exception as exc:
                latency = round(perf_counter() - started_counter, 3)
                failure_trace = artifacts.trace_events if artifacts else []
                trace_file = writer.write_trace(run_id, failure_trace)
                failure_result = self._build_failure_result(
                    task=task,
                    run_id=run_id,
                    batch_id=manifest.batch_id,
                    strategy_name=strategy_name,
                    repetition_index=repetition_index,
                    started_at=started_at,
                    latency=latency,
                    trace_file=trace_file,
                    workspace_path=workspace_handle.relative_workspace_path if workspace_handle else None,
                    error_type=_classify_error(exc),
                    error_message=str(exc),
                    model_override=model_override,
                )
                writer.write_raw_result(failure_result)
                manifest.failed_run_id = run_id
                manifest.errors.append(f"{run_id}: {exc}")
                writer.write_manifest(manifest)
                raise
        return results

    def _iter_strategy_runs(
        self,
        task: LoadedTask,
        selected_strategy: StrategySelector | None,
        repetitions_override: int | None,
    ) -> list[tuple[StrategySelector, int | None]]:
        repetitions = repetitions_override or task.config.repetitions
        runs: list[tuple[StrategySelector, int | None]] = []
        if selected_strategy is None:
            if task.config.router_strategy.enabled:
                runs.append(("router", None))
            if task.config.single_strategy.enabled:
                runs.extend(("single", index) for index in range(1, repetitions + 1))
            if task.config.multi_strategy.enabled:
                runs.extend(("multi", index) for index in range(1, repetitions + 1))
            return runs
        if selected_strategy == "router":
            return [("router", None)]
        return [(selected_strategy, index) for index in range(1, repetitions + 1)]

    def _runner_for(self, strategy_name: StrategySelector):
        if strategy_name == "single":
            return self.single_runner
        if strategy_name == "multi":
            return self.multi_runner
        return self.router_runner

    def _build_success_result(
        self,
        *,
        task: LoadedTask,
        run_id: str,
        batch_id: str,
        strategy_name: StrategySelector,
        repetition_index: int | None,
        artifacts: StrategyArtifacts,
        started_at: str,
        latency: float,
        usage,
        trace_file: str,
        output_file: str | None,
        workspace_path: str | None,
        changed_files: list[str],
    ) -> SingleMultiRunResult | RouterRunResult:
        common = dict(
            run_id=run_id,
            batch_id=batch_id,
            task_id=task.config.id,
            model=artifacts.model,
            started_at=started_at,
            finished_at=utc_now_iso(),
            latency_sec=latency,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            estimated_cost=usage.estimated_cost,
            status="completed",
            trace_file=trace_file,
            prompt_checksum=task.prompt_checksum,
            input_checksum=task.input_checksum,
            task_config_checksum=task.task_config_checksum,
            timeout_sec=task.config.timeout_sec,
            nondeterministic=task.config.nondeterministic,
            sdk_versions=self.sdk_versions,
        )
        if strategy_name == "router":
            return RouterRunResult(
                strategy="router",
                temperature=artifacts.temperature,
                route_candidates=task.config.router_strategy.route_candidates,
                selected_route=artifacts.selected_route,
                route_reason=artifacts.route_reason,
                route_confidence=artifacts.route_confidence,
                final_output_text=artifacts.final_output_text,
                **common,
            )
        return SingleMultiRunResult(
            strategy=strategy_name,
            repetition_index=repetition_index or 1,
            temperature=artifacts.temperature,
            allowed_tools=task.config.allowed_tools,
            tool_calls_count=len(artifacts.tool_calls),
            tool_calls=artifacts.tool_calls,
            agent_steps=artifacts.agent_steps,
            final_output_text=artifacts.final_output_text,
            final_output_file=output_file,
            workspace_path=workspace_path,
            changed_files=changed_files,
            **common,
        )

    def _build_failure_result(
        self,
        *,
        task: LoadedTask,
        run_id: str,
        batch_id: str,
        strategy_name: StrategySelector,
        repetition_index: int | None,
        started_at: str,
        latency: float,
        trace_file: str,
        workspace_path: str | None,
        error_type: str,
        error_message: str,
        model_override: str | None,
    ) -> SingleMultiRunResult | RouterRunResult:
        if strategy_name == "single":
            model = model_override or task.config.single_strategy.model
            temperature = task.config.single_strategy.temperature
        elif strategy_name == "multi":
            model = model_override or task.config.multi_strategy.model
            temperature = task.config.multi_strategy.temperature
        else:
            model = model_override or task.config.router_strategy.model
            temperature = task.config.router_strategy.temperature

        common = dict(
            run_id=run_id,
            batch_id=batch_id,
            task_id=task.config.id,
            model=model,
            started_at=started_at,
            finished_at=utc_now_iso(),
            latency_sec=latency,
            status="failed",
            error_type=error_type,
            error_message=error_message,
            trace_file=trace_file,
            prompt_checksum=task.prompt_checksum,
            input_checksum=task.input_checksum,
            task_config_checksum=task.task_config_checksum,
            timeout_sec=task.config.timeout_sec,
            nondeterministic=task.config.nondeterministic,
            sdk_versions=self.sdk_versions,
        )
        if strategy_name == "router":
            return RouterRunResult(
                strategy="router",
                temperature=temperature,
                route_candidates=task.config.router_strategy.route_candidates,
                **common,
            )
        return SingleMultiRunResult(
            strategy=strategy_name,
            repetition_index=repetition_index or 1,
            temperature=temperature,
            allowed_tools=task.config.allowed_tools,
            workspace_path=workspace_path,
            **common,
        )

    def _build_run_id(self, task_id: str, strategy_name: StrategySelector, repetition_index: int | None) -> str:
        if strategy_name == "router":
            return f"{task_id}__router"
        return f"{task_id}__{strategy_name}__rep{repetition_index}"

    def _generate_batch_id(self) -> str:
        return utc_now_iso().replace(":", "-").replace("+00:00", "Z")
