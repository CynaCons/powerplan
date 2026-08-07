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
from .plan_writer import write_node, write_plan, write_plan_file

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


def _backlog_index(plan: Plan) -> Optional[int]:
    """Index of the first BacklogSection, or None when the plan has no backlog."""
    for i, block in enumerate(plan.blocks):
        if isinstance(block, BacklogSection):
            return i
    return None


def _doc_newline(plan: Plan) -> str:
    """CRLF when the document already uses it, else LF."""
    for block in plan.blocks:
        raw = getattr(block, "raw", "") or getattr(block, "header_raw", "")
        if raw and "\r\n" in raw:
            return "\r\n"
    return "\n"


def _pad_header(node, preceding: str, nl: str) -> None:
    """
    Ensure a blank line separates ``node``'s header from ``preceding`` text.

    The padding goes on the new node's own header rather than on the previous
    block, so existing content is never rewritten.
    """
    # Parsed headers never carry leading newlines — only this function adds
    # them, so stripping first makes repeated normalization idempotent.
    header = (node.header_raw or "").lstrip("\r\n")
    normalized = preceding.replace("\r\n", "\n")
    if not preceding.strip() or normalized.endswith("\n\n"):
        node.header_raw = header
        return
    pad = nl if normalized.endswith("\n") else nl + nl
    node.header_raw = pad + header


def _insert_top_level(plan: Plan, node) -> None:
    """
    Insert a top-level node, keeping the backlog pinned as the final section.

    Every structural top-level mutation goes through here; a plain ``append``
    would strand the backlog mid-document once one exists.
    """
    idx = _backlog_index(plan)
    if idx is None:
        idx = len(plan.blocks)
    if isinstance(node, (MajorSection, BacklogSection, Iteration)):
        preceding = "".join(write_node(b) for b in plan.blocks[:idx])
        _pad_header(node, preceding, _doc_newline(plan))
    plan.blocks.insert(idx, node)


def _append_major_child(major: MajorSection, node) -> None:
    """Append under a major, padding structural headers off previous content."""
    if isinstance(node, (Iteration, MajorSection)):
        preceding = "".join(write_node(c) for c in major.children)
        if preceding:
            nl = "\r\n" if "\r\n" in preceding else "\n"
            _pad_header(node, preceding, nl)
    major.children.append(node)


_RE_RULE = re.compile(r"^[-*_]{3,}$")


def _trim_trailing_rule(raw: str) -> str:
    """Drop trailing horizontal rules (and the blank lines around them)."""
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # text ended with a newline
    removed = False
    while lines:
        tail = lines[-1].strip()
        if not tail:
            lines.pop()
        elif _RE_RULE.match(tail):
            lines.pop()
            removed = True
        else:
            break
    if not removed:
        return raw
    body = nl.join(lines)
    return body + nl if body else ""


def _strip_trailing_dividers(section: BacklogSection) -> None:
    """
    Drop a trailing horizontal rule from a relocated backlog.

    The parser absorbs whatever follows a backlog header into that section, so
    a ``---`` that separated the backlog from later majors rides along when the
    section moves and lands as a dangling rule at end of file. Trailing prose is
    merged before trimming because the rule is often embedded in the same block
    as real content; merging is byte-neutral since the writer concatenates raws.
    """
    buf: List[ProseBlock] = []
    while section.items and isinstance(section.items[-1], ProseBlock):
        buf.append(section.items.pop())
    if not buf:
        return
    buf.reverse()
    trimmed = _trim_trailing_rule("".join(n.raw for n in buf))
    if trimmed:
        section.items.append(ProseBlock(raw=trimmed))


