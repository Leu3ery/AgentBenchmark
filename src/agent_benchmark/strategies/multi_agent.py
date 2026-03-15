from __future__ import annotations

from agent_benchmark.agents.pipeline_builder import build_pipeline_agents
from agent_benchmark.agents.tools import ToolBuildContext, ToolRegistry
from agent_benchmark.execution.openai_client import AgentExecutionSpec, AgentExecutor
from agent_benchmark.strategies.base import BaseStrategyRunner, StrategyArtifacts, StrategyContext


class MultiAgentStrategyRunner(BaseStrategyRunner):
    strategy_name = "multi"

    def __init__(self, executor: AgentExecutor, tool_registry: ToolRegistry) -> None:
        self.executor = executor
        self.tool_registry = tool_registry

    def run(self, context: StrategyContext) -> StrategyArtifacts:
        task = context.task
        config = task.config.multi_strategy
        model = context.model_override or config.model
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        tool_calls: list[dict] = []
        agent_steps: list[dict] = []
        trace_events: list[dict] = []
        latest_output = ""
        latest_summary = "No previous agent output."
        changed_files_summary = "Unknown before execution."

        for pipeline_agent in build_pipeline_agents(task.config):
            tools = self.tool_registry.build_tools(
                pipeline_agent.allowed_tools,
                ToolBuildContext(task_id=task.config.id, workspace_path=context.workspace_path),
            )
            instructions = (
                f"You are agent '{pipeline_agent.id}' in a fixed benchmark pipeline.\n"
                f"Role: {pipeline_agent.role}\n"
                "Operate only inside the workspace and do not mention hidden evaluation materials.\n"
                "Leave a concise output that the next agent can use."
            )
            prompt = (
                f"Task prompt:\n{task.prompt_text}\n\n"
                f"Previous agent summary:\n{latest_summary}\n\n"
                f"Previous agent output:\n{latest_output}\n\n"
                f"Changed files so far:\n{changed_files_summary}\n"
            )
            execution = self.executor.run_agent(
                AgentExecutionSpec(
                    name=pipeline_agent.id,
                    instructions=instructions,
                    input_text=prompt,
                    model=model,
                    temperature=config.temperature,
                    max_turns=config.max_steps,
                    timeout_sec=task.config.timeout_sec,
                    tools=tools,
                )
            )
            latest_output = execution.final_output_text
            latest_summary = execution.final_output_text[:1000]
            total_prompt_tokens += execution.prompt_tokens
            total_completion_tokens += execution.completion_tokens
            total_tokens += execution.total_tokens
            tool_calls.extend(execution.tool_calls)
            agent_steps.extend(execution.agent_steps)
            trace_events.extend(execution.trace_events)
            if context.workspace_path is not None:
                changed_files_summary = ", ".join(
                    sorted(path.as_posix() for path in context.workspace_path.rglob("*") if path.is_file())
                )[:2000]

        return StrategyArtifacts(
            model=model,
            temperature=config.temperature,
            final_output_text=latest_output,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            tool_calls=tool_calls,
            agent_steps=agent_steps,
            trace_events=trace_events,
        )
