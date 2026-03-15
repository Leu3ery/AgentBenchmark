from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class UsageTotals(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


class ToolCallRecord(BaseModel):
    agent_id: str | None = None
    tool_name: str
    tool_input: Any = None
    result_preview: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    status: Literal["started", "completed", "failed"] = "completed"


class AgentStepRecord(BaseModel):
    agent_id: str | None = None
    event_type: str
    timestamp: str
    message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class SingleMultiManualEval(BaseModel):
    filled_by_user: bool = False
    score_overall: float | None = None
    score_correctness: float | None = None
    score_completeness: float | None = None
    score_efficiency: float | None = None
    score_notes: str | None = None
    pass_fail: bool | None = None


class RouterManualEval(BaseModel):
    filled_by_user: bool = False
    route_was_good_choice: bool | None = None
    score_notes: str | None = None


class BaseRunResult(BaseModel):
    run_id: str
    batch_id: str
    task_id: str
    strategy: Literal["single", "multi", "router"]
    model: str
    started_at: str
    finished_at: str
    latency_sec: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    status: Literal["completed", "failed"] = "completed"
    error_type: str | None = None
    error_message: str | None = None
    trace_file: str | None = None
    prompt_checksum: str
    input_checksum: str
    task_config_checksum: str
    timeout_sec: int
    nondeterministic: bool = False
    sdk_versions: dict[str, str] = Field(default_factory=dict)


class SingleMultiRunResult(BaseRunResult):
    strategy: Literal["single", "multi"]
    repetition_index: int
    temperature: float
    allowed_tools: list[str] = Field(default_factory=list)
    tool_calls_count: int = 0
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    agent_steps: list[AgentStepRecord] = Field(default_factory=list)
    final_output_text: str | None = None
    final_output_file: str | None = None
    workspace_path: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    manual_eval: SingleMultiManualEval = Field(default_factory=SingleMultiManualEval)


class RouterRunResult(BaseRunResult):
    strategy: Literal["router"] = "router"
    temperature: float = 0.0
    route_candidates: list[str] = Field(default_factory=list)
    selected_route: str | None = None
    route_reason: str | None = None
    route_confidence: float | None = None
    final_output_text: str | None = None
    manual_eval: RouterManualEval = Field(default_factory=RouterManualEval)


class BatchManifest(BaseModel):
    batch_id: str
    started_at: str
    finished_at: str | None = None
    completed_runs: list[str] = Field(default_factory=list)
    failed_run_id: str | None = None
    aborted: bool = False
    status: Literal["running", "completed", "failed"] = "running"
    errors: list[str] = Field(default_factory=list)


class AggregatedRow(BaseModel):
    task_id: str
    strategy: str
    repetition_index: int | None = None
    batch_id: str
    model: str
    latency_sec: float
    total_tokens: int
    estimated_cost: float
    status: str
    error_type: str | None = None
    error_message: str | None = None
    final_output_path: str | None = None
    workspace_path: str | None = None
    selected_route: str | None = None
    route_confidence: float | None = None
    manual_score_overall: float | None = None
    manual_pass_fail: bool | None = None
    manual_route_was_good_choice: bool | None = None
    notes: str | None = None
