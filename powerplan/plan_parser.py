"""
Tolerant PLAN.md parser.

Recognizes the managed powernote-style format (``## vX.Y`` majors,
``### vX.Y.Z`` iterations) and freeform plans with the same iteration/task
markers. Phase-like headers and everything else become ProseBlock nodes with
raw text preserved exactly (including line endings) so write_plan can
round-trip byte-identical.
"""

from __future__ import annotations

import re
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
)

# ### v2.3.2 - Title   /   ### v0.1.0 — Title
_RE_ITERATION = re.compile(
    r"^(###)\s+(v?\d+\.\d+\.\d+)\s*([-—–])\s*(.+?)\s*$"
)

# Phase-like headers are NOT structural — matched only so we close open
# containers and emit opaque prose at the right nesting level.
_RE_PHASE_LIKE = re.compile(r"^#\s+Phase\s+(\d+)\s*:\s*(.+?)\s*$", re.IGNORECASE)

# ## v0.1 — Title  (major section; not ## Quick Summary / ## Backlog)
_RE_MAJOR = re.compile(r"^##\s+(v?\d+\.\d+)\s*([-—–])\s*(.+?)\s*$")

# Backlog section headers only (not versioned titles that mention "backlog")
# Matches: "## Backlog", "# Backlog (...)", "## Future (Backlog)", ...
_RE_BACKLOG = re.compile(
    r"^(#{1,3})\s+((?:Future\s*\(\s*Backlog\s*\)|Backlog\b).*)$",
    re.IGNORECASE,
)

# Checkbox tasks
_RE_TASK = re.compile(r"^(-|\*)\s+\[([ xX])\]\s+(.*)$")

# Plain backlog bullets (no checkbox)
_RE_BULLET = re.compile(r"^(-|\*)\s+(?!\[[ xX]\])(.*)$")

# **Goal:** ...
_RE_GOAL = re.compile(r"^\*\*Goal:\*\*\s*(.*)$", re.IGNORECASE)

# Status keywords for header extraction
_STATUS_HINT = re.compile(
    r"(COMPLETE|CLOSED|DONE|ACTIVE|IN PROGRESS|NEXT|WIP|BLOCKED|"
    r"FAILED|REOPEN(?:ED)?|DRASTIC)",
    re.IGNORECASE,
)


def _split_lines_keepends(text: str) -> List[str]:
    """Split text into lines, each keeping its original terminator."""
    if not text:
        return []
    lines: List[str] = []
    i = 0
    n = len(text)
    start = 0
    while i < n:
        if text[i] == "\r" and i + 1 < n and text[i + 1] == "\n":
            lines.append(text[start : i + 2])
            i += 2
            start = i
        elif text[i] in ("\n", "\r"):
            lines.append(text[start : i + 1])
            i += 1
            start = i
        else:
            i += 1
    if start < n:
        lines.append(text[start:])
    return lines


def _line_content(line: str) -> str:
    """Line text without trailing newline characters."""
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1]
    return line


def _normalize_version(version: str) -> str:
    v = version.strip()
    if not v.lower().startswith("v"):
        v = "v" + v
    # Preserve original casing of the digits portion; force leading v lower.
    if v[0] in ("V", "v"):
        v = "v" + v[1:]
    return v


def _extract_status(title: str) -> tuple[str, Optional[str]]:
    """
    Pull a status fragment out of an iteration title when present.

    Examples:
      'Foo (COMPLETE)' -> ('Foo', 'COMPLETE')
      'Foo — COMPLETE 2026-07-12' -> ('Foo', 'COMPLETE 2026-07-12')
      'Foo (CLOSED 2026-07-11 — open items moved)' -> title, status
    """
    # Trailing parenthetical with a status keyword
    m = re.search(r"\s*\(([^)]*)\)\s*$", title)
    if m and _STATUS_HINT.search(m.group(1)):
        status = m.group(1).strip()
        clean = title[: m.start()].rstrip()
        return clean, status

    # Em-dash / hyphen COMPLETE tail: "title — COMPLETE ..."
    m2 = re.search(
        r"\s+([-—–])\s+((?:COMPLETE|CLOSED|DONE)\b.*)$",
        title,
        re.IGNORECASE,
    )
    if m2:
        status = m2.group(2).strip()
        clean = title[: m2.start()].rstrip()
        return clean, status

    return title.strip(), None


