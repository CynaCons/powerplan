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
from typing import Callable, List, NamedTuple, Optional, Sequence, Union

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

_file_lock = threading.RLock()
_BATCH_CAP = 100


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
    """
    Append opaque prose at top level, above the backlog when one exists.

    A new block is separated from the section above it by a blank line, padded
    onto the new block so existing content is never rewritten (the same rule
    _pad_header applies to section headers). Without it, prose appended in the
    same batch as a preceding structural mutation would butt straight against
    that section — a re-parse between two separate calls supplies the blank
    line, so this keeps one batch byte-identical to N sequential calls.
    """
    raw = _nl(text)
    idx = _backlog_index(plan)
    tail = len(plan.blocks) if idx is None else idx
    if tail > 0 and isinstance(plan.blocks[tail - 1], ProseBlock):
        plan.blocks[tail - 1].raw += raw
    else:
        if tail > 0:
            nl = _doc_newline(plan)
            preceding = "".join(
                write_node(b) for b in plan.blocks[:tail]
            ).replace("\r\n", "\n")
            if preceding.strip() and not preceding.endswith("\n\n"):
                raw = (nl if preceding.endswith("\n") else nl + nl) + raw
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
    it.body.insert(_task_insert_index(it), task)
    return task


def add_tasks(
    plan: Plan,
    version: str,
    texts: Sequence[str],
    *,
    done: bool = False,
    agent: Optional[str] = None,
) -> List[Task]:
    """
    Append several checkbox tasks in one mutation (order preserved).

    Shared ``done`` / ``agent`` apply to every item. Empty list or any
    blank item refuses the whole batch so the writer never records a
    partial add.
    """
    if texts is None:
        raise ValueError("tasks must be a non-empty list of strings")
    items = list(texts)
    if not items:
        raise ValueError("tasks must be a non-empty list of strings")
    for i, raw in enumerate(items, start=1):
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"tasks[{i}] must be a non-empty string")
    if plan.find_iteration(version) is None:
        raise ValueError(f"Iteration not found: {version}")
    return [add_task(plan, version, text, done=done, agent=agent) for text in items]


def _trailing_blank_run(nodes: List) -> int:
    """Index of the first node in the trailing run of blank-only prose."""
    idx = len(nodes)
    while idx > 0:
        node = nodes[idx - 1]
        if isinstance(node, ProseBlock) and not node.raw.strip():
            idx -= 1
        else:
            break
    return idx


def _task_insert_index(it: Iteration) -> int:
    """
    Where a new task line belongs in an iteration body.

    After the last existing task, and always before trailing blank prose —
    section-separating blank lines are re-parsed into the preceding
    iteration's body, and appending past them buries one blank line per call.
    """
    for i in range(len(it.body) - 1, -1, -1):
        if isinstance(it.body[i], Task):
            return i + 1
    return _trailing_blank_run(it.body)


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


def _resolve_task(
    it: Iteration,
    *,
    task: Optional[str] = None,
    index: Optional[int] = None,
    expect: Optional[str] = None,
) -> Task:
    """
    Resolve one task of an iteration by text or by 1-based ordinal.

    Exactly one of ``task`` (substring match, same matcher the lifecycle tools
    use) or ``index`` is required. ``expect`` asserts the task's current text
    first — compare-and-swap for callers editing a plan that may have moved.
    Agent tags are ignored on both sides of that comparison so callers need not
    know whether a line carries one.
    """
    has_task = task is not None and str(task).strip() != ""
    has_index = index is not None

    if has_task and has_index:
        raise ValueError("Pass either task or index, not both")
    if not has_task and not has_index:
        raise ValueError("One of task or index is required")

    if has_index:
        try:
            idx = int(index)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ValueError(f"index must be an integer, got {index!r}")
        total = len(it.tasks)
        if total == 0:
            raise ValueError(f"{it.version} has no tasks to address")
        if idx < 1 or idx > total:
            raise ValueError(f"index {idx} out of range for {it.version} (1..{total})")
        found = it.tasks[idx - 1]
    else:
        found = _match_task(it, str(task))

    if expect is not None:
        want = _strip_agent_tag(str(expect)).strip()
        got = _strip_agent_tag(found.text).strip()
        if want != got:
            raise ValueError(
                f"expect mismatch in {it.version}: plan has {got!r}, expected {want!r}"
            )
    return found


