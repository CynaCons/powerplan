"""
powerplan MCP server v0.1.2

Standalone MCP that makes PLAN.md the operational backbone of agentic
development. Server name: ``powerplan``.

Read tools (agent-oriented): get_current_iteration, get_iteration, list_iterations,
find_task, get_backlog. Optional skim: show_plan, show_current_iteration.

Mutation tools (v0.1.2): create_major, create_iteration, set_iteration_goal,
add_task, complete_task, reopen_task, add_to_backlog, append_prose.

Every tool accepts optional plan_path (else walk-up discovery of PLAN.md).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from powerplan.discovery import find_plan_md, load_plan
from powerplan import mutations as mut
from powerplan.plan_writer import write_plan_file
from powerplan.views import (
    find_task_view,
    get_backlog_view,
    get_current_iteration_view,
    get_iteration_view,
    list_iterations_view,
    show_current_iteration,
    show_plan,
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SERVER_VERSION = "0.1.2"

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
_AGENT_PROP = {
    "agent": {
        "type": "string",
        "description": "Optional agent id tag written as [agent: id] on touched lines.",
    }
}


def _load(arguments: dict[str, Any]):
    plan_path: Optional[str] = arguments.get("plan_path")
    return load_plan(plan_path=plan_path)


def _resolve_path(arguments: dict[str, Any]) -> Path:
    plan_path = arguments.get("plan_path")
    if plan_path:
        return Path(plan_path).expanduser().resolve()
    return find_plan_md()


def _mutate(arguments: dict[str, Any], fn: Callable) -> list:
    path = _resolve_path(arguments)

    def _apply(plan):
        fn(plan)

    plan = mut.mutate_and_save(path, _apply)
    return _text(
        json.dumps(
            {
                "success": True,
                "path": str(path),
                "iterations": len(plan.all_iterations()),
                "message": "plan updated",
            },
            indent=2,
        )
    )


def _text(payload: str) -> list:
    return [TextContent(type="text", text=payload)]


def _err(msg: str, **extra: Any) -> list:
    body = {"success": False, "error": msg, **extra}
    return _text(json.dumps(body, indent=2))


@server.list_tools()
async def list_tools() -> list:
    return [
        Tool(
            name="get_current_iteration",
            description=(
                "Structured JSON for the *current* iteration (what to work on now). "
                "Resolves (current) markers / Current Status table / first open work. "
                "Preferred entry point for agents — avoids reading all of PLAN.md."
            ),
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        Tool(
            name="get_iteration",
            description=(
                "Structured JSON for one iteration by version (goal, tasks, progress). "
                "Use this (or get_current_iteration) instead of reading the whole PLAN.md."
            ),
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {"type": "string"},
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        Tool(
            name="show_current_iteration",
            description=(
                "ASCII view of the resolved *current* iteration (same resolution as "
                "get_current_iteration). Human-readable; agents should prefer the JSON tool."
            ),
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        Tool(
            name="show_plan",
            description=(
                "Optional compact index of the plan + which iteration is current. "
                "Usually unnecessary for agents (they can get_current_iteration / "
                "get_iteration). Prefer scoped tools over reading full PLAN.md."
            ),
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        Tool(
            name="list_iterations",
            description="List iterations filtered by open | complete | all.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "enum": ["open", "complete", "all"],
                        "default": "all",
                    },
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        Tool(
            name="get_backlog",
            description="Backlog section items (JSON).",
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        Tool(
            name="find_task",
            description="Locate tasks by substring match (JSON).",
            inputSchema={
                "type": "object",
                "required": ["text"],
                "properties": {"text": {"type": "string"}, **_PLAN_PATH_PROP},
            },
        ),
        # --- mutations (v0.1.2) ---
        Tool(
            name="create_major",
            description="Create a ## vX.Y — Title major section (powernote style).",
            inputSchema={
                "type": "object",
                "required": ["version", "title"],
                "properties": {
                    "version": {"type": "string", "description": "e.g. v0.1"},
                    "title": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": "Optional > blockquote under the major header.",
                    },
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        Tool(
            name="create_iteration",
            description="Create a ### vX.Y.Z — Title iteration under a major (or top-level).",
            inputSchema={
                "type": "object",
                "required": ["version", "title"],
                "properties": {
                    "version": {"type": "string"},
                    "title": {"type": "string"},
                    "major": {
                        "type": "string",
                        "description": "Parent major version (default: latest major).",
                    },
                    "goal": {"type": "string"},
                    "status": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": "Optional > blockquote under the iteration header.",
                    },
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="set_iteration_goal",
            description="Set/replace **Goal:** on an iteration.",
            inputSchema={
                "type": "object",
                "required": ["version", "goal"],
                "properties": {
                    "version": {"type": "string"},
                    "goal": {"type": "string"},
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        Tool(
            name="add_task",
            description="Append a checkbox task to an iteration (powernote - [ ] style).",
            inputSchema={
                "type": "object",
                "required": ["version", "text"],
                "properties": {
                    "version": {"type": "string"},
                    "text": {"type": "string"},
                    "done": {"type": "boolean", "default": False},
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="complete_task",
            description="Tick a task checkbox (substring match on task text).",
            inputSchema={
                "type": "object",
                "required": ["version", "task"],
                "properties": {
                    "version": {"type": "string"},
                    "task": {"type": "string", "description": "Exact or unique substring."},
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="reopen_task",
            description="Untick a task checkbox.",
            inputSchema={
                "type": "object",
                "required": ["version", "task"],
                "properties": {
                    "version": {"type": "string"},
                    "task": {"type": "string"},
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="add_to_backlog",
            description="Append an item to the Backlog / Future (Backlog) section.",
            inputSchema={
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {"type": "string"},
                    "checkbox": {"type": "boolean", "default": False},
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="append_prose",
            description="Append freeform markdown prose at top level (headers, tables, ---).",
            inputSchema={
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {"type": "string"},
                    **_PLAN_PATH_PROP,
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list:
    try:
        args = arguments or {}
        if name == "get_current_iteration":
            return _text(get_current_iteration_view(_load(args)))
        if name == "get_iteration":
            version = args.get("version")
            if not version:
                return _err("version is required")
            return _text(get_iteration_view(_load(args), version))
        if name == "show_current_iteration":
            return _text(show_current_iteration(_load(args)))
        if name == "show_plan":
            return _text(show_plan(_load(args)))
        if name == "list_iterations":
            return _text(list_iterations_view(_load(args), args.get("filter", "all")))
        if name == "get_backlog":
            return _text(get_backlog_view(_load(args)))
        if name == "find_task":
            text = args.get("text")
            if text is None or str(text).strip() == "":
                return _err("text is required")
            return _text(find_task_view(_load(args), str(text)))

        if name == "create_major":
            ver, title = args.get("version"), args.get("title")
            if not ver or not title:
                return _err("version and title are required")
            return _mutate(
                args,
                lambda p: mut.create_major(
                    p, ver, title, description=args.get("description")
                ),
            )

        if name == "create_iteration":
            ver, title = args.get("version"), args.get("title")
            if not ver or not title:
                return _err("version and title are required")
            return _mutate(
                args,
                lambda p: mut.create_iteration(
                    p,
                    ver,
                    title,
                    major=args.get("major"),
                    goal=args.get("goal"),
                    status=args.get("status"),
                    description=args.get("description"),
                ),
            )

        if name == "set_iteration_goal":
            ver, goal = args.get("version"), args.get("goal")
            if not ver or goal is None:
                return _err("version and goal are required")
            return _mutate(args, lambda p: mut.set_iteration_goal(p, ver, goal))

        if name == "add_task":
            ver, text = args.get("version"), args.get("text")
            if not ver or text is None:
                return _err("version and text are required")
            return _mutate(
                args,
                lambda p: mut.add_task(
                    p,
                    ver,
                    text,
                    done=bool(args.get("done", False)),
                    agent=args.get("agent"),
                ),
            )

        if name == "complete_task":
            ver, task = args.get("version"), args.get("task")
            if not ver or not task:
                return _err("version and task are required")
            return _mutate(
                args,
                lambda p: mut.complete_task(p, ver, task, agent=args.get("agent")),
            )

        if name == "reopen_task":
            ver, task = args.get("version"), args.get("task")
            if not ver or not task:
                return _err("version and task are required")
            return _mutate(
                args,
                lambda p: mut.reopen_task(p, ver, task, agent=args.get("agent")),
            )

        if name == "add_to_backlog":
            text = args.get("text")
            if text is None:
                return _err("text is required")
            return _mutate(
                args,
                lambda p: mut.add_to_backlog(
                    p,
                    text,
                    agent=args.get("agent"),
                    checkbox=bool(args.get("checkbox", False)),
                ),
            )

        if name == "append_prose":
            text = args.get("text")
            if text is None:
                return _err("text is required")
            return _mutate(args, lambda p: mut.append_prose(p, text))

        return _err(f"Unknown tool: {name}")
    except FileNotFoundError as e:
        return _err(str(e), error_type="FileNotFoundError")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__)


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
    asyncio.run(main())


if __name__ == "__main__":
    run_sync()
