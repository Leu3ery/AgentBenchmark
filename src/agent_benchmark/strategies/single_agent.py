from __future__ import annotations

from agent_benchmark.agents.tools import ToolBuildContext, ToolRegistry
from agent_benchmark.execution.openai_client import AgentExecutionSpec, AgentExecutor
from agent_benchmark.strategies.base import BaseStrategyRunner, StrategyArtifacts, StrategyContext


class SingleAgentStrategyRunner(BaseStrategyRunner):
    strategy_name = "single"

    def __init__(self, executor: AgentExecutor, tool_registry: ToolRegistry) -> None:
        self.executor = executor
        self.tool_registry = tool_registry

    def run(self, context: StrategyContext) -> StrategyArtifacts:
        task = context.task
        config = task.config.single_strategy
        model = context.model_override or config.model
        tools = self.tool_registry.build_tools(
            task.config.allowed_tools,
            ToolBuildContext(task_id=task.config.id, workspace_path=context.workspace_path),
        )
        instructions = (
            "You are running inside a benchmark workspace. "
            "Solve the task using only the provided tools and files inside the workspace. "
            "Do not assume access to evaluation files. Return a concise final summary."
        )
        execution = self.executor.run_agent(
            AgentExecutionSpec(
                name=f"{task.config.id}-single",
                instructions=instructions,
                input_text=task.prompt_text,
                model=model,
                temperature=config.temperature,
                max_turns=config.max_steps,
                timeout_sec=task.config.timeout_sec,
                tools=tools,
            )
        )
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
        )
