from __future__ import annotations

from dotenv import load_dotenv

from agent_benchmark.cli import app


def main() -> int:
    load_dotenv()
    app()
    return 0
