from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class GlobalConfig(BaseModel):
    default_timeout_sec: int = 600
    default_repetitions: int = 1
    default_batch_prefix: str = "batch"


class ModelPricing(BaseModel):
    prompt_cost_per_1m: float = 0.0
    completion_cost_per_1m: float = 0.0
    notes: str | None = None


class ModelsConfig(BaseModel):
    default_model: str | None = None
    router_model: str | None = None
    models: dict[str, ModelPricing] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_defaults(self) -> "ModelsConfig":
        if not self.models:
            return self
        if self.default_model is None and len(self.models) == 1:
            self.default_model = next(iter(self.models))
        if self.default_model and self.default_model not in self.models:
            raise ValueError(f"default_model '{self.default_model}' is not declared in models")
        if self.router_model and self.router_model not in self.models:
            raise ValueError(f"router_model '{self.router_model}' is not declared in models")
        if self.router_model is None:
            self.router_model = self.default_model
        return self


class ToolSpec(BaseModel):
    id: str
    description: str
    provider: Literal["custom", "openai", "langchain", "deep_agents"] = "custom"
    supports_workspace: bool = True
    nondeterministic: bool = False


class ToolsConfig(BaseModel):
    tools: dict[str, ToolSpec] = Field(default_factory=dict)


class SingleStrategyConfig(BaseModel):
    enabled: bool = True
    model: str
    temperature: float = 0.2
    max_steps: int = 20


class MultiAgentConfig(BaseModel):
    id: str
    role: str
    allowed_tools: list[str] = Field(default_factory=list)


class MultiArchitectureConfig(BaseModel):
    type: Literal["pipeline"] = "pipeline"
    agents: list[MultiAgentConfig]
    flow: list[str]

    @field_validator("agents")
    @classmethod
    def validate_unique_agent_ids(cls, agents: list[MultiAgentConfig]) -> list[MultiAgentConfig]:
        ids = [agent.id for agent in agents]
        if len(ids) != len(set(ids)):
            raise ValueError("Multi-agent architecture contains duplicate agent ids.")
        return agents


class MultiStrategyConfig(BaseModel):
    enabled: bool = True
    model: str
    temperature: float = 0.2
    max_steps: int = 20
    architecture: MultiArchitectureConfig


class RouterStrategyConfig(BaseModel):
    enabled: bool = True
    model: str
    temperature: float = 0.0
    max_steps: int = 5
    route_candidates: list[str]

    @field_validator("route_candidates")
    @classmethod
    def validate_route_candidates(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("router_strategy.route_candidates must not be empty")
        return value


class TaskConfig(BaseModel):
    id: str
    name: str
    category: str
    description: str
    repetitions: int = 1
    timeout_sec: int = 600
    input_dir: str = "input"
    evaluation_dir: str = "evaluation"
    prompt_file: str = "prompt.md"
    nondeterministic: bool = False
    allowed_tools: list[str] = Field(default_factory=list)
    single_strategy: SingleStrategyConfig
    multi_strategy: MultiStrategyConfig
    router_strategy: RouterStrategyConfig

    @field_validator("repetitions", "timeout_sec")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be greater than 0.")
        return value

    @model_validator(mode="after")
    def validate_strategy_tools(self) -> "TaskConfig":
        task_tools = set(self.allowed_tools)
        pipeline_tools = {
            tool_id
            for agent in self.multi_strategy.architecture.agents
            for tool_id in agent.allowed_tools
        }
        missing = sorted(pipeline_tools - task_tools)
        if missing:
            raise ValueError(
                f"multi_strategy references tools not present in allowed_tools: {', '.join(missing)}"
            )

        agent_ids = {agent.id for agent in self.multi_strategy.architecture.agents}
        flow_unknown = [agent_id for agent_id in self.multi_strategy.architecture.flow if agent_id not in agent_ids]
        if flow_unknown:
            raise ValueError(
                f"multi_strategy.architecture.flow references unknown agents: {', '.join(flow_unknown)}"
            )
        return self


class LoadedTask(BaseModel):
    root_dir: Path
    prompt_text: str
    config: TaskConfig
    input_dir: Path
    evaluation_dir: Path
    prompt_path: Path
    prompt_checksum: str
    input_checksum: str
    task_config_checksum: str

    model_config = {"arbitrary_types_allowed": True}


class ValidationReport(BaseModel):
    task_dir: Path
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class ConfigBundle(BaseModel):
    root_dir: Path
    global_config: GlobalConfig = Field(default_factory=GlobalConfig)
    models_config: ModelsConfig = Field(default_factory=ModelsConfig)
    tools_config: ToolsConfig = Field(default_factory=ToolsConfig)

    model_config = {"arbitrary_types_allowed": True}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