def _normalize_address(
    *,
    task: Optional[str] = None,
    index: Optional[int] = None,
    tasks: Optional[Sequence[str]] = None,
    indexes: Optional[Sequence[int]] = None,
    expect: Optional[str] = None,
) -> tuple[Optional[List[int]], Optional[List[str]], Optional[str]]:
    """
    Fold scalar ``index``/``task`` into lists. Exactly one addressing mode.

    ``expect`` is only valid for a singular scalar address, not for ``indexes``
    / ``tasks`` arrays.
    """
    has_index = index is not None
    has_indexes = indexes is not None
    has_task = task is not None and str(task).strip() != ""
    has_tasks = tasks is not None

    if has_index and has_indexes:
        raise ValueError("Pass either index or indexes, not both")
    if has_task and has_tasks:
        raise ValueError("Pass either task or tasks, not both")
    index_mode = has_index or has_indexes
    text_mode = has_task or has_tasks
    if index_mode and text_mode:
        raise ValueError("Pass either index/indexes or task/tasks, not both")
    if not index_mode and not text_mode:
        raise ValueError(
            "One of task or index is required (or tasks/indexes for several)"
        )
    if expect is not None and (has_indexes or has_tasks):
        raise ValueError("expect is only valid when addressing a single task")

    idx_list: Optional[List[int]] = None
    task_list: Optional[List[str]] = None
    if has_index:
        idx_list = [index]  # type: ignore[list-item]
    elif has_indexes:
        idx_list = list(indexes)  # type: ignore[arg-type]
        if not idx_list:
            raise ValueError("indexes must be a non-empty list")
    elif has_task:
        task_list = [str(task)]
    else:
        task_list = list(tasks)  # type: ignore[arg-type]
        if not task_list:
            raise ValueError("tasks must be a non-empty list of strings")
        for i, raw in enumerate(task_list, start=1):
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"tasks[{i}] must be a non-empty string")

    n = len(idx_list or task_list or [])
    if n > _BATCH_CAP:
        raise ValueError(f"batch size {n} exceeds cap of {_BATCH_CAP}")
    return idx_list, task_list, expect


def _resolve_many(
    it: Iteration,
    *,
    task: Optional[str] = None,
    index: Optional[int] = None,
    tasks: Optional[Sequence[str]] = None,
    indexes: Optional[Sequence[int]] = None,
    expect: Optional[str] = None,
) -> List[tuple[int, Task]]:
    """
    Resolve every address against the current task list before any mutation.

    Returns (original 1-based index, task) in caller order. Duplicate targets
    (same Task identity) are an error so remove/defer cannot be applied twice.
    """
    idx_list, task_list, expect = _normalize_address(
        task=task, index=index, tasks=tasks, indexes=indexes, expect=expect
    )
    found: List[tuple[int, Task]] = []
    seen: set[int] = set()
    singular_expect = expect if (idx_list and len(idx_list) == 1) or (
        task_list and len(task_list) == 1
    ) else None

    if idx_list is not None:
        for raw in idx_list:
            t = _resolve_task(it, index=raw, expect=singular_expect)
            ident = id(t)
            if ident in seen:
                raise ValueError(f"duplicate target in {it.version}: index {raw}")
            seen.add(ident)
            found.append((int(raw), t))
        return found

    assert task_list is not None
    pos = {id(x): i for i, x in enumerate(it.tasks, start=1)}
    for raw in task_list:
        t = _resolve_task(it, task=raw, expect=singular_expect)
        ident = id(t)
        if ident in seen:
            raise ValueError(f"duplicate target in {it.version}: {raw!r}")
        seen.add(ident)
        found.append((pos[ident], t))
    return found


def _iteration_or_raise(plan: Plan, version: str) -> Iteration:
    it = plan.find_iteration(version)
    if it is None:
        raise ValueError(f"Iteration not found: {version}")
    return it


