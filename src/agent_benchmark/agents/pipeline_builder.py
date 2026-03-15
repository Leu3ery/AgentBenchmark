from __future__ import annotations

from agent_benchmark.config.schemas import MultiAgentConfig, TaskConfig


def build_pipeline_agents(task_config: TaskConfig) -> list[MultiAgentConfig]:
    agents_by_id = {agent.id: agent for agent in task_config.multi_strategy.architecture.agents}
    return [agents_by_id[agent_id] for agent_id in task_config.multi_strategy.architecture.flow]
