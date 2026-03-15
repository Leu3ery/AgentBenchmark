from __future__ import annotations

from pydantic import BaseModel

from agent_benchmark.execution.openai_client import AgentExecutionSpec, AgentExecutor
from agent_benchmark.strategies.base import BaseStrategyRunner, StrategyArtifacts, StrategyContext


class RouterDecision(BaseModel):
    selected_route: str
    reason: str
    confidence: float | None = None


class RouterStrategyRunner(BaseStrategyRunner):
    strategy_name = "router"

    def __init__(self, executor: AgentExecutor) -> None:
        self.executor = executor

    def run(self, context: StrategyContext) -> StrategyArtifacts:
        task = context.task
        config = task.config.router_strategy
        model = context.model_override or config.model
        router_prompt = (
            "You are a router-only classifier for benchmark tasks.\n"
            "You do not solve the task. Pick the best route candidate, explain the choice briefly, "
            "and provide a confidence score when possible.\n\n"
            f"Task metadata:\n"
            f"- id: {task.config.id}\n"
            f"- name: {task.config.name}\n"
            f"- category: {task.config.category}\n"
            f"- description: {task.config.description}\n"
            f"- nondeterministic: {task.config.nondeterministic}\n"
            f"- route candidates: {', '.join(config.route_candidates)}\n\n"
            f"Task prompt:\n{task.prompt_text}"
        )
        execution = self.executor.run_agent(
            AgentExecutionSpec(
                name=f"{task.config.id}-router",
                instructions="Return only the structured router decision.",
                input_text=router_prompt,
                model=model,
                temperature=config.temperature,
                max_turns=config.max_steps,
                timeout_sec=task.config.timeout_sec,
                tools=[],
                output_type=RouterDecision,
            )
        )
        decision = execution.final_output
        assert isinstance(decision, RouterDecision)
        return StrategyArtifacts(
            model=model,
            temperature=config.temperature,
            final_output_text=execution.final_output_text,
            prompt_tokens=execution.prompt_tokens,
            completion_tokens=execution.completion_tokens,
            total_tokens=execution.total_tokens,
            tool_calls=execution.tool_calls,
            agent_steps=execution.agent_steps,
            trace_events=execution.trace_events,
            selected_route=decision.selected_route,
            route_reason=decision.reason,
            route_confidence=decision.confidence,
        )
