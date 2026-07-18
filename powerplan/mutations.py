"""
Surgical mutation API for PLAN.md (powernote-style formatting).

Used by the MCP server and by offline drivers. When nodes are created without
``header_raw`` / ``raw``, writers emit the managed format:

  ## v0.1 — Title
  > major description

  ### v0.1.0 — Iteration title
  **Goal:** …
  - [ ] task
  - [x] done task
"""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import List, Optional, Union

from .plan_model import (
    BacklogItem,
    BacklogSection,
    Iteration,
    MajorSection,
    Plan,
    ProseBlock,
    Task,
    _norm_version,
)
from .plan_parser import parse_plan_file
from .plan_writer import write_plan, write_plan_file

# Powernote / managed format uses em dash with spaces
_EM = "—"

_file_lock = threading.Lock()


def _nl(text: str) -> str:
    """Ensure text ends with a newline, preserving CRLF if the body uses it."""
    if not text:
        return ""
    if "\r\n" in text:
        if not text.endswith("\n"):
            text += "\r\n"
        return text
    # Normalize lone CR to LF for LF documents
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"
    return text


def _agent_suffix(agent: Optional[str]) -> str:
    if not agent:
        return ""
    tag = agent.strip()
    if not tag:
        return ""
    # strip existing agent tag from accidental double-apply
    return f" [agent: {tag}]"


def _strip_agent_tag(text: str) -> str:
    return re.sub(r"\s*\[agent:\s*[^\]]+\]\s*$", "", text).rstrip()


def format_major_header(version: str, title: str) -> str:
    v = version if version.lower().startswith("v") else f"v{version}"
    return f"## {v} {_EM} {title}\n"


def format_iteration_header(
    version: str, title: str, status: Optional[str] = None
) -> str:
    v = version if version.lower().startswith("v") else f"v{version}"
    t = title
    if status:
        t = f"{title} ({status})"
    return f"### {v} {_EM} {t}\n"


def format_task_line(text: str, done: bool = False, agent: Optional[str] = None) -> str:
    mark = "x" if done else " "
    body = _strip_agent_tag(text) + _agent_suffix(agent)
    return f"- [{mark}] {body}\n"


def format_goal_line(goal: str) -> str:
    return f"**Goal:** {goal}\n"


def format_blockquote(description: str) -> str:
    # Single-line > description (powernote style under majors / some iterations)
    desc = description.strip()
    return f"> {desc}\n"


def empty_plan(title: str = "Implementation Plan") -> Plan:
    """Create an empty plan with an H1 title and blank line."""
    h1 = f"# {title}\n"
    return Plan(title=title, blocks=[ProseBlock(raw=h1 + "\n")])


def set_preamble(plan: Plan, preamble: str) -> Plan:
    """
    Replace leading ProseBlock(s) before the first major/iteration/backlog
    with a single preamble prose block (title + meta + rules).
    """
    preamble = _nl(preamble)
    rest: List = []
    seen_structure = False
    for b in plan.blocks:
        if not seen_structure and isinstance(b, ProseBlock):
            continue
        seen_structure = True
        rest.append(b)
    plan.blocks = [ProseBlock(raw=preamble)] + rest
    if preamble.startswith("# "):
        first = preamble.split("\n", 1)[0][2:].strip()
        if first:
            plan.title = first
    return plan


def append_prose(plan: Plan, text: str) -> Plan:
    """Append opaque prose at top level (closes no structure beyond append)."""
    raw = _nl(text)
    if plan.blocks and isinstance(plan.blocks[-1], ProseBlock):
        plan.blocks[-1].raw += raw
    else:
        plan.blocks.append(ProseBlock(raw=raw))
    return plan


def add_separator(plan: Plan) -> Plan:
    """Append a markdown horizontal rule block (powernote section divider)."""
    # Prefer separator as its own prose chunk for clarity
    plan.blocks.append(ProseBlock(raw="\n---\n\n"))
    return plan


def create_major(
    plan: Plan,
    version: str,
    title: str,
    description: Optional[str] = None,
) -> MajorSection:
    header = format_major_header(version, title)
    major = MajorSection(
        version=version if version.lower().startswith("v") else f"v{version}",
        title=title,
        description=description,
        header_raw=header,
        children=[],
    )
    if description:
        major.children.append(ProseBlock(raw=format_blockquote(description) + "\n"))
    plan.blocks.append(major)
    return major


def _find_major(plan: Plan, version: Optional[str]) -> Optional[MajorSection]:
    if not version:
        # last major
        for b in reversed(plan.blocks):
            if isinstance(b, MajorSection):
                return b
        return None
    key = _norm_version(version)
    for b in plan.blocks:
        if isinstance(b, MajorSection) and _norm_version(b.version) == key:
            return b
    return None


def create_iteration(
    plan: Plan,
    version: str,
    title: str,
    *,
    major: Optional[str] = None,
    goal: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
) -> Iteration:
    """
    Create a new iteration. If major is set (or a major exists), attach under
    that major; else top-level.
    """
    if plan.find_iteration(version) is not None:
        raise ValueError(f"Iteration {version} already exists")

    header = format_iteration_header(version, title, status)
    it = Iteration(
        version=version if version.lower().startswith("v") else f"v{version}",
        title=title,
        status=status,
        goal=goal,
        header_raw=header,
        tasks=[],
        body=[],
    )
    if description:
        it.body.append(ProseBlock(raw=format_blockquote(description)))
    if goal:
        it.body.append(ProseBlock(raw=format_goal_line(goal)))
        # blank line after goal is common but not required; powernote usually
        # goes straight to tasks without blank line after header

    maj = _find_major(plan, major)
    if maj is not None:
        maj.children.append(it)
    else:
        plan.blocks.append(it)
    return it


