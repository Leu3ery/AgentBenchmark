from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from agent_benchmark.benchmark import BenchmarkService, StrategyName

app = typer.Typer(help="Agent benchmark CLI")


def _service() -> BenchmarkService:
    return BenchmarkService(Path.cwd())


@app.command()
def validate(task_dir: Annotated[Path, typer.Argument(help="Path to a single task directory")]) -> None:
    service = _service()
    report = service.validate_task(task_dir)
    if report.valid:
        typer.echo(f"VALID: {task_dir}")
        for warning in report.warnings:
            typer.echo(f"warning: {warning}")
        return
    for error in report.errors:
        typer.echo(f"error: {error}")
    raise typer.Exit(code=1)


@app.command("run")
def run_task(
    task_dir: Annotated[Path, typer.Argument(help="Path to a single task directory")],
    strategy: Annotated[StrategyName | None, typer.Option("--strategy", help="single, multi, or router")] = None,
    repetitions: Annotated[int | None, typer.Option("--repetitions")] = None,
    model: Annotated[str | None, typer.Option("--model")] = None,
    batch_id: Annotated[str | None, typer.Option("--batch-id")] = None,
    cleanup_workspaces: Annotated[bool, typer.Option("--cleanup-workspaces")] = False,
) -> None:
    service = _service()
    try:
        results = service.run_task(
            task_dir,
            strategy=strategy,
            repetitions_override=repetitions,
            model_override=model,
            batch_id=batch_id,
            cleanup_workspaces=cleanup_workspaces,
        )
    except Exception as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    typer.echo(f"Completed {len(results)} run(s).")


@app.command("run-all")
def run_all(
    tasks_root: Annotated[Path, typer.Argument(help="Root directory that contains task folders")],
    strategy: Annotated[StrategyName | None, typer.Option("--strategy")] = None,
    repetitions: Annotated[int | None, typer.Option("--repetitions")] = None,
    model: Annotated[str | None, typer.Option("--model")] = None,
    batch_id: Annotated[str | None, typer.Option("--batch-id")] = None,
    cleanup_workspaces: Annotated[bool, typer.Option("--cleanup-workspaces")] = False,
) -> None:
    service = _service()
    try:
        results = service.run_all(
            tasks_root,
            strategy=strategy,
            repetitions_override=repetitions,
            model_override=model,
            batch_id=batch_id,
            cleanup_workspaces=cleanup_workspaces,
        )
    except Exception as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    typer.echo(f"Completed {len(results)} run(s).")


@app.command()
def aggregate(
    path: Annotated[Path, typer.Argument(help="runs/ root or a concrete batch directory")],
    format: Annotated[list[str], typer.Option("--format", help="csv, jsonl, parquet")] = ["jsonl", "csv"],
) -> None:
    service = _service()
    try:
        written = service.aggregate(path, set(format))
    except Exception as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    for fmt, output_path in written.items():
        typer.echo(f"{fmt}: {output_path}")
