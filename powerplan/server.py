"""
powerplan MCP server v0.1.1

Standalone MCP that makes PLAN.md the operational backbone of agentic
development. Server name: ``powerplan``.

Tools (read, v0.1.1): show_plan, show_current_iteration, get_iteration,
list_iterations, get_backlog, find_task. Mutations land in v0.1.2+.

Every tool accepts optional plan_path (else walk-up discovery of PLAN.md).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure repo root is importable when launched as a script path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from powerplan.discovery import load_plan
from powerplan.views import (
    find_task_view,
    get_backlog_view,
    get_iteration_view,
    list_iterations_view,
    show_current_iteration,
    show_plan,
)

# Ensure UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SERVER_VERSION = "0.1.1"

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    from mcp.server.models import InitializationOptions
    from mcp.server.lowlevel import NotificationOptions
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

server = Server("powerplan")

_PLAN_PATH_PROP = {
    "plan_path": {
        "type": "string",
        "description": "Optional absolute/relative path to PLAN.md (overrides walk-up discovery).",
    }
}


def _load(arguments: dict[str, Any]):
    plan_path: Optional[str] = arguments.get("plan_path")
    return load_plan(plan_path=plan_path)


def _text(payload: str) -> list:
    return [TextContent(type="text", text=payload)]


def _err(msg: str, **extra: Any) -> list:
    body = {"success": False, "error": msg, **extra}
    return _text(json.dumps(body, indent=2))


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================


@server.list_tools()
async def list_tools() -> list:
    return [
        Tool(
            name="show_plan",
            description=(
                "ASCII overview of the plan: majors and iterations with "
                "[done/total] progress. Discovers nearest PLAN.md unless plan_path is set."
            ),
            inputSchema={
                "type": "object",
                "properties": {**_PLAN_PATH_PROP},
            },
        ),
        Tool(
            name="show_current_iteration",
            description=(
                "ASCII detail of the active/first-open iteration (goal, status, tasks)."
            ),
            inputSchema={
                "type": "object",
                "properties": {**_PLAN_PATH_PROP},
            },
        ),
        Tool(
            name="get_iteration",
            description="Structured JSON for one iteration (goal, tasks, status, progress).",
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {
                        "type": "string",
                        "description": "Iteration version, e.g. v0.1.0 or 2.7.3",
                    },
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        Tool(
            name="list_iterations",
            description="List iterations filtered by open | complete | all (JSON).",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "enum": ["open", "complete", "all"],
                        "default": "all",
                        "description": "Which iterations to include.",
                    },
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        Tool(
            name="get_backlog",
            description="Backlog section items from PLAN.md (JSON).",
            inputSchema={
                "type": "object",
                "properties": {**_PLAN_PATH_PROP},
            },
        ),
        Tool(
            name="find_task",
            description="Locate tasks by case-insensitive substring match (JSON).",
            inputSchema={
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Substring to search for in task text.",
                    },
                    **_PLAN_PATH_PROP,
                },
            },
        ),
    ]


# =============================================================================
# TOOL HANDLERS
# =============================================================================


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list:
    try:
        args = arguments or {}
        if name == "show_plan":
            plan = _load(args)
            return _text(show_plan(plan))
        if name == "show_current_iteration":
            plan = _load(args)
            return _text(show_current_iteration(plan))
        if name == "get_iteration":
            plan = _load(args)
            version = args.get("version")
            if not version:
                return _err("version is required")
            return _text(get_iteration_view(plan, version))
        if name == "list_iterations":
            plan = _load(args)
            filt = args.get("filter", "all")
            return _text(list_iterations_view(plan, filt))
        if name == "get_backlog":
            plan = _load(args)
            return _text(get_backlog_view(plan))
        if name == "find_task":
            plan = _load(args)
            text = args.get("text")
            if text is None or str(text).strip() == "":
                return _err("text is required")
            return _text(find_task_view(plan, str(text)))
        return _err(f"Unknown tool: {name}")
    except FileNotFoundError as e:
        return _err(str(e), error_type="FileNotFoundError")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__)


# =============================================================================
# MAIN
# =============================================================================


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="powerplan",
            server_version=SERVER_VERSION,
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await server.run(read_stream, write_stream, init_options)


def run_sync() -> None:
    """Console-script entry (powerplan = powerplan.server:run_sync)."""
    asyncio.run(main())


if __name__ == "__main__":
    run_sync()