def set_iteration_goal(plan: Plan, version: str, goal: str) -> Iteration:
    it = plan.find_iteration(version)
    if it is None:
        raise ValueError(f"Iteration not found: {version}")
    it.goal = goal
    # Update or insert Goal prose in body
    goal_line = format_goal_line(goal)
    for i, node in enumerate(it.body):
        if isinstance(node, ProseBlock) and node.raw.lstrip().startswith("**Goal:**"):
            it.body[i] = ProseBlock(raw=goal_line)
            return it
    # Insert after optional leading blockquote
    insert_at = 0
    if it.body and isinstance(it.body[0], ProseBlock) and it.body[0].raw.lstrip().startswith(">"):
        insert_at = 1
    it.body.insert(insert_at, ProseBlock(raw=goal_line))
    return it


def add_task(
    plan: Plan,
    version: str,
    text: str,
    *,
    done: bool = False,
    agent: Optional[str] = None,
) -> Task:
    it = plan.find_iteration(version)
    if it is None:
        raise ValueError(f"Iteration not found: {version}")
    raw = format_task_line(text, done=done, agent=agent)
    task = Task(text=_strip_agent_tag(text) + _agent_suffix(agent).lstrip(), done=done, raw=raw)
    # Task.text for matching should be without forcing agent into search oddly —
    # store display text as written without the leading junk
    task.text = _strip_agent_tag(text) + (_agent_suffix(agent) if agent else "")
    if agent:
        task.text = _strip_agent_tag(text) + _agent_suffix(agent)
    else:
        task.text = text
    it.tasks.append(task)
    it.body.append(task)
    return task


def _match_task(it: Iteration, task_query: str) -> Task:
    q = task_query.lower().strip()
    # exact then substring
    for t in it.tasks:
        if t.text.lower().strip() == q:
            return t
    hits = [t for t in it.tasks if q in t.text.lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ValueError(f"No task matching {task_query!r} in {it.version}")
    raise ValueError(
        f"Ambiguous task {task_query!r} in {it.version}: "
        + "; ".join(t.text[:40] for t in hits[:5])
    )


def complete_task(
    plan: Plan, version: str, task: str, *, agent: Optional[str] = None
) -> Task:
    it = plan.find_iteration(version)
    if it is None:
        raise ValueError(f"Iteration not found: {version}")
    t = _match_task(it, task)
    t.done = True
    base = _strip_agent_tag(t.text)
    if agent:
        t.text = base + _agent_suffix(agent)
    else:
        t.text = base
    t.raw = format_task_line(base, done=True, agent=agent)
    return t


def reopen_task(
    plan: Plan, version: str, task: str, *, agent: Optional[str] = None
) -> Task:
    it = plan.find_iteration(version)
    if it is None:
        raise ValueError(f"Iteration not found: {version}")
    t = _match_task(it, task)
    t.done = False
    base = _strip_agent_tag(t.text)
    t.text = base + (_agent_suffix(agent) if agent else "")
    t.raw = format_task_line(base, done=False, agent=agent)
    return t


def add_iteration_prose(plan: Plan, version: str, text: str) -> None:
    it = plan.find_iteration(version)
    if it is None:
        raise ValueError(f"Iteration not found: {version}")
    it.body.append(ProseBlock(raw=_nl(text)))


def ensure_backlog(plan: Plan, title: str = "Future (Backlog)") -> BacklogSection:
    for b in plan.blocks:
        if isinstance(b, BacklogSection):
            return b
    sec = BacklogSection(title=title, header_raw=f"## {title}\n", items=[])
    plan.blocks.append(sec)
    return sec


def add_to_backlog(
    plan: Plan, text: str, *, agent: Optional[str] = None, checkbox: bool = False, done: bool = False
) -> BacklogItem:
    sec = ensure_backlog(plan)
    body = _strip_agent_tag(text) + _agent_suffix(agent)
    if checkbox:
        mark = "x" if done else " "
        raw = f"- [{mark}] {body}\n"
    else:
        raw = f"- {body}\n"
    item = BacklogItem(text=body, raw=raw)
    sec.items.append(item)
    return item


def load_plan_for_mutation(plan_path: Union[str, Path]) -> Plan:
    path = Path(plan_path)
    if path.is_file():
        return parse_plan_file(path)
    # create empty file shell
    plan = empty_plan()
    plan.path = path
    return plan


def save_plan(plan: Plan, plan_path: Optional[Union[str, Path]] = None) -> Path:
    with _file_lock:
        return write_plan_file(plan, plan_path)


def mutate_and_save(
    plan_path: Union[str, Path],
    mutator,
) -> Plan:
    """Load → mutator(plan) → save under file lock."""
    path = Path(plan_path)
    with _file_lock:
        if path.is_file():
            plan = parse_plan_file(path)
        else:
            plan = empty_plan()
            plan.path = path
        mutator(plan)
        write_plan_file(plan, path)
        return plan
