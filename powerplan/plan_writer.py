"""
Serialize a Plan model back to PLAN.md text.

When nothing was mutated after parse, the output is byte-identical to the
source because every node retains its original ``raw`` / ``header_raw`` text.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

from .plan_model import (
    BacklogItem,
    BacklogSection,
    Iteration,
    MajorSection,
    Plan,
    ProseBlock,
    Task,
)


def write_node(node) -> str:
    """Serialize one model node to text."""
    if isinstance(node, ProseBlock):
        return node.raw

    if isinstance(node, Task):
        if node.raw:
            return node.raw
        mark = "x" if node.done else " "
        return f"- [{mark}] {node.text}\n"

    if isinstance(node, BacklogItem):
        if node.raw:
            return node.raw
        return f"- {node.text}\n"

    if isinstance(node, Iteration):
        parts = [node.header_raw or _format_iteration_header(node)]
        for child in node.body:
            parts.append(write_node(child))
        return "".join(parts)

    if isinstance(node, MajorSection):
        parts = [node.header_raw or f"## {node.version} — {node.title}\n"]
        for child in node.children:
            parts.append(write_node(child))
        return "".join(parts)

    if isinstance(node, BacklogSection):
        parts = [node.header_raw or f"## {node.title}\n"]
        for child in node.items:
            parts.append(write_node(child))
        return "".join(parts)

    raise TypeError(f"Unknown plan node type: {type(node)!r}")


def _format_iteration_header(it: Iteration) -> str:
    title = it.title
    if it.status:
        title = f"{title} ({it.status})"
    return f"### {it.version} - {title}\n"


def write_plan(plan: Plan) -> str:
    """Serialize the full plan to a string (exact raw concatenation)."""
    return "".join(write_node(block) for block in plan.blocks)


def write_plan_file(plan: Plan, path: Union[str, Path, None] = None) -> Path:
    """
    Write plan text to disk using UTF-8 without newline translation.

    Written to a sibling temp file and moved into place with ``os.replace``, so
    a crash or kill mid-write leaves the previous PLAN.md intact rather than a
    truncated one. This matters most for ``apply_ops``, where a single write
    carries a whole turn's worth of mutations.
    """
    target = Path(path) if path is not None else plan.path
    if target is None:
        raise ValueError("No path provided and plan.path is unset")
    text = write_plan(plan)
    tmp = target.with_name(f".{target.name}.powerplan.tmp")
    try:
        tmp.write_bytes(text.encode("utf-8"))
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return target
