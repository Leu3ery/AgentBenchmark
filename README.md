# Agent Benchmark

Local CLI benchmark harness for comparing `single-agent`, `multi-agent`, and `router-only` strategies over folder-based tasks.

## What This Project Does

The benchmark reads tasks from folders under `tasks/`, runs one or more strategies against each task, and stores:

- raw run results as JSON
- final text outputs
- normalized traces
- per-run metadata such as tokens, latency, cost, changed files, and manual evaluation fields

It is designed for research and comparison workflows, not as a production agent framework.

![Compact strategy comparison](docs/images/benchmark-results/strategy-comparison-compact.svg)

## Features

- `single` strategy: one agent solves the task
- `multi` strategy: fixed pipeline of agents defined in `task.yaml`
- `router` strategy: model classifies which route it would choose without solving the task
- isolated workspace per run
- repeated runs for `single` and `multi`
- aggregation into `csv` and `jsonl`
- starter task fixtures for coding, data analysis, document QA, web research, and fake email workflows

## Project Layout

```text
agent-benchmark/
├── configs/
│   ├── global.yaml
│   ├── models.yaml
│   └── tools.yaml
├── tasks/
├── runs/
├── src/
└── tests/
```

## Setup

Create a virtual environment, install dependencies, and install the package in editable mode:

```bash
cd /Users/leuzery/Desktop/projects/papaer
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## API Key

The CLI loads environment variables from a local `.env` file automatically.

Example:

```bash
echo 'OPENAI_API_KEY=your_key_here' > .env
chmod 600 .env
```

## Quick Start

Validate one task:

```bash
benchmark validate tasks/task_001_bugfix_csv
```

Run one task with all enabled strategies:

```bash
benchmark run tasks/task_001_bugfix_csv --batch-id first_run
```

Run only one strategy:

```bash
benchmark run tasks/task_001_bugfix_csv --strategy single --batch-id single_smoke
benchmark run tasks/task_001_bugfix_csv --strategy multi --batch-id multi_smoke
benchmark run tasks/task_001_bugfix_csv --strategy router --batch-id router_smoke
```

Run all tasks:

```bash
benchmark run-all tasks --batch-id full_benchmark
```

Aggregate results:

```bash
benchmark aggregate runs
benchmark aggregate runs/full_benchmark
```

## CLI Commands

### `benchmark validate`

Validate one task directory:

```bash
benchmark validate tasks/task_001_bugfix_csv
```

Checks include:

- required files and folders exist
- `task.yaml` matches the schema
- referenced tools exist in `configs/tools.yaml`
- multi-agent pipeline ids and flow are valid

### `benchmark run`

Run one task:

```bash
benchmark run tasks/task_001_bugfix_csv
```

Useful options:

```bash
benchmark run tasks/task_001_bugfix_csv --strategy single
benchmark run tasks/task_001_bugfix_csv --repetitions 5
benchmark run tasks/task_001_bugfix_csv --model gpt-5-mini
benchmark run tasks/task_001_bugfix_csv --cleanup-workspaces
benchmark run tasks/task_001_bugfix_csv --batch-id my_batch
```

Notes:

- `router` runs once per task
- `single` and `multi` run `repetitions` times
- `--repetitions` only affects `single` and `multi`
- `--model` overrides the resolved model for the selected run

### `benchmark run-all`

Run all task directories under `tasks/`:

```bash
benchmark run-all tasks
```

This command is fail-fast: it stops on the first failed run, but it still writes the failed raw result and updates the batch manifest.

### `benchmark aggregate`

Collect raw results and export aggregate files:

```bash
benchmark aggregate runs
benchmark aggregate runs/2026-03-15T12-00-00Z
benchmark aggregate runs --format jsonl --format csv
```

Supported formats:

- `jsonl`
- `csv`
- `parquet` if the parquet dependency is installed

## Task Format

Each task lives in its own directory:

```text
tasks/<task_id>/
├── task.yaml
├── prompt.md
├── input/
└── evaluation/
```

### `prompt.md`

The main task prompt shown to the agent.

### `input/`

All files the agent is allowed to use. This folder is copied into a fresh workspace for each run.

### `evaluation/`

Hidden evaluation materials for human review only. These files are never copied into the agent workspace.

### `task.yaml`

Defines:

- task metadata
- repetitions and timeout
- allowed tools
- `single`, `multi`, and `router` strategy config
- fixed pipeline structure for `multi`

## Models

Models are resolved from `configs/models.yaml`.

Current behavior:

- `default_model` is used for `single` and `multi`
- `router_model` is used for `router`
- individual `task.yaml` files do not need to hardcode model ids
- `--model` on the CLI overrides the resolved model at runtime

Example:

```yaml
default_model: gpt-5-mini
router_model: gpt-5-mini
models:
  gpt-5-mini:
    prompt_cost_per_1m: 0.25
    completion_cost_per_1m: 2.00
```

## Tools

Tool definitions are registered in `configs/tools.yaml`.

The project currently supports:

- coding tools: `list_files`, `read_file`, `search_in_files`, `write_file`, `run_tests`, `terminal`
- data analysis tools: `python`, `read_file`, `write_file`
- web tools: `web_search`, `open_url`
- fake email tools: `list_emails`, `get_email`, `send_reply`

For local benchmark safety, workspace-bound tools are implemented as thin custom wrappers restricted to the run workspace.

## Output Structure

Each batch is written under `runs/<batch_id>/`.

The top-level `runs/` directory is tracked in git so benchmark artifacts, batch manifests, and aggregate exports can be shared and compared across commits.

Typical structure:

```text
runs/<batch_id>/
├── raw/
├── outputs/
├── traces/
├── workspaces/
├── aggregated/
└── batch_manifest.json
```

### `raw/`

One JSON file per run:

- `task_001_bugfix_csv__single__rep1.json`
- `task_001_bugfix_csv__multi__rep1.json`
- `task_001_bugfix_csv__router.json`

### `outputs/`

Text output per run.

### `traces/`

Normalized trace JSON with lifecycle events, tool calls, and usage snapshots.

### `workspaces/`

Copied `input/` workspaces for each run. These are kept by default for debugging and reproducibility.

## Manual Evaluation

The benchmark does not auto-grade results in v1.

Instead, each raw JSON contains empty manual evaluation fields:

- for `single` and `multi`: overall score, correctness, completeness, efficiency, pass/fail, notes
- for `router`: overall score, route quality, and notes

![Policy summary and router choices](docs/images/benchmark-results/policy-summary-router-decisions.svg)

The source of truth for manual evaluation is the raw JSON, not the aggregated CSV.

![Run-level variability](docs/images/benchmark-results/run-level-variability.svg)

## Recommended First Run

If you want the cheapest reasonable smoke test:

```bash
benchmark validate tasks/task_001_bugfix_csv
benchmark run tasks/task_001_bugfix_csv --strategy router --batch-id smoke_router
benchmark run tasks/task_001_bugfix_csv --strategy single --batch-id smoke_single
benchmark aggregate runs
```

## Tests

Run the test suite with:

```bash
.venv/bin/python -m pytest -q
```

## Current Limitations

- no automatic judge model
- no dynamic multi-agent graph construction
- no distributed execution
- no browser automation
- live web research tasks are nondeterministic by design
