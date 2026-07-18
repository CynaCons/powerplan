"""ASCII / structured views over a Plan model (read tools)."""

from __future__ import annotations

import json
from typing import Any, List, Optional

from .plan_model import (
    BacklogSection,
    Iteration,
    MajorSection,
    Plan,
    ProseBlock,
)


def _progress(it: Iteration) -> str:
    return f"[{it.done_count}/{it.total_count}]"


def _status_tag(it: Iteration) -> str:
    if it.status:
        return f" ({it.status})"
    if it.is_complete:
        return " (complete)"
    if it.total_count == 0:
        return ""
    return " (open)"


def show_plan(plan: Plan) -> str:
    """ASCII overview of majors / iterations with progress."""
    lines: List[str] = []
    title = plan.title or (plan.path.name if plan.path else "PLAN.md")
    lines.append(title)
    lines.append("=" * min(72, max(24, len(title))))
    if plan.path:
        lines.append(f"path: {plan.path}")

    iterations = plan.all_iterations()
    if iterations:
        done_iters = sum(1 for it in iterations if it.is_complete)
        open_iters = len(iterations) - done_iters
        task_done = sum(it.done_count for it in iterations)
        task_total = sum(it.total_count for it in iterations)
        lines.append(
            f"iterations: {len(iterations)}  "
            f"(complete: {done_iters}, open: {open_iters})  "
            f"tasks: [{task_done}/{task_total}]"
        )
    lines.append("")

    def emit_iteration(it: Iteration, indent: str = "  ") -> None:
        mark = "x" if it.is_complete else " "
        lines.append(
            f"{indent}[{mark}] {_progress(it)} {it.version} - {it.title}{_status_tag(it)}"
        )

    for block in plan.blocks:
        if isinstance(block, MajorSection):
            lines.append(f"## {block.version} — {block.title}")
            if block.description:
                lines.append(f"  > {block.description}")
            for child in block.children:
                if isinstance(child, Iteration):
                    emit_iteration(child, "  ")
            lines.append("")
        elif isinstance(block, Iteration):
            emit_iteration(block, "")
        elif isinstance(block, BacklogSection):
            n_items = sum(
                1 for i in block.items if not isinstance(i, ProseBlock)
            )
            lines.append(f"# Backlog: {block.title} ({n_items} items)")
            lines.append("")
        # ProseBlock (incl. phase-like headers): omitted from overview

    current = plan.current_iteration()
    if current:
        lines.append(
            f"current: {current.version} - {current.title} {_progress(current)}"
        )
    return "\n".join(lines).rstrip() + "\n"


def show_current_iteration(plan: Plan) -> str:
    """ASCII detail of the active / first-open iteration."""
    it = plan.current_iteration()
    if it is None:
        return "No iterations found in plan.\n"
    return _format_iteration_detail(it, plan)


def show_iteration(plan: Plan, version: str) -> str:
    it = plan.find_iteration(version)
    if it is None:
        return f"Iteration not found: {version}\n"
    return _format_iteration_detail(it, plan)


def _format_iteration_detail(it: Iteration, plan: Optional[Plan] = None) -> str:
    lines: List[str] = []
    lines.append(f"{it.version} - {it.title}")
    lines.append("-" * min(72, max(24, len(lines[0]))))
    if it.status:
        lines.append(f"status: {it.status}")
    lines.append(f"complete: {it.is_complete}  progress: {_progress(it)}")
    if it.goal:
        lines.append(f"goal: {it.goal}")
    lines.append("")
    if not it.tasks:
        lines.append("(no checkbox tasks)")
    else:
        for t in it.tasks:
            mark = "x" if t.done else " "
            lines.append(f"- [{mark}] {t.text}")
    lines.append("")
    return "\n".join(lines)


def list_iterations_view(plan: Plan, filter_name: str = "all") -> str:
    """Return JSON list of iterations filtered by open|complete|all."""
    filt = (filter_name or "all").strip().lower()
    if filt not in ("open", "complete", "all"):
        return json.dumps(
            {"error": f"Invalid filter: {filter_name!r}; use open|complete|all"},
            indent=2,
        )
    rows: List[dict[str, Any]] = []
    for it in plan.all_iterations():
        if filt == "open" and not it.is_open:
            continue
        if filt == "complete" and not it.is_complete:
            continue
        rows.append(
            {
                "version": it.version,
                "title": it.title,
                "status": it.status,
                "goal": it.goal,
                "is_complete": it.is_complete,
                "done": it.done_count,
                "total": it.total_count,
            }
        )
    return json.dumps({"filter": filt, "count": len(rows), "iterations": rows}, indent=2)


def get_iteration_view(plan: Plan, version: str) -> str:
    it = plan.find_iteration(version)
    if it is None:
        return json.dumps({"error": f"Iteration not found: {version}"}, indent=2)
    return json.dumps(it.to_dict(), indent=2, ensure_ascii=False)


def get_backlog_view(plan: Plan) -> str:
    sections = []
    for block in plan.blocks:
        if isinstance(block, BacklogSection):
            items = []
            for entry in block.items:
                if isinstance(entry, ProseBlock):
                    continue
                items.append(entry.text)
            sections.append({"title": block.title, "items": items})
    flat = plan.all_backlog_items()
    return json.dumps(
        {
            "sections": sections,
            "items": [i.text for i in flat],
            "count": len(flat),
        },
        indent=2,
        ensure_ascii=False,
    )


def find_task_view(plan: Plan, text: str) -> str:
    hits = plan.find_tasks(text)
    return json.dumps(
        {"query": text, "count": len(hits), "matches": hits},
        indent=2,
        ensure_ascii=False,
    )