def _existing_agent(text: str) -> Optional[str]:
    hit = re.search(r"\[agent:\s*([^\]]+)\]\s*$", text)
    return hit.group(1).strip() if hit else None


def _drop_task(it: Iteration, target: Task) -> None:
    """Remove by identity — equal-valued tasks must not be confused."""
    it.tasks = [t for t in it.tasks if t is not target]
    it.body = [n for n in it.body if n is not target]


def _rewrite_task(t: Task, *, text: str, agent: Optional[str]) -> Task:
    new_text = "" if text is None else str(text)
    if not new_text.strip():
        raise ValueError("text must be a non-empty string")
    base = _strip_agent_tag(new_text)
    tag = agent if agent is not None else _existing_agent(t.text)
    t.text = base + _agent_suffix(tag)
    t.raw = format_task_line(base, done=t.done, agent=tag)
    return t


def _set_task_done(t: Task, done: bool, agent: Optional[str]) -> Task:
    t.done = done
    base = _strip_agent_tag(t.text)
    if done:
        if agent:
            t.text = base + _agent_suffix(agent)
        else:
            t.text = base
        t.raw = format_task_line(base, done=True, agent=agent)
    else:
        t.text = base + (_agent_suffix(agent) if agent else "")
        t.raw = format_task_line(base, done=False, agent=agent)
    return t


def update_task(
    plan: Plan,
    version: str,
    *,
    text: Optional[str] = None,
    task: Optional[str] = None,
    index: Optional[int] = None,
    expect: Optional[str] = None,
    agent: Optional[str] = None,
    changes: Optional[Sequence] = None,
) -> List[tuple[int, Task]]:
    """Rewrite task text in place, preserving done state. One row or ``changes``."""
    it = _iteration_or_raise(plan, version)
    if changes is not None:
        singular_used = any(
            v is not None for v in (text, task, index, expect)
        )
        if singular_used:
            raise ValueError("Pass either a single task update or changes, not both")
        if not isinstance(changes, (list, tuple)) or not changes:
            raise ValueError("changes must be a non-empty list")
        if len(changes) > _BATCH_CAP:
            raise ValueError(f"batch size {len(changes)} exceeds cap of {_BATCH_CAP}")
        resolved: List[tuple[int, Task, str]] = []
        seen: set[int] = set()
        pos = {id(x): i for i, x in enumerate(it.tasks, start=1)}
        for i, ch in enumerate(changes, start=1):
            if not isinstance(ch, dict):
                raise ValueError(f"changes[{i}] must be an object")
            new_text = ch.get("text")
            if new_text is None or not str(new_text).strip():
                raise ValueError(f"changes[{i}].text must be a non-empty string")
            t = _resolve_task(
                it,
                task=ch.get("task"),
                index=ch.get("index"),
                expect=ch.get("expect"),
            )
            ident = id(t)
            if ident in seen:
                raise ValueError(f"duplicate target in changes[{i}]")
            seen.add(ident)
            resolved.append((pos[ident], t, str(new_text)))
        out: List[tuple[int, Task]] = []
        for orig, t, new_text in resolved:
            _rewrite_task(t, text=new_text, agent=agent)
            out.append((orig, t))
        return out

    if text is None or not str(text).strip():
        raise ValueError("text must be a non-empty string")
    pairs = _resolve_many(it, task=task, index=index, expect=expect)
    return [(orig, _rewrite_task(t, text=text, agent=agent)) for orig, t in pairs]


def remove_task(
    plan: Plan,
    version: str,
    *,
    task: Optional[str] = None,
    index: Optional[int] = None,
    expect: Optional[str] = None,
    tasks: Optional[Sequence[str]] = None,
    indexes: Optional[Sequence[int]] = None,
) -> List[tuple[int, Task]]:
    """Delete one or many tasks (task list and body). Resolve all, then drop."""
    it = _iteration_or_raise(plan, version)
    pairs = _resolve_many(
        it, task=task, index=index, expect=expect, tasks=tasks, indexes=indexes
    )
    for _, t in pairs:
        _drop_task(it, t)
    return pairs


