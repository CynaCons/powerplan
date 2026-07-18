#!/usr/bin/env python3
"""
Rebuild a PLAN.md using powerplan mutation APIs (same surface as MCP tools).

Usage:
  python scripts/recreate_plan.py \\
    --source /path/to/PowerNote/PLAN.md \\
    --out temp.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# repo root on path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from powerplan.plan_parser import parse_plan_file
from powerplan.plan_model import (
    BacklogItem,
    BacklogSection,
    Iteration,
    MajorSection,
    ProseBlock,
    Task,
)
from powerplan.plan_writer import write_plan
from powerplan import mutations as m


def _rebuild_iteration(plan, it: Iteration, major_version: str | None) -> None:
    """Rebuild iteration using mutation API; preserve source header_raw / task raw."""
    goal = it.goal
    body = list(it.body)

    # Use create_iteration for structure, then overwrite header_raw for fidelity
    # (handles titles like v0.25.0-proto that the version regex truncates).
    created = m.create_iteration(
        plan,
        it.version,
        it.title,
        major=major_version,
        goal=None,  # re-apply from body order below
        status=it.status,
        description=None,
    )
    if it.header_raw:
        created.header_raw = it.header_raw
    # clear auto-inserted goal body from create_iteration
    created.body = []
    created.tasks = []
    created.goal = goal

    for node in body:
        if isinstance(node, Task):
            # Prefer original raw line for exact look
            if node.raw:
                t = Task(text=node.text, done=node.done, raw=node.raw)
                created.tasks.append(t)
                created.body.append(t)
            else:
                m.add_task(plan, it.version, node.text, done=node.done)
        elif isinstance(node, ProseBlock):
            created.body.append(ProseBlock(raw=node.raw))


def rebuild(source: Path) -> str:
    src_plan = parse_plan_file(source)
    plan = m.empty_plan(src_plan.title or "Implementation Plan")

    # We'll replace empty_plan's default H1 via set_preamble when we see first prose
    plan.blocks = []
    first_preamble_done = False

    for block in src_plan.blocks:
        if isinstance(block, ProseBlock):
            raw = block.raw
            if not first_preamble_done and (
                raw.lstrip().startswith("# ") or "**Goal:**" in raw or "**Philosophy:**" in raw
            ):
                m.set_preamble(plan, raw)
                first_preamble_done = True
            elif raw.strip() == "---" or raw.strip() == "---\n" or raw.replace("\n", "") == "---":
                m.add_separator(plan)
            elif raw.strip() in ("",) or set(raw) <= {"\n", "\r", " ", "\t"}:
                m.append_prose(plan, raw if raw.endswith("\n") else raw + "\n")
            else:
                # section headers / tables / freeform
                if not plan.blocks:
                    m.set_preamble(plan, raw)
                    first_preamble_done = True
                else:
                    m.append_prose(plan, raw)
            continue

        if isinstance(block, MajorSection):
            children = list(block.children)
            # Structural create, then restore exact header/description children from source
            created = m.create_major(
                plan, block.version, block.title, description=None
            )
            if block.header_raw:
                created.header_raw = block.header_raw
            created.title = block.title
            created.description = block.description
            # Drop auto-generated blockquote from create_major
            created.children = []

            for child in children:
                if isinstance(child, Iteration):
                    _rebuild_iteration(plan, child, block.version)
                elif isinstance(child, ProseBlock):
                    maj = m._find_major(plan, block.version)
                    assert maj is not None
                    maj.children.append(ProseBlock(raw=child.raw))
            first_preamble_done = True
            continue

        if isinstance(block, Iteration):
            _rebuild_iteration(plan, block, None)
            first_preamble_done = True
            continue

        if isinstance(block, BacklogSection):
            sec = m.ensure_backlog(plan, title=block.title)
            sec.header_raw = block.header_raw or f"## {block.title}\n"
            sec.title = block.title
            sec.items = []
            for item in block.items:
                if isinstance(item, BacklogItem):
                    sec.items.append(
                        BacklogItem(text=item.text, raw=item.raw or f"- {item.text}\n")
                    )
                elif isinstance(item, ProseBlock):
                    sec.items.append(ProseBlock(raw=item.raw))
            first_preamble_done = True
            continue

    return write_plan(plan)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source",
        type=Path,
        default=Path(r"C:\dev\private-repo\PowerNote\PLAN.md"),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=_ROOT / "temp.md",
    )
    args = ap.parse_args()

    text = rebuild(args.source)
    src_bytes = args.source.read_bytes()
    # Preserve source newline style (PowerNote on Windows often uses CRLF)
    if b"\r\n" in src_bytes:
        payload = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    else:
        payload = text.replace("\r\n", "\n").encode("utf-8")
    args.out.write_bytes(payload)

    identical = payload == src_bytes
    print(f"wrote {args.out} ({len(payload)} bytes)")
    print(f"byte_identical_to_source: {identical}")
    if not identical:
        import difflib

        src = src_bytes.decode("utf-8")
        out = payload.decode("utf-8")
        # Compare logical lines (ignore pure newline-style diffs already handled)
        s_lines = src.splitlines()
        t_lines = out.splitlines()
        print(f"source_lines={len(s_lines)} out_lines={len(t_lines)}")
        diff = list(
            difflib.unified_diff(s_lines, t_lines, fromfile="source", tofile="temp", n=1)
        )
        for line in diff[:80]:
            print(line)
        print(f"... total diff lines: {len(diff)}")
        # content-equal ignoring newline style?
        print(
            "content_equal_ignoring_newlines:",
            src.replace("\r\n", "\n") == out.replace("\r\n", "\n"),
        )
    return 0 if identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