def normalize_plan(plan: Plan) -> Plan:
    """
    Enforce document invariants on a mutated plan before it is written.

    1. Backlog section(s) are the final blocks of the document.
    2. A blank line precedes every top-level section header.

    Only the save path calls this, so an unmutated parse -> write round-trip
    stays byte-identical; plans are healed the first time they are touched.
    """
    backlogs = [b for b in plan.blocks if isinstance(b, BacklogSection)]
    if backlogs:
        rest = [b for b in plan.blocks if not isinstance(b, BacklogSection)]
        relocated = plan.blocks != rest + backlogs
        plan.blocks = rest + backlogs
        if relocated:
            # A divider that separated the backlog from the sections below it
            # has nothing left to separate once the backlog moves to the end.
            _strip_trailing_dividers(backlogs[-1])

    nl = _doc_newline(plan)
    seen = ""
    for block in plan.blocks:
        if isinstance(block, (MajorSection, BacklogSection, Iteration)):
            _pad_header(block, seen, nl)
        if isinstance(block, MajorSection):
            child_seen = block.header_raw or ""
            for child in block.children:
                if isinstance(child, Iteration):
                    _pad_header(child, child_seen, nl)
                child_seen += write_node(child)
        seen += write_node(block)
    return plan


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
    """Append opaque prose at top level, above the backlog when one exists."""
    raw = _nl(text)
    idx = _backlog_index(plan)
    tail = len(plan.blocks) if idx is None else idx
    if tail > 0 and isinstance(plan.blocks[tail - 1], ProseBlock):
        plan.blocks[tail - 1].raw += raw
    else:
        plan.blocks.insert(tail, ProseBlock(raw=raw))
    return plan


def add_separator(plan: Plan) -> Plan:
    """Append a markdown horizontal rule block (powernote section divider)."""
    # Prefer separator as its own prose chunk for clarity
    _insert_top_level(plan, ProseBlock(raw="\n---\n\n"))
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
    _insert_top_level(plan, major)
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
        _append_major_child(maj, it)
    else:
        _insert_top_level(plan, it)
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
    # No backlog yet, so this lands at the end — where it must stay.
    _insert_top_level(plan, sec)
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
    plan = empty_plan()
    plan.path = path
    return plan


def save_plan(plan: Plan, plan_path: Optional[Union[str, Path]] = None) -> Path:
    with _file_lock:
        normalize_plan(plan)
        return write_plan_file(plan, plan_path)


def mutate_and_save(
    plan_path: Union[str, Path],
    mutator,
    *,
    allow_create: bool = False,
) -> Plan:
    """
    Load → mutator(plan) → save under file lock.

    If the file is missing and ``allow_create`` is False, raise FileNotFoundError
    (callers should use create_plan). When True, start from empty_plan().
    """
    path = Path(plan_path)
    with _file_lock:
        if path.is_file():
            plan = parse_plan_file(path)
        elif allow_create:
            plan = empty_plan()
            plan.path = path
        else:
            raise FileNotFoundError(
                f"No PLAN.md at {path}. Use create_plan(plan_path=...) first."
            )
        mutator(plan)
        normalize_plan(plan)
        write_plan_file(plan, path)
        return plan


def create_plan(
    *,
    title: str,
    goal: Optional[str] = None,
    philosophy: Optional[str] = None,
    plan_path: Union[str, Path],
    force: bool = False,
    seed_major: bool = True,
) -> Plan:
    """
    Bootstrap a new powernote-style PLAN.md.

    Refuses to overwrite an existing file unless ``force=True``.
    """
    path = Path(plan_path)
    if path.is_file() and not force:
        raise FileExistsError(
            f"Plan already exists: {path}. Pass force=true to overwrite."
        )
    if not path.parent.is_dir():
        raise FileNotFoundError(f"Parent directory does not exist: {path.parent}")

    title = (title or "Implementation Plan").strip()
    lines = [f"# {title}\n", "\n"]
    if goal:
        lines.append(f"**Goal:** {goal.strip()}\n")
        lines.append("\n")
    if philosophy:
        lines.append(f"**Philosophy:** {philosophy.strip()}\n")
        lines.append("\n")
    lines.append("---\n")
    lines.append("\n")

    plan = Plan(title=title, path=path, blocks=[ProseBlock(raw="".join(lines))])
    if seed_major:
        create_major(plan, "v0.1", "Foundation", description="First iteration group")
        create_iteration(
            plan,
            "v0.1.0",
            "Bootstrap",
            major="v0.1",
            goal=goal or "Stand up the project",
        )
        add_task(plan, "v0.1.0", "Define first tasks", done=False)

    with _file_lock:
        write_plan_file(plan, path)
    return plan


def _set_iteration_status(it: Iteration, status: Optional[str]) -> None:
    """Update status field and rewrite header_raw in managed style."""
    it.status = status
    # Preserve version/title; rebuild header with optional (STATUS)
    it.header_raw = format_iteration_header(it.version, it.title, status=status)


