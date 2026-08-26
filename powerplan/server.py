"""
powerplan MCP server

Standalone MCP: PLAN.md as the operational backbone of agentic development.
Server name: ``powerplan``. Public package name: ``powerplan-mcp``.

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

from powerplan import __version__ as SERVER_VERSION
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
# Shared task addressing: one of task / index / tasks / indexes.
# expect is singular-only (scalar task or index).
_TASK_ADDRESS_PROPS = {
    "task": {
        "type": "string",
        "description": "One task (exact, else unique substring). One addressing mode.",
    },
    "index": {
        "type": "integer",
        "minimum": 1,
        "description": "One 1-based position. One addressing mode.",
    },
    "tasks": {
        "type": "array",
        "minItems": 1,
        "items": {"type": "string"},
        "description": (
            "Several task texts (exact, else unique substring). "
            "One write. One addressing mode."
        ),
    },
    "indexes": {
        "type": "array",
        "minItems": 1,
        "items": {"type": "integer", "minimum": 1},
        "description": (
            "Several 1-based positions. Prefer this after get_iteration. "
            "One write. One addressing mode."
        ),
    },
    "expect": {
        "type": "string",
        "description": (
            "Optional guard for a single task: current text must match or the "
            "edit is refused. Ignored/rejected with tasks/indexes. Agent tags "
            "are ignored in the comparison."
        ),
    },
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


def _mutate_result(arguments: dict[str, Any], fn: Callable):
    """Load → mutator(plan) → save; return (plan, mutator_return, path)."""
    path = _resolve_existing(arguments)
    holder: dict[str, Any] = {}

    def wrapped(p):
        holder["r"] = fn(p)

    plan = mut.mutate_and_save(path, wrapped, allow_create=False)
    return plan, holder.get("r"), path


def _pairs_ok(path, version: str, verb: str, pairs) -> list:
    rows = [{"index": i, "text": t.text, "done": t.done} for i, t in pairs]
    return _ok(
        path=str(path),
        version=version,
        updated=len(rows),
        tasks=rows,
        message=f"{verb} {len(rows)} task(s)",
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
            name="add_tasks",
            description=(
                "Append several checkbox tasks in one write. Prefer this over "
                "repeated add_task. Shared done/agent apply to every item."
            ),
            inputSchema={
                "type": "object",
                "required": ["version", "tasks"],
                "properties": {
                    "version": {"type": "string"},
                    "tasks": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                        "description": "Task texts to append, in order.",
                    },
                    "done": {
                        "type": "boolean",
                        "default": False,
                        "description": "Mark every added task done (default false).",
                    },
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="complete_task",
            description=(
                "Tick one or many tasks in one write. For several, pass indexes "
                "(preferred after get_iteration) or tasks. For exactly one, "
                "index or task still work."
            ),
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {"type": "string"},
                    **_TASK_ADDRESS_PROPS,
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="reopen_task",
            description=(
                "Untick one or many tasks in one write. For several, pass "
                "indexes or tasks. For exactly one, index or task still work."
            ),
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {"type": "string"},
                    **_TASK_ADDRESS_PROPS,
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="update_task",
            description=(
                "Rewrite task text, preserving done state. One task: text + "
                "index/task. Several: changes[{text, index|task, expect?}]."
            ),
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {"type": "string"},
                    "text": {"type": "string", "description": "New text for a single task."},
                    "changes": {
                        "type": "array",
                        "minItems": 1,
                        "description": (
                            "Several rewrites in one write. Do not mix with the "
                            "singular text + index/task shape."
                        ),
                        "items": {
                            "type": "object",
                            "required": ["text"],
                            "properties": {
                                "text": {"type": "string"},
                                "index": {"type": "integer", "minimum": 1},
                                "task": {"type": "string"},
                                "expect": {"type": "string"},
                            },
                        },
                    },
                    **_TASK_ADDRESS_PROPS,
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="remove_task",
            description=(
                "Delete one or many tasks in one write. For several, pass "
                "indexes or tasks. Resolve-all then drop (indexes do not shift)."
            ),
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {"type": "string"},
                    **_TASK_ADDRESS_PROPS,
                    **_PLAN_PATH_PROP,
                },
            },
        ),
        Tool(
            name="defer_task",
            description=(
                "Move one or many tasks to the backlog in one write. For several, "
                "pass indexes or tasks. Shared reason/agent apply to every item."
            ),
            inputSchema={
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {"type": "string"},
                    "reason": {
                        "type": "string",
                        "description": "Optional why, appended to the backlog entry.",
                    },
                    **_TASK_ADDRESS_PROPS,
                    **_PLAN_PATH_PROP,
                    **_AGENT_PROP,
                },
            },
        ),
        Tool(
            name="add_to_backlog",
            description=(
                "Append one (text) or many (texts) items to Future (Backlog) "
                "in one write."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "One backlog item."},
                    "texts": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                        "description": "Several backlog items, in order. One write.",
                    },
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
        if name == "add_tasks":
            ver, tasks = args.get("version"), args.get("tasks")
            if not ver:
                return _err("version is required")
            if not isinstance(tasks, list) or not tasks:
                return _err("tasks must be a non-empty list of strings")
            plan, added, path = _mutate_result(
                args,
                lambda p: mut.add_tasks(
                    p,
                    ver,
                    tasks,
                    done=bool(args.get("done", False)),
                    agent=args.get("agent"),
                ),
            )
            it = plan.find_iteration(ver)
            n = len(added or [])
            start_idx = (it.total_count - n + 1) if it is not None else 1
            return _ok(
                path=str(path),
                version=ver,
                added=n,
                tasks=[
                    {"index": start_idx + i, "text": t.text, "done": t.done}
                    for i, t in enumerate(added or [])
                ],
                message=f"added {n} task(s)",
            )
        if name in ("complete_task", "reopen_task", "update_task", "remove_task", "defer_task"):
            ver = args.get("version")
            if not ver:
                return _err("version is required")
            addr = {
                "task": args.get("task"),
                "index": args.get("index"),
                "expect": args.get("expect"),
                "tasks": args.get("tasks"),
                "indexes": args.get("indexes"),
            }
            singular = {
                "task": addr["task"],
                "index": addr["index"],
                "expect": addr["expect"],
            }

            if name == "update_task":
                changes = args.get("changes")
                if changes is not None:
                    _, result, path = _mutate_result(
                        args,
                        lambda p: mut.update_task(
                            p, ver, changes=changes, agent=args.get("agent")
                        ),
                    )
                    return _pairs_ok(path, ver, "updated", result)
                if addr["tasks"] is not None or addr["indexes"] is not None:
                    return _err("for several updates, pass changes (not tasks/indexes)")
                text = args.get("text")
                if text is None or str(text).strip() == "":
                    return _err("text is required (or pass changes)")
                _, result, path = _mutate_result(
                    args,
                    lambda p: mut.update_task(
                        p, ver, text=text, agent=args.get("agent"), **singular
                    ),
                )
                return _pairs_ok(path, ver, "updated", result)

            if name == "complete_task":
                fn = lambda p: mut.complete_task(p, ver, agent=args.get("agent"), **addr)
                verb = "completed"
            elif name == "reopen_task":
                fn = lambda p: mut.reopen_task(p, ver, agent=args.get("agent"), **addr)
                verb = "reopened"
            elif name == "remove_task":
                fn = lambda p: mut.remove_task(p, ver, **addr)
                verb = "removed"
            else:  # defer_task
                fn = lambda p: mut.defer_task(
                    p, ver, reason=args.get("reason"), agent=args.get("agent"), **addr
                )
                verb = "deferred"

            _, result, path = _mutate_result(args, fn)
            if name == "defer_task":
                rows = [
                    {"index": i, "text": t.text, "done": t.done}
                    for i, t, _item in result
                ]
                backlog = [{"text": item.text} for _i, _t, item in result]
                return _ok(
                    path=str(path),
                    version=ver,
                    updated=len(rows),
                    tasks=rows,
                    backlog=backlog,
                    message=f"{verb} {len(rows)} task(s)",
                )
            return _pairs_ok(path, ver, verb, result)
        if name == "add_to_backlog":
            text, texts = args.get("text"), args.get("texts")
            if text is not None and texts is not None:
                return _err("pass either text or texts, not both")
            if text is None and texts is None:
                return _err("text or texts is required")
            _, result, path = _mutate_result(
                args,
                lambda p: mut.add_to_backlog(
                    p,
                    text=text,
                    texts=texts,
                    agent=args.get("agent"),
                    checkbox=bool(args.get("checkbox", False)),
                ),
            )
            items = result if isinstance(result, list) else [result]
            return _ok(
                path=str(path),
                added=len(items),
                backlog=[{"text": i.text} for i in items],
                message=f"added {len(items)} backlog item(s)",
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
