from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import httpx
from agents import WebSearchTool, function_tool

from agent_benchmark.config.schemas import ToolSpec


@dataclass(slots=True)
class ToolBuildContext:
    task_id: str
    workspace_path: Path | None


def _default_tool_specs() -> dict[str, ToolSpec]:
    specs = {
        "list_files": ToolSpec(id="list_files", description="List files in the current workspace."),
        "read_file": ToolSpec(id="read_file", description="Read a text file from the workspace."),
        "search_in_files": ToolSpec(
            id="search_in_files", description="Search for a text pattern in workspace files."
        ),
        "write_file": ToolSpec(id="write_file", description="Write or append a text file in the workspace."),
        "run_tests": ToolSpec(id="run_tests", description="Run the task test command in the workspace."),
        "terminal": ToolSpec(id="terminal", description="Execute a shell command in the workspace."),
        "execute_shell": ToolSpec(id="execute_shell", description="Execute a shell command in the workspace."),
        "python": ToolSpec(id="python", description="Execute Python code in the workspace."),
        "web_search": ToolSpec(
            id="web_search",
            description="Run a live web search.",
            provider="openai",
            supports_workspace=False,
            nondeterministic=True,
        ),
        "open_url": ToolSpec(
            id="open_url",
            description="Fetch and read a web page.",
            provider="custom",
            supports_workspace=False,
            nondeterministic=True,
        ),
        "list_emails": ToolSpec(id="list_emails", description="List fake inbox emails for the task."),
        "get_email": ToolSpec(id="get_email", description="Read one fake inbox email."),
        "send_reply": ToolSpec(id="send_reply", description="Write a fake email reply artifact."),
    }
    return specs


def _resolve_workspace_path(workspace_path: Path, user_path: str) -> Path:
    resolved = (workspace_path / user_path).resolve()
    workspace_root = workspace_path.resolve()
    if workspace_root not in resolved.parents and resolved != workspace_root:
        raise ValueError("Path escapes the benchmark workspace.")
    return resolved


def _read_email_store(workspace_path: Path) -> list[dict[str, Any]]:
    candidates = [workspace_path / "emails" / "inbox.json", workspace_path / "inbox.json"]
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError("Could not locate inbox.json in the workspace.")


