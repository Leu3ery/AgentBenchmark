from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
import yaml

from agent_benchmark.config.loader import ConfigLoader
from agent_benchmark.config.schemas import ValidationReport


def validate_task_dir(task_dir: Path, config_loader: ConfigLoader) -> ValidationReport:
    task_dir = task_dir.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for required in ("task.yaml", "prompt.md", "input", "evaluation"):
        required_path = task_dir / required
        if not required_path.exists():
            errors.append(f"Missing required path: {required_path}")

    if errors:
        return ValidationReport(task_dir=task_dir, valid=False, errors=errors, warnings=warnings)

    raw_task_data = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8")) or {}
    bundle = config_loader.load_bundle()
    registered_tools = set(bundle.tools_config.tools)
    raw_allowed_tools = set(raw_task_data.get("allowed_tools", []))
    unknown_raw_tools = sorted(raw_allowed_tools - registered_tools)
    if unknown_raw_tools:
        errors.append(f"Unknown allowed_tools: {', '.join(unknown_raw_tools)}")

    raw_agents = (
        raw_task_data.get("multi_strategy", {})
        .get("architecture", {})
        .get("agents", [])
    )
    for agent in raw_agents:
        raw_agent_tools = set(agent.get("allowed_tools", []))
        unknown_agent_tools = sorted(raw_agent_tools - registered_tools)
        if unknown_agent_tools:
            errors.append(
                f"Agent '{agent.get('id', '<unknown>')}' references unknown tools: "
                f"{', '.join(unknown_agent_tools)}"
            )

    try:
        config = config_loader.load_task_config(task_dir)
    except ValidationError as exc:
        errors.extend(error["msg"] for error in exc.errors())
        return ValidationReport(task_dir=task_dir, valid=False, errors=errors, warnings=warnings)

    unknown_tools = sorted(set(config.allowed_tools) - registered_tools)
    if unknown_tools:
        errors.append(f"Unknown allowed_tools: {', '.join(unknown_tools)}")

    flow = config.multi_strategy.architecture.flow
    agent_ids = {agent.id for agent in config.multi_strategy.architecture.agents}
    if flow and flow[-1] not in agent_ids:
        errors.append("Last multi-agent flow entry must reference a defined agent.")

    prompt_path = task_dir / config.prompt_file
    input_path = task_dir / config.input_dir
    evaluation_path = task_dir / config.evaluation_dir
    if not prompt_path.exists():
        errors.append(f"Configured prompt_file does not exist: {prompt_path}")
    if not input_path.exists():
        errors.append(f"Configured input_dir does not exist: {input_path}")
    if not evaluation_path.exists():
        errors.append(f"Configured evaluation_dir does not exist: {evaluation_path}")

    for agent in config.multi_strategy.architecture.agents:
        invalid_agent_tools = sorted(set(agent.allowed_tools) - set(config.allowed_tools))
        if invalid_agent_tools:
            errors.append(
                f"Agent '{agent.id}' uses tools not listed in task.allowed_tools: "
                f"{', '.join(invalid_agent_tools)}"
            )

    if config.nondeterministic:
        warnings.append("Task is marked as nondeterministic; reproduce results with caution.")

    return ValidationReport(task_dir=task_dir, valid=not errors, errors=errors, warnings=warnings)
