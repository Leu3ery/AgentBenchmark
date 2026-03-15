from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from agents import Runner
from pydantic import BaseModel

from agent_benchmark.agents.factory import build_agent
from agent_benchmark.execution.tracing import TraceCollector


@dataclass(slots=True)
class AgentExecutionSpec:
    name: str
    instructions: str
    input_text: str
    model: str
    temperature: float
    max_turns: int
    timeout_sec: int
    tools: list[Any] = field(default_factory=list)
    output_type: type[Any] | None = None


@dataclass(slots=True)
class AgentExecutionResult:
    final_output: Any
    final_output_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_calls: list[dict[str, Any]]
    agent_steps: list[dict[str, Any]]
    trace_events: list[dict[str, Any]]
    response_ids: list[str]


class AgentExecutor(Protocol):
    def run_agent(self, spec: AgentExecutionSpec) -> AgentExecutionResult:
        ...


def _stringify_output(output: Any) -> str:
    if output is None:
        return ""
    if isinstance(output, BaseModel):
        return output.model_dump_json(indent=2)
    if isinstance(output, (dict, list, tuple)):
        return json.dumps(output, indent=2, ensure_ascii=True, default=str)
    return str(output)


class OpenAIAgentExecutor:
    def run_agent(self, spec: AgentExecutionSpec) -> AgentExecutionResult:
        collector = TraceCollector()
        agent = build_agent(
            name=spec.name,
            instructions=spec.instructions,
            model=spec.model,
            temperature=spec.temperature,
            tools=spec.tools,
            output_type=spec.output_type,
        )

        async def _run() -> Any:
            return await asyncio.wait_for(
                Runner.run(
                    agent,
                    spec.input_text,
                    max_turns=spec.max_turns,
                    hooks=collector,
                ),
                timeout=spec.timeout_sec,
            )

        result = asyncio.run(_run())
        final_output_text = _stringify_output(result.final_output)
        return AgentExecutionResult(
            final_output=result.final_output,
            final_output_text=final_output_text,
            prompt_tokens=collector.prompt_tokens,
            completion_tokens=collector.completion_tokens,
            total_tokens=collector.total_tokens,
            tool_calls=[record.model_dump(mode="json") for record in collector.tool_calls],
            agent_steps=[record.model_dump(mode="json") for record in collector.agent_steps],
            trace_events=collector.events,
            response_ids=collector.response_ids,
        )
