from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from agents import RunHooks
from pydantic import BaseModel

from agent_benchmark.storage.models import AgentStepRecord, ToolCallRecord


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _serialize(value: Any, max_chars: int = 4_000) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if isinstance(value, (dict, list, tuple)):
        rendered = json.dumps(value, ensure_ascii=True, default=str)
    else:
        rendered = str(value)
    if len(rendered) > max_chars:
        return rendered[:max_chars] + "...<truncated>"
    return rendered


class TraceCollector(RunHooks):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []
        self.tool_calls: list[ToolCallRecord] = []
        self.agent_steps: list[AgentStepRecord] = []
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.response_ids: list[str] = []

    def _append_step(self, agent_id: str | None, event_type: str, message: str | None = None, **payload: Any) -> None:
        timestamp = _timestamp()
        event = {
            "timestamp": timestamp,
            "agent_id": agent_id,
            "event_type": event_type,
            "message": message,
            "payload": payload,
        }
        self.events.append(event)
        self.agent_steps.append(
            AgentStepRecord(
                agent_id=agent_id,
                event_type=event_type,
                timestamp=timestamp,
                message=message,
                payload={key: value for key, value in payload.items() if value is not None},
            )
        )

    def on_agent_start(self, context, agent) -> None:  # type: ignore[override]
        self._append_step(agent.name, "agent_start", message=f"Agent {agent.name} started")

    def on_agent_end(self, context, agent, output) -> None:  # type: ignore[override]
        self._append_step(
            agent.name,
            "agent_end",
            message=f"Agent {agent.name} completed",
            output_preview=_serialize(output, max_chars=1_000),
        )

    def on_handoff(self, context, from_agent, to_agent) -> None:  # type: ignore[override]
        self._append_step(
            from_agent.name,
            "handoff",
            message=f"Handoff from {from_agent.name} to {to_agent.name}",
            to_agent=to_agent.name,
        )

    def on_llm_start(self, context, agent, system_prompt, input_items) -> None:  # type: ignore[override]
        self._append_step(
            agent.name,
            "llm_start",
            prompt_preview=_serialize(system_prompt, max_chars=1_000),
            input_items_count=len(input_items),
        )

    def on_llm_end(self, context, agent, response) -> None:  # type: ignore[override]
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.prompt_tokens += getattr(usage, "input_tokens", 0)
            self.completion_tokens += getattr(usage, "output_tokens", 0)
            self.total_tokens += getattr(usage, "total_tokens", 0)
        response_id = getattr(response, "response_id", None)
        if response_id:
            self.response_ids.append(response_id)
        self._append_step(
            agent.name,
            "llm_end",
            response_id=response_id,
            usage={
                "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
                "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
            },
        )

    def on_tool_start(self, context, agent, tool) -> None:  # type: ignore[override]
        tool_input = getattr(context, "tool_input", None)
        call = ToolCallRecord(
            agent_id=agent.name,
            tool_name=getattr(tool, "name", tool.__class__.__name__),
            tool_input=_serialize(tool_input, max_chars=1_500),
            started_at=_timestamp(),
            status="started",
        )
        self.tool_calls.append(call)
        self._append_step(
            agent.name,
            "tool_start",
            message=f"Tool {call.tool_name} started",
            tool_name=call.tool_name,
            tool_input=call.tool_input,
        )

    def on_tool_end(self, context, agent, tool, result) -> None:  # type: ignore[override]
        tool_name = getattr(tool, "name", tool.__class__.__name__)
        for call in reversed(self.tool_calls):
            if call.tool_name == tool_name and call.agent_id == agent.name and call.finished_at is None:
                call.finished_at = _timestamp()
                call.status = "completed"
                call.result_preview = _serialize(result, max_chars=1_500)
                break
        self._append_step(
            agent.name,
            "tool_end",
            message=f"Tool {tool_name} completed",
            tool_name=tool_name,
            result_preview=_serialize(result, max_chars=1_000),
        )