class ToolRegistry:
    def __init__(self, configured_specs: dict[str, ToolSpec] | None = None) -> None:
        merged = _default_tool_specs()
        for key, spec in (configured_specs or {}).items():
            merged[key] = spec
        self.specs = merged

    @property
    def registered_tool_ids(self) -> set[str]:
        return set(self.specs)

    def build_tools(self, tool_ids: list[str], context: ToolBuildContext) -> list[Any]:
        tools: list[Any] = []
        for tool_id in tool_ids:
            tools.append(self._build_tool(tool_id, context))
        return tools

    def _build_tool(self, tool_id: str, context: ToolBuildContext) -> Any:
        builders: dict[str, Callable[[ToolBuildContext], Any]] = {
            "list_files": self._build_list_files,
            "read_file": self._build_read_file,
            "search_in_files": self._build_search_in_files,
            "write_file": self._build_write_file,
            "run_tests": self._build_run_tests,
            "terminal": self._build_terminal,
            "execute_shell": self._build_terminal,
            "python": self._build_python,
            "web_search": self._build_web_search,
            "open_url": self._build_open_url,
            "list_emails": self._build_list_emails,
            "get_email": self._build_get_email,
            "send_reply": self._build_send_reply,
        }
        if tool_id not in builders:
            raise ValueError(f"Unknown tool id: {tool_id}")
        return builders[tool_id](context)

    def _require_workspace(self, context: ToolBuildContext) -> Path:
        if context.workspace_path is None:
            raise ValueError("This tool requires a workspace.")
        return context.workspace_path

    def _build_list_files(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="list_files")
        def list_files(path: str = ".", recursive: bool = True, limit: int = 200) -> str:
            base_path = _resolve_workspace_path(workspace_path, path)
            if not base_path.exists():
                return f"Path does not exist: {path}"
            if base_path.is_file():
                return path
            iterator = base_path.rglob("*") if recursive else base_path.glob("*")
            entries = []
            for child in iterator:
                relative = child.relative_to(workspace_path).as_posix()
                suffix = "/" if child.is_dir() else ""
                entries.append(relative + suffix)
                if len(entries) >= limit:
                    break
            return "\n".join(sorted(entries)) or "<empty>"

        return list_files

    def _build_read_file(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="read_file")
        def read_file(path: str, max_chars: int = 10_000) -> str:
            file_path = _resolve_workspace_path(workspace_path, path)
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if len(content) > max_chars:
                return content[:max_chars] + "\n...<truncated>"
            return content

        return read_file

    def _build_search_in_files(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="search_in_files")
        def search_in_files(pattern: str, limit: int = 50) -> str:
            matches: list[str] = []
            for file_path in workspace_path.rglob("*"):
                if not file_path.is_file():
                    continue
                try:
                    text = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for line_no, line in enumerate(text.splitlines(), start=1):
                    if pattern in line:
                        matches.append(f"{file_path.relative_to(workspace_path).as_posix()}:{line_no}: {line}")
                    if len(matches) >= limit:
                        return "\n".join(matches)
            return "\n".join(matches) or "No matches found."

        return search_in_files

    def _build_write_file(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="write_file")
        def write_file(path: str, content: str, append: bool = False) -> str:
            file_path = _resolve_workspace_path(workspace_path, path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with file_path.open(mode, encoding="utf-8") as handle:
                handle.write(content)
            return f"Wrote {len(content)} characters to {path}"

        return write_file

    def _build_run_tests(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="run_tests")
        def run_tests(command: str = "pytest -q", timeout_sec: int = 120) -> str:
            process = subprocess.run(
                command,
                shell=True,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            return json.dumps(
                {
                    "command": command,
                    "returncode": process.returncode,
                    "stdout": process.stdout[-8_000:],
                    "stderr": process.stderr[-8_000:],
                },
                ensure_ascii=True,
            )

        return run_tests

    def _build_terminal(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="terminal")
        def terminal(command: str, timeout_sec: int = 120) -> str:
            process = subprocess.run(
                command,
                shell=True,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            return json.dumps(
                {
                    "command": command,
                    "returncode": process.returncode,
                    "stdout": process.stdout[-8_000:],
                    "stderr": process.stderr[-8_000:],
                },
                ensure_ascii=True,
            )

        return terminal

    def _build_python(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="python")
        def python(code: str, timeout_sec: int = 120) -> str:
            process = subprocess.run(
                ["python3", "-c", code],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            return json.dumps(
                {
                    "returncode": process.returncode,
                    "stdout": process.stdout[-8_000:],
                    "stderr": process.stderr[-8_000:],
                },
                ensure_ascii=True,
            )

        return python

    def _build_web_search(self, context: ToolBuildContext) -> Any:
        return WebSearchTool()

    def _build_open_url(self, context: ToolBuildContext) -> Any:
        @function_tool(name_override="open_url")
        def open_url(url: str, max_chars: int = 12_000) -> str:
            response = httpx.get(url, timeout=20.0, follow_redirects=True)
            response.raise_for_status()
            text = response.text
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...<truncated>"
            return text

        return open_url

    def _build_list_emails(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="list_emails")
        def list_emails() -> str:
            emails = _read_email_store(workspace_path)
            summary = [
                {
                    "id": email["id"],
                    "from": email["from"],
                    "subject": email["subject"],
                }
                for email in emails
            ]
            return json.dumps(summary, ensure_ascii=True)

        return list_emails

    def _build_get_email(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)

        @function_tool(name_override="get_email")
        def get_email(email_id: str) -> str:
            emails = _read_email_store(workspace_path)
            for email in emails:
                if email["id"] == email_id:
                    return json.dumps(email, ensure_ascii=True)
            return json.dumps({"error": f"Unknown email id: {email_id}"}, ensure_ascii=True)

        return get_email

    def _build_send_reply(self, context: ToolBuildContext) -> Any:
        workspace_path = self._require_workspace(context)
        output_dir = workspace_path / ".benchmark_artifacts" / "replies"

        @function_tool(name_override="send_reply")
        def send_reply(email_id: str, body: str, subject: str | None = None) -> str:
            output_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "email_id": email_id,
                "subject": subject,
                "body": body,
            }
            artifact_path = output_dir / f"{email_id}.json"
            artifact_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
            relative_path = artifact_path.relative_to(workspace_path).as_posix()
            return json.dumps({"status": "recorded", "artifact_path": relative_path}, ensure_ascii=True)

        return send_reply
