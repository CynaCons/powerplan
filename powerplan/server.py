"""
powerplan MCP server v0.2.2

Standalone MCP: PLAN.md as the operational backbone of agentic development.
Server name: ``powerplan``.

Every tool accepts optional ``plan_path`` (relative or absolute). Default:
walk up from cwd to nearest PLAN.md. Use ``create_plan`` when none exists.
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

from powerplan.discovery import find_plan_md, load_plan, resolve_plan_path
from powerplan import mutations as mut
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

SERVER_VERSION = "0.2.2"

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
        "description": (
            "Optional path to PLAN.md (relative to cwd or absolute). "
            "Default: walk up from cwd to nearest PLAN.md."
        ),
    }
}
_AGENT_PROP = {
    "agent": {
        "type": "string",
        "description": "Optional agent id tag written as [agent: id] on touched lines.",
    }
}


def _text(payload: str) -> list:
    return [TextContent(type="text", text=payload)]


def _err(msg: str, **extra: Any) -> list:
    return _text(json.dumps({"success": False, "error": msg, **extra}, indent=2))


def _ok(**extra: Any) -> list:
    body = {"success": True, **extra}
    return _text(json.dumps(body, indent=2))


def _load(arguments: dict[str, Any]):
    return load_plan(plan_path=arguments.get("plan_path"))


def _resolve_existing(arguments: dict[str, Any]) -> Path:
    return resolve_plan_path(arguments.get("plan_path"), must_exist=True)


def _mutate(arguments: dict[str, Any], fn: Callable) -> list:
    path = _resolve_existing(arguments)
    plan = mut.mutate_and_save(path, fn, allow_create=False)
    return _ok(
        path=str(path),
        iterations=len(plan.all_iterations()),
        message="plan updated",
    )


@server.list_tools()
async def list_tools() -> list:
    return [
        # --- agent-first reads ---
        Tool(
            name="get_current_iteration",
            description=(
                "JSON for the *current* iteration (what to work on now). "
                "Preferred agent entry — avoids reading all of PLAN.md."
            ),
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        Tool(
            name="get_iteration",
            description="JSON for one iteration by version (goal, tasks, progress).",
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {"version": {"type": "string"}, **_PLAN_PATH_PROP},
            },
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
            name="find_task",
            description="Locate tasks by substring match (JSON).",
            inputSchema={
                "type": "object",
                "required": ["text"],
                "properties": {"text": {"type": "string"}, **_PLAN_PATH_PROP},
            },
        ),
        Tool(
            name="get_backlog",
            description="Backlog section items (JSON).",
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        Tool(
            name="show_current_iteration",
            description="ASCII view of the resolved current iteration (humans/logs).",
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        Tool(
            name="show_plan",
            description=(
                "Compact index: counts + current iteration. Agents should prefer "
                "get_current_iteration / get_iteration over this or full PLAN.md."
            ),
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        Tool(
            name="check_plan",
            description="Structure lint: duplicates, multiple current, complete-with-open-tasks.",
            inputSchema={"type": "object", "properties": {**_PLAN_PATH_PROP}},
        ),
        # --- bootstrap ---
        Tool(
            name="create_plan",
            description=(
                "Bootstrap a new PLAN.md when none exists (powernote-style skeleton). "
                "Default path: ./PLAN.md in cwd. Refuses overwrite unless force=true."
            ),
            inputSchema={
                "type": "object",
                "required": ["title"],
                "properties": {
                    "title": {"type": "string"},
                    "goal": {"type": "string"},
                    "philosophy": {"type": "string"},
                    "force": {
                        "type": "boolean",
                        "default": False,
                        "description": "Overwrite existing file if true.",
                    },
                    "seed_major": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include v0.1 / v0.1.0 starter shell (default true).",
                    },
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        # --- mutations ---
        Tool(
            name="create_major",
            description="Create ## vX.Y — Title major section.",
            inputSchema={
                "type": "object",
                "required": ["version", "title"],
                "properties": {
                    "version": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        Tool(
            name="create_iteration",
            description="Create ### vX.Y.Z — Title iteration.",
            inputSchema={
                "type": "object",
                "required": ["version", "title"],
                "properties": {
                    "version": {"type": "string"},
                    "title": {"type": "string"},
                    "major": {"type": "string"},
                    "goal": {"type": "string"},
                    "status": {"type": "string"},
                    "description": {"type": "string"},
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
            description="Append a checkbox task to an iteration.",
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
            description="Tick a task checkbox (substring match).",
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
            description="Append an item to Future (Backlog).",
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
            description="Append freeform markdown at top level.",
            inputSchema={
                "type": "object",
                "required": ["text"],
                "properties": {"text": {"type": "string"}, **_PLAN_PATH_PROP},
            },
        ),
        Tool(
            name="start_iteration",
            description="Mark iteration ACTIVE / current; clears other current markers.",
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {"version": {"type": "string"}, **_PLAN_PATH_PROP},
            },
        ),
        Tool(
            name="close_iteration",
            description=(
                "Mark iteration COMPLETE. Requires force=true if open tasks remain. "
                "Optional stamp (e.g. date) appended to title."
            ),
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {"type": "string"},
                    "force": {"type": "boolean", "default": False},
                    "stamp": {"type": "string"},
                    **_PLAN_PATH_PROP,
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list:
    try:
        args = arguments or {}

        if name == "create_plan":
            title = args.get("title")
            if not title:
                return _err("title is required")
            path = resolve_plan_path(
                args.get("plan_path"),
                must_exist=False,
            )
            # default name PLAN.md when only directory implied — resolve_plan_path
            # already returns cwd/PLAN.md when missing
            plan = mut.create_plan(
                title=title,
                goal=args.get("goal"),
                philosophy=args.get("philosophy"),
                plan_path=path,
                force=bool(args.get("force", False)),
                seed_major=args.get("seed_major", True) is not False,
            )
            return _ok(
                path=str(path),
                created=True,
                title=plan.title,
                iterations=len(plan.all_iterations()),
            )

        if name == "get_current_iteration":
            return _text(get_current_iteration_view(_load(args)))
        if name == "get_iteration":
            version = args.get("version")
            if not version:
                return _err("version is required")
            return _text(get_iteration_view(_load(args), version))
        if name == "list_iterations":
            return _text(list_iterations_view(_load(args), args.get("filter", "all")))
        if name == "find_task":
            text = args.get("text")
            if text is None or str(text).strip() == "":
                return _err("text is required")
            return _text(find_task_view(_load(args), str(text)))
        if name == "get_backlog":
            return _text(get_backlog_view(_load(args)))
        if name == "show_current_iteration":
            return _text(show_current_iteration(_load(args)))
        if name == "show_plan":
            return _text(show_plan(_load(args)))
        if name == "check_plan":
            plan = _load(args)
            report = mut.check_plan(plan)
            report["path"] = str(plan.path) if plan.path else None
            report["success"] = True
            return _text(json.dumps(report, indent=2))

        if name == "create_major":
            ver, title = args.get("version"), args.get("title")
            if not ver or not title:
                return _err("version and title are required")
            return _mutate(
                args,
                lambda p: mut.create_major(p, ver, title, description=args.get("description")),
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
                    p, ver, text, done=bool(args.get("done", False)), agent=args.get("agent")
                ),
            )
        if name == "complete_task":
            ver, task = args.get("version"), args.get("task")
            if not ver or not task:
                return _err("version and task are required")
            return _mutate(
                args, lambda p: mut.complete_task(p, ver, task, agent=args.get("agent"))
            )
        if name == "reopen_task":
            ver, task = args.get("version"), args.get("task")
            if not ver or not task:
                return _err("version and task are required")
            return _mutate(
                args, lambda p: mut.reopen_task(p, ver, task, agent=args.get("agent"))
            )
        if name == "add_to_backlog":
            text = args.get("text")
            if text is None:
                return _err("text is required")
            return _mutate(
                args,
                lambda p: mut.add_to_backlog(
                    p, text, agent=args.get("agent"), checkbox=bool(args.get("checkbox", False))
                ),
            )
        if name == "append_prose":
            text = args.get("text")
            if text is None:
                return _err("text is required")
            return _mutate(args, lambda p: mut.append_prose(p, text))
        if name == "start_iteration":
            ver = args.get("version")
            if not ver:
                return _err("version is required")
            return _mutate(args, lambda p: mut.start_iteration(p, ver))
        if name == "close_iteration":
            ver = args.get("version")
            if not ver:
                return _err("version is required")
            return _mutate(
                args,
                lambda p: mut.close_iteration(
                    p, ver, force=bool(args.get("force", False)), stamp=args.get("stamp")
                ),
            )

        return _err(f"Unknown tool: {name}")
    except FileNotFoundError as e:
        return _err(str(e), error_type="FileNotFoundError", hint="create_plan")
    except FileExistsError as e:
        return _err(str(e), error_type="FileExistsError", hint="force=true")
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