def defer_task(
    plan: Plan,
    version: str,
    *,
    task: Optional[str] = None,
    index: Optional[int] = None,
    reason: Optional[str] = None,
    expect: Optional[str] = None,
    agent: Optional[str] = None,
    tasks: Optional[Sequence[str]] = None,
    indexes: Optional[Sequence[int]] = None,
) -> List[tuple[int, Task, BacklogItem]]:
    """Move one or many tasks out of an iteration and into the backlog."""
    it = _iteration_or_raise(plan, version)
    pairs = _resolve_many(
        it, task=task, index=index, expect=expect, tasks=tasks, indexes=indexes
    )
    note = f"deferred from {it.version}"
    if reason and str(reason).strip():
        note = f"{note}: {str(reason).strip()}"
    out: List[tuple[int, Task, BacklogItem]] = []
    for orig, t in pairs:
        base = _strip_agent_tag(t.text)
        _drop_task(it, t)
        tag = agent if agent is not None else _existing_agent(t.text)
        item = add_to_backlog(plan, f"{base} ({note})", agent=tag)
        out.append((orig, t, item))
    return out


def complete_task(
    plan: Plan,
    version: str,
    task: Optional[str] = None,
    *,
    index: Optional[int] = None,
    expect: Optional[str] = None,
    agent: Optional[str] = None,
    tasks: Optional[Sequence[str]] = None,
    indexes: Optional[Sequence[int]] = None,
) -> List[tuple[int, Task]]:
    it = _iteration_or_raise(plan, version)
    pairs = _resolve_many(
        it, task=task, index=index, expect=expect, tasks=tasks, indexes=indexes
    )
    return [(orig, _set_task_done(t, True, agent)) for orig, t in pairs]


def reopen_task(
    plan: Plan,
    version: str,
    task: Optional[str] = None,
    *,
    index: Optional[int] = None,
    expect: Optional[str] = None,
    agent: Optional[str] = None,
    tasks: Optional[Sequence[str]] = None,
    indexes: Optional[Sequence[int]] = None,
) -> List[tuple[int, Task]]:
    it = _iteration_or_raise(plan, version)
    pairs = _resolve_many(
        it, task=task, index=index, expect=expect, tasks=tasks, indexes=indexes
    )
    return [(orig, _set_task_done(t, False, agent)) for orig, t in pairs]


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


def _append_backlog_item(
    plan: Plan,
    text: str,
    *,
    agent: Optional[str] = None,
    checkbox: bool = False,
    done: bool = False,
) -> BacklogItem:
    sec = ensure_backlog(plan)
    body = _strip_agent_tag(text) + _agent_suffix(agent)
    if checkbox:
        mark = "x" if done else " "
        raw = f"- [{mark}] {body}\n"
    else:
        raw = f"- {body}\n"
    item = BacklogItem(text=body, raw=raw)
    sec.items.insert(_trailing_blank_run(sec.items), item)
    return item