def parse_plan(text: str, path: Optional[Union[str, Path]] = None) -> Plan:
    """Parse PLAN.md text into a Plan model (tolerant, order-preserving)."""
    lines = _split_lines_keepends(text)
    plan = Plan(path=Path(path) if path else None)

    # Title from first H1 that is not a phase-like header
    for line in lines:
        content = _line_content(line)
        if content.startswith("# ") and not _RE_PHASE_LIKE.match(content):
            plan.title = content[2:].strip()
            break

    blocks: List = []
    current_major: Optional[MajorSection] = None
    current_backlog: Optional[BacklogSection] = None
    current_iteration: Optional[Iteration] = None
    prose_buf: List[str] = []

    def flush_prose() -> None:
        nonlocal prose_buf
        if not prose_buf:
            return
        raw = "".join(prose_buf)
        prose_buf = []
        node = ProseBlock(raw=raw)

        if current_iteration is not None:
            current_iteration.body.append(node)
            # Goal extraction from prose that starts with **Goal:**
            for chunk in raw.splitlines():
                gm = _RE_GOAL.match(chunk.strip()) if chunk.strip().startswith("**") else _RE_GOAL.match(chunk)
                if gm is None:
                    # try raw chunk without strip for mid-line? goals are full-line
                    gm = _RE_GOAL.match(chunk)
                if gm and current_iteration.goal is None:
                    goal_text = gm.group(1).strip()
                    # Multi-line goals: keep first line; rest stays in prose
                    current_iteration.goal = goal_text or None
            return

        if current_backlog is not None:
            current_backlog.items.append(node)
            return

        if current_major is not None:
            current_major.children.append(node)
            # Capture > description lines under major
            if current_major.description is None:
                desc_lines = []
                for chunk in raw.splitlines():
                    s = chunk.strip()
                    if s.startswith(">"):
                        desc_lines.append(s.lstrip(">").strip())
                if desc_lines:
                    current_major.description = " ".join(desc_lines)
            return

        blocks.append(node)

    def close_iteration() -> None:
        nonlocal current_iteration
        flush_prose()
        current_iteration = None

    def close_backlog() -> None:
        nonlocal current_backlog
        flush_prose()
        current_backlog = None

    def close_major() -> None:
        nonlocal current_major
        close_iteration()
        flush_prose()
        current_major = None

    def attach_iteration(it: Iteration) -> None:
        nonlocal current_iteration
        close_iteration()
        if current_major is not None:
            current_major.children.append(it)
        else:
            blocks.append(it)
        current_iteration = it

    def attach_top_level_prose_line(line: str) -> None:
        """Emit one opaque line at top level (closes open iteration/major)."""
        nonlocal current_major
        close_backlog()
        close_iteration()
        flush_prose()
        # Close major so phase-like section breaks leave subsequent
        # iterations at top level (managed format has no phase nesting).
        if current_major is not None:
            current_major = None
        blocks.append(ProseBlock(raw=line))

    for line in lines:
        content = _line_content(line)

        # --- phase-like headers: opaque prose, not structure ---
        if _RE_PHASE_LIKE.match(content):
            attach_top_level_prose_line(line)
            continue

        # Versioned headers first so titles that merely *mention* "backlog"
        # (e.g. "deferred — product Backlog") are not misclassified.
        m_major = _RE_MAJOR.match(content)
        if m_major:
            flush_prose()
            close_backlog()
            close_iteration()
            current_major = MajorSection(
                version=_normalize_version(m_major.group(1)),
                title=m_major.group(3).strip(),
                header_raw=line,
            )
            blocks.append(current_major)
            continue

        m_iter = _RE_ITERATION.match(content)
        if m_iter:
            flush_prose()
            close_backlog()  # iteration after backlog is rare; leave backlog closed
            title_raw = m_iter.group(4).strip()
            title, status = _extract_status(title_raw)
            it = Iteration(
                version=_normalize_version(m_iter.group(2)),
                title=title,
                status=status,
                header_raw=line,
            )
            attach_iteration(it)
            continue

        m_backlog = _RE_BACKLOG.match(content)
        if m_backlog:
            flush_prose()
            close_iteration()
            close_major()
            current_backlog = BacklogSection(
                title=m_backlog.group(2).strip(),
                header_raw=line,
            )
            blocks.append(current_backlog)
            continue

        # --- tasks (only inside an iteration; else prose for round-trip) ---
        m_task = _RE_TASK.match(content)
        if m_task and current_iteration is not None and current_backlog is None:
            flush_prose()
            done = m_task.group(2).lower() == "x"
            raw_text = m_task.group(3)
            task = Task(text=raw_text, done=done, raw=line)
            current_iteration.tasks.append(task)
            current_iteration.body.append(task)
            continue

        # --- backlog bullets ---
        if current_backlog is not None and current_iteration is None:
            m_bullet = _RE_BULLET.match(content)
            if m_bullet:
                flush_prose()
                item_text = m_bullet.group(2).strip()
                current_backlog.items.append(
                    BacklogItem(text=item_text, raw=line)
                )
                continue
            m_btask = _RE_TASK.match(content)
            if m_btask:
                flush_prose()
                # checkbox under backlog still a backlog item for tools
                item_text = m_btask.group(3).strip()
                current_backlog.items.append(
                    BacklogItem(text=item_text, raw=line)
                )
                continue

        # --- goal line inside iteration: keep as prose (raw) + set field ---
        if current_iteration is not None:
            gm = _RE_GOAL.match(content)
            if gm:
                flush_prose()
                # Store as prose for byte fidelity; also set goal field
                current_iteration.body.append(ProseBlock(raw=line))
                if current_iteration.goal is None:
                    current_iteration.goal = gm.group(1).strip() or None
                continue

        # Default: accumulate opaque prose
        prose_buf.append(line)

    flush_prose()
    plan.blocks = blocks
    return plan


def parse_plan_file(path: Union[str, Path]) -> Plan:
    """Read a PLAN.md file (utf-8) and parse it."""
    p = Path(path)
    # utf-8-sig strips BOM if present; source files are plain utf-8
    data = p.read_bytes()
    # Decode preserving exact content (no newline translation)
    text = data.decode("utf-8")
    if text.startswith("\ufeff"):
        # Keep BOM as part of first prose? Rare. Strip for parse, fail round-trip
        # if BOM present — our fixtures have no BOM.
        text = text.lstrip("\ufeff")
    return parse_plan(text, path=p)
