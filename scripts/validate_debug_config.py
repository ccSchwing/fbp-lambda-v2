#!/usr/bin/env python3
"""Validate VS Code debug/task configuration for SAM + debugpy workflows."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LAUNCH_PATH = ROOT / ".vscode" / "launch.json"
TASKS_PATH = ROOT / ".vscode" / "tasks.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def emit(path: Path, severity: str, message: str, line: int = 1, column: int = 1) -> None:
    print(f"{rel(path)}:{line}:{column}: {severity}: {message}")


def load_json(path: Path) -> Any | None:
    if not path.exists():
        emit(path, "error", "File not found")
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        emit(path, "error", f"Invalid JSON: {exc.msg}", exc.lineno, exc.colno)
        return None


def extract_debugpy_attach_ports(launch: dict[str, Any]) -> set[int]:
    ports: set[int] = set()
    for cfg in launch.get("configurations", []):
        if not isinstance(cfg, dict):
            continue
        if cfg.get("type") != "debugpy" or cfg.get("request") != "attach":
            continue

        connect = cfg.get("connect")
        if isinstance(connect, dict) and isinstance(connect.get("port"), int):
            ports.add(connect["port"])
            continue

        port = cfg.get("port")
        if isinstance(port, int):
            ports.add(port)

    return ports


def validate_launch_json(launch: dict[str, Any]) -> int:
    issues = 0
    configs = launch.get("configurations")

    if not isinstance(configs, list):
        emit(LAUNCH_PATH, "error", "Expected 'configurations' to be an array")
        return 1

    for cfg in configs:
        if not isinstance(cfg, dict):
            continue

        name = cfg.get("name", "<unnamed>")
        if cfg.get("type") != "debugpy" or cfg.get("request") != "attach":
            continue

        connect = cfg.get("connect")
        host_name = cfg.get("hostName")
        port = cfg.get("port")

        has_connect = isinstance(connect, dict) and isinstance(connect.get("host"), str) and isinstance(connect.get("port"), int)
        has_legacy_host_port = isinstance(host_name, str) and isinstance(port, int)

        if not has_connect and not has_legacy_host_port:
            emit(
                LAUNCH_PATH,
                "error",
                f"debugpy attach config '{name}' must define either connect.host/connect.port or hostName/port",
            )
            issues += 1

        path_mappings = cfg.get("pathMappings")
        if not isinstance(path_mappings, list) or not path_mappings:
            emit(
                LAUNCH_PATH,
                "error",
                f"debugpy attach config '{name}' should define non-empty pathMappings for container debugging",
            )
            issues += 1
        else:
            for mapping in path_mappings:
                if not isinstance(mapping, dict):
                    emit(LAUNCH_PATH, "error", f"debugpy attach config '{name}' has invalid pathMappings entry")
                    issues += 1
                    continue
                if not isinstance(mapping.get("localRoot"), str) or not mapping.get("localRoot"):
                    emit(LAUNCH_PATH, "error", f"debugpy attach config '{name}' has pathMapping without localRoot")
                    issues += 1
                if not isinstance(mapping.get("remoteRoot"), str) or not mapping.get("remoteRoot"):
                    emit(LAUNCH_PATH, "error", f"debugpy attach config '{name}' has pathMapping without remoteRoot")
                    issues += 1

    return issues


def validate_tasks_json(tasks_doc: dict[str, Any], debug_ports: set[int]) -> int:
    issues = 0
    tasks = tasks_doc.get("tasks")

    if not isinstance(tasks, list):
        emit(TASKS_PATH, "error", "Expected 'tasks' to be an array")
        return 1

    for task in tasks:
        if not isinstance(task, dict):
            continue

        label = task.get("label", "<unnamed>")
        args = task.get("args")
        if not isinstance(args, list) or len(args) < 2:
            continue
        if args[0] != "-c" or not isinstance(args[1], str):
            continue

        cmd = args[1]
        if "sam local invoke" not in cmd:
            continue

        has_debug_args = "--debug-args" in cmd
        has_debugger_path = "--debugger-path" in cmd
        has_wait = "--wait-for-client" in cmd
        has_debugpy = "-m debugpy" in cmd

        if has_debug_args and not has_debugger_path:
            emit(
                TASKS_PATH,
                "warning",
                f"task '{label}' uses --debug-args without --debugger-path; debugpy may not resolve in SAM runtime",
            )
            issues += 1

        if has_wait and has_debugpy and not has_debugger_path:
            emit(
                TASKS_PATH,
                "error",
                f"task '{label}' uses --wait-for-client with debugpy but has no --debugger-path",
            )
            issues += 1

        port_match = re.search(r"(?:^|\s)-d\s+(\d+)(?:\s|$)", cmd)
        if port_match and (has_debug_args or has_debugpy):
            port = int(port_match.group(1))
            if port not in debug_ports:
                emit(
                    TASKS_PATH,
                    "warning",
                    f"task '{label}' exposes debug port {port} but no debugpy attach config uses that port",
                )
                issues += 1

    return issues


def main() -> int:
    launch = load_json(LAUNCH_PATH)
    tasks = load_json(TASKS_PATH)

    if launch is None or tasks is None:
        return 1

    issue_count = 0
    issue_count += validate_launch_json(launch)
    debug_ports = extract_debugpy_attach_ports(launch)
    issue_count += validate_tasks_json(tasks, debug_ports)

    if issue_count == 0:
        print("validate_debug_config: OK")
        return 0

    print(f"validate_debug_config: found {issue_count} issue(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