def add_to_backlog(
    plan: Plan,
    text: Optional[str] = None,
    *,
    texts: Optional[Sequence[str]] = None,
    agent: Optional[str] = None,
    checkbox: bool = False,
    done: bool = False,
):
    """Append one backlog item (``text``) or many (``texts``) in one mutation."""
    if text is not None and texts is not None:
        raise ValueError("Pass either text or texts, not both")
    if texts is not None:
        items = list(texts)
        if not items:
            raise ValueError("texts must be a non-empty list of strings")
        if len(items) > _BATCH_CAP:
            raise ValueError(f"batch size {len(items)} exceeds cap of {_BATCH_CAP}")
        for i, raw in enumerate(items, start=1):
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"texts[{i}] must be a non-empty string")
        return [
            _append_backlog_item(
                plan, raw, agent=agent, checkbox=checkbox, done=done
            )
            for raw in items
        ]
    if text is None:
        raise ValueError("text is required")
    return _append_backlog_item(
        plan, text, agent=agent, checkbox=checkbox, done=done
    )


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
    dry_run: bool = False,
) -> Plan:
    """
    Load → mutator(plan) → save under file lock.

    If the file is missing and ``allow_create`` is False, raise FileNotFoundError
    (callers should use create_plan). When True, start from empty_plan().

    With ``dry_run`` the plan is parsed, mutated and normalized exactly as
    usual, but never written: the mutated Plan is returned and discarded by the
    caller. Everything a real call would raise it still raises, so a dry run is
    an honest pre-flight rather than a weaker check.
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
        if not dry_run:
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


# ---------------------------------------------------------------------------
# apply_ops — heterogeneous atomic batches (v0.11.0)
# ---------------------------------------------------------------------------
#
# INVARIANT: an op adapter must only mutate the in-memory Plan it is handed.
# It must never call save_plan / write_plan_file / mutate_and_save / create_plan,
# because apply_ops runs the whole list inside one mutate_and_save: a nested
# write would break all-or-nothing and (before _file_lock became an RLock)
# deadlock. Every adapter below delegates to a pure in-memory mutation above.

_OPS_CAP = 50

# How an op's "version" key behaves.
_V_ADDRESSES = "addresses"  # names an existing iteration — inherits the default
_V_OWN = "own"              # names a NEW section — must always be explicit
_V_NONE = "none"            # the op has no version at all — key is rejected


class _OpSpec(NamedTuple):
    apply: Callable          # (plan, version, args) -> summary dict
    required: frozenset      # keys that must be present (minus "op"/"version")
    optional: frozenset      # keys that may be present
    version_mode: str
    inherit_agent: bool      # may the batch-level agent default flow in?


def _pair_count(result) -> dict:
    return {"count": len(result or [])}


def _op_add_to_backlog(plan: Plan, version: Optional[str], a: dict) -> dict:
    """``add_to_backlog`` returns one item or a list; normalize to a count."""
    result = add_to_backlog(
        plan,
        a.get("text"),
        texts=a.get("texts"),
        agent=a.get("agent"),
        checkbox=bool(a.get("checkbox", False)),
    )
    return {"count": len(result) if isinstance(result, list) else 1}


def _spec_table() -> "dict[str, _OpSpec]":
    """
    Op name -> spec. Names are the existing MCP tool names and the keys are the
    existing tool schemas' properties, so there is nothing new to learn.

    ``inherit_agent`` is False wherever the underlying function has no ``agent``
    parameter, and deliberately False for update_task: _rewrite_task replaces an
    existing [agent: x] tag whenever agent is not None, so letting a batch-level
    default reach it would silently relabel other agents' work. An explicit
    ``agent`` inside the update_task op still works.
    """
    return {
        "create_major": _OpSpec(
            lambda p, v, a: (
                create_major(p, v, a["title"], description=a.get("description")),
                {"version": v},
            )[1],
            frozenset({"title"}), frozenset({"description"}), _V_OWN, False,
        ),
        "create_iteration": _OpSpec(
            lambda p, v, a: (
                create_iteration(
                    p, v, a["title"],
                    major=a.get("major"), goal=a.get("goal"),
                    status=a.get("status"), description=a.get("description"),
                ),
                {"version": v},
            )[1],
            frozenset({"title"}),
            frozenset({"major", "goal", "status", "description"}),
            _V_OWN, False,
        ),
        "set_iteration_goal": _OpSpec(
            lambda p, v, a: (set_iteration_goal(p, v, a["goal"]), {"version": v})[1],
            frozenset({"goal"}), frozenset(), _V_ADDRESSES, False,
        ),
        "add_task": _OpSpec(
            lambda p, v, a: (
                add_task(p, v, a["text"], done=bool(a.get("done", False)),
                         agent=a.get("agent")),
                {"version": v, "count": 1},
            )[1],
            frozenset({"text"}), frozenset({"done", "agent"}), _V_ADDRESSES, True,
        ),
        "add_tasks": _OpSpec(
            lambda p, v, a: {
                "version": v,
                "count": len(add_tasks(
                    p, v, a["tasks"], done=bool(a.get("done", False)),
                    agent=a.get("agent"),
                )),
            },
            frozenset({"tasks"}), frozenset({"done", "agent"}), _V_ADDRESSES, True,
        ),
        "complete_task": _OpSpec(
            lambda p, v, a: {
                "version": v,
                **_pair_count(complete_task(p, v, **_addr(a), agent=a.get("agent"))),
            },
            frozenset(), _ADDR_KEYS | frozenset({"agent"}), _V_ADDRESSES, True,
        ),
        "reopen_task": _OpSpec(
            lambda p, v, a: {
                "version": v,
                **_pair_count(reopen_task(p, v, **_addr(a), agent=a.get("agent"))),
            },
            frozenset(), _ADDR_KEYS | frozenset({"agent"}), _V_ADDRESSES, True,
        ),
        "update_task": _OpSpec(
            lambda p, v, a: {
                "version": v,
                **_pair_count(update_task(
                    p, v,
                    text=a.get("text"), task=a.get("task"), index=a.get("index"),
                    expect=a.get("expect"), changes=a.get("changes"),
                    agent=a.get("agent"),
                )),
            },
            frozenset(),
            frozenset({"text", "task", "index", "expect", "changes", "agent"}),
            _V_ADDRESSES, False,
        ),
        "remove_task": _OpSpec(
            lambda p, v, a: {
                "version": v, **_pair_count(remove_task(p, v, **_addr(a))),
            },
            frozenset(), _ADDR_KEYS, _V_ADDRESSES, False,
        ),
        "defer_task": _OpSpec(
            lambda p, v, a: {
                "version": v,
                **_pair_count(defer_task(
                    p, v, **_addr(a), reason=a.get("reason"), agent=a.get("agent"),
                )),
            },
            frozenset(), _ADDR_KEYS | frozenset({"reason", "agent"}),
            _V_ADDRESSES, True,
        ),
        "add_to_backlog": _OpSpec(
            _op_add_to_backlog,
            frozenset(), frozenset({"text", "texts", "agent", "checkbox"}),
            _V_NONE, True,
        ),
        "append_prose": _OpSpec(
            lambda p, v, a: (append_prose(p, a["text"]), {})[1],
            frozenset({"text"}), frozenset(), _V_NONE, False,
        ),
        "start_iteration": _OpSpec(
            lambda p, v, a: (start_iteration(p, v), {"version": v})[1],
            frozenset(), frozenset(), _V_ADDRESSES, False,
        ),
        "close_iteration": _OpSpec(
            lambda p, v, a: (
                close_iteration(
                    p, v, force=bool(a.get("force", False)), stamp=a.get("stamp"),
                ),
                {"version": v},
            )[1],
            frozenset(), frozenset({"force", "stamp"}), _V_ADDRESSES, False,
        ),
    }


_ADDR_KEYS = frozenset({"task", "index", "expect", "tasks", "indexes"})

# Ops that drop rows, so 1-based indexes after them refer to different tasks.
_SHIFTING_OPS = frozenset({"remove_task", "defer_task"})


def _addr(a: dict) -> dict:
    """The five addressing keys, omitted when absent (so defaults stay in play)."""
    return {k: a[k] for k in _ADDR_KEYS if k in a}


def _op_names() -> list:
    return sorted(_spec_table())


def apply_ops(
    plan: Plan,
    ops: Sequence[dict],
    *,
    version: Optional[str] = None,
    agent: Optional[str] = None,
) -> dict:
    """
    Apply a heterogeneous list of mutating ops to ``plan``, in order.

    Pure in-memory: the caller wraps this in one mutate_and_save, so either every
    op lands or PLAN.md is left untouched. Ops see the plan as earlier ops left
    it, which is what makes create-then-populate-then-close work in one call.

    ``version`` is the default for ops that address an existing iteration and
    omit their own. It is resolved **once, before the first op**, so a
    start_iteration or close_iteration inside the batch cannot silently move
    where later ops land. ``agent`` is the default only for ops whose underlying
    function takes one (see _spec_table).

    Returns a summary dict; raises ValueError (never TypeError/AttributeError)
    for any malformed op, with the op's 0-based position in the message.
    """
    table = _spec_table()

    if not isinstance(ops, (list, tuple)) or not ops:
        raise ValueError("ops must be a non-empty list of operations")
    if len(ops) > _OPS_CAP:
        raise ValueError(f"batch size {len(ops)} exceeds cap of {_OPS_CAP} ops")

    # Resolve the default iteration once, up front.
    default_version: Optional[str] = None
    if version is not None and str(version).strip():
        default_version = str(version).strip()
    else:
        cur = plan.current_iteration()
        if cur is not None:
            default_version = cur.version

    # ---- shape validation: every op, before the first mutation runs ----
    prepared: List[tuple[int, str, _OpSpec, Optional[str], dict]] = []
    for i, raw in enumerate(ops):
        if not isinstance(raw, dict):
            raise ValueError(f"ops[{i}] must be an object")
        name = raw.get("op")
        if not name or not isinstance(name, str):
            raise ValueError(f"ops[{i}].op is required (one of: {', '.join(_op_names())})")
        spec = table.get(name)
        if spec is None:
            raise ValueError(
                f"ops[{i}].op {name!r} is not a known operation "
                f"(one of: {', '.join(_op_names())})"
            )
        args = {k: v for k, v in raw.items() if k != "op"}

        allowed = spec.required | spec.optional
        if spec.version_mode != _V_NONE:
            allowed = allowed | frozenset({"version"})
        unknown = sorted(set(args) - allowed)
        if unknown:
            raise ValueError(
                f"ops[{i}] ({name}): unknown key(s) {', '.join(unknown)}; "
                f"allowed: {', '.join(sorted(allowed)) or 'none'}"
            )
        missing = sorted(spec.required - set(args))
        if missing:
            raise ValueError(f"ops[{i}] ({name}): missing required key(s) {', '.join(missing)}")

        own = args.get("version")
        own = str(own).strip() if own is not None and str(own).strip() else None
        if spec.version_mode == _V_NONE:
            resolved = None
        elif spec.version_mode == _V_OWN:
            if own is None:
                raise ValueError(
                    f"ops[{i}] ({name}): version is required and is never inherited, "
                    "because it names a new section rather than an existing one"
                )
            resolved = own
        else:
            resolved = own or default_version
            if resolved is None:
                raise ValueError(
                    f"ops[{i}] ({name}): version is required — pass it on the op, or a "
                    "batch-level version, or mark an iteration current first"
                )

        if spec.inherit_agent and agent is not None and "agent" not in args:
            args["agent"] = agent

        prepared.append((i, name, spec, resolved, args))

    # ---- index-shift guard: only remove/defer renumber rows ----
    dropped_in: dict = {}
    for i, name, spec, resolved, args in prepared:
        if ("index" in args or "indexes" in args) and resolved in dropped_in:
            raise ValueError(
                f"ops[{i}] ({name}): addresses {resolved} by index, but ops"
                f"[{dropped_in[resolved]}] already dropped a task there, so 1-based "
                "indexes have shifted. Address these by text (task/tasks) instead, "
                "or order the removals last."
            )
        if name in _SHIFTING_OPS:
            dropped_in.setdefault(resolved, i)

    # ---- apply ----
    summaries: List[dict] = []
    for i, name, spec, resolved, args in prepared:
        try:
            summary = spec.apply(plan, resolved, args)
        except (ValueError, KeyError) as exc:
            raise _OpFailed(i, name, str(exc)) from exc
        except TypeError as exc:  # a bad arg type reaching a mutation function
            raise _OpFailed(i, name, f"invalid arguments: {exc}") from exc
        summaries.append({"i": i, "op": name, **(summary or {})})

    report = check_plan(plan)
    return {
        "applied": len(summaries),
        "ops": summaries,
        "resolved_version": default_version,
        "check": {
            "ok": report.get("ok"),
            "issue_count": report.get("issue_count"),
        },
    }


class _OpFailed(ValueError):
    """A single op raised; carries which one so the caller can locate it."""

    def __init__(self, i: int, op: str, message: str):
        super().__init__(f"ops[{i}] ({op}): {message}")
        self.i = i
        self.op = op
        self.reason = message