def start_iteration(plan: Plan, version: str) -> Iteration:
    """Mark iteration ACTIVE (current work). Clears ACTIVE from siblings."""
    it = plan.find_iteration(version)
    if it is None:
        raise ValueError(f"Iteration not found: {version}")
    for other in plan.all_iterations():
        if other is it:
            continue
        st = (other.status or "").upper()
        if st in ("ACTIVE", "IN PROGRESS", "WIP", "CURRENT", "NEXT"):
            _set_iteration_status(other, None)
        # strip (current) from titles of others
        if re.search(r"\s*\(current\)\s*$", other.title, re.I):
            other.title = re.sub(r"\s*\(current\)\s*$", "", other.title, flags=re.I).strip()
            _set_iteration_status(other, other.status)
    _set_iteration_status(it, "ACTIVE")
    if not re.search(r"\bcurrent\b", it.title, re.I):
        it.title = f"{it.title} (current)"
        _set_iteration_status(it, "ACTIVE")
    return it


def close_iteration(
    plan: Plan, version: str, *, force: bool = False, stamp: Optional[str] = None
) -> Iteration:
    """
    Mark iteration COMPLETE. If open tasks remain, requires force=True.
    Optional stamp appended to title (e.g. date).
    """
    it = plan.find_iteration(version)
    if it is None:
        raise ValueError(f"Iteration not found: {version}")
    open_n = sum(1 for t in it.tasks if not t.done)
    if open_n and not force:
        raise ValueError(
            f"Iteration {version} has {open_n} open task(s). "
            "Pass force=true to close anyway."
        )
    # strip (current) from title
    it.title = re.sub(r"\s*\(current\)\s*$", "", it.title, flags=re.I).strip()
    if stamp:
        stamp = stamp.strip()
        if stamp and stamp not in it.title:
            it.title = f"{it.title} ({stamp})"
    _set_iteration_status(it, "COMPLETE")
    return it


def check_plan(plan: Plan) -> dict:
    """
    Minimal structure lint. Returns dict with ok, issues[], summary.
    """
    issues: List[dict] = []
    iterations = plan.all_iterations()
    versions = [it.version for it in iterations]

    # Duplicate versions
    seen = set()
    for v in versions:
        key = _norm_version(v)
        if key in seen:
            issues.append(
                {"code": "duplicate_version", "version": v, "message": f"Duplicate iteration version {v}"}
            )
        seen.add(key)

    # Malformed: empty titles
    for it in iterations:
        if not (it.title or "").strip():
            issues.append(
                {
                    "code": "empty_title",
                    "version": it.version,
                    "message": f"Iteration {it.version} has empty title",
                }
            )

    # Multiple ACTIVE / current markers
    active = [
        it
        for it in iterations
        if (it.status or "").upper() in ("ACTIVE", "IN PROGRESS", "WIP", "CURRENT")
        or re.search(r"\bcurrent\b", it.title, re.I)
    ]
    if len(active) > 1:
        issues.append(
            {
                "code": "multiple_current",
                "versions": [a.version for a in active],
                "message": "Multiple iterations marked current/ACTIVE",
            }
        )

    # COMPLETE with open tasks
    for it in iterations:
        st = (it.status or "").upper()
        if "COMPLETE" in st or "CLOSED" in st or "DONE" in st:
            open_n = sum(1 for t in it.tasks if not t.done)
            if open_n:
                issues.append(
                    {
                        "code": "complete_with_open_tasks",
                        "version": it.version,
                        "open": open_n,
                        "message": f"{it.version} marked complete but has {open_n} open task(s)",
                    }
                )

    # Backlog must be the final section (any mutation relocates it)
    bidx = _backlog_index(plan)
    if bidx is not None:
        trailing = [
            b
            for b in plan.blocks[bidx + 1 :]
            if not isinstance(b, BacklogSection)
            and not (isinstance(b, ProseBlock) and not b.raw.strip())
        ]
        if trailing:
            issues.append(
                {
                    "code": "content_after_backlog",
                    "count": len(trailing),
                    "message": (
                        f"{len(trailing)} block(s) follow the backlog section; "
                        "the backlog must be last (next mutation will relocate it)"
                    ),
                }
            )

    cur = plan.current_iteration()
    return {
        "ok": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
        "iteration_count": len(iterations),
        "current": cur.version if cur else None,
        "task_progress": {
            "done": sum(it.done_count for it in iterations),
            "total": sum(it.total_count for it in iterations),
        },
    }
