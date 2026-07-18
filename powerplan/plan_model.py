"""
Structured model for PLAN.md documents.

Recognized nodes (MajorSection, Iteration, Task, Backlog*) carry parsed
fields for tools. Unrecognized content — including phase-like headers — is
stored as ProseBlock nodes with raw text preserved byte-for-byte so an
unmutated parse→write round-trip is identical to the source file.

Iterations are the only structural unit tools operate on under the plan
(majors group them when present). There is no Phase type.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Union


@dataclass
class ProseBlock:
    """Opaque unrecognized content preserved byte-for-byte."""

    raw: str


@dataclass
class Task:
    """A checkbox task line: ``- [ ]`` / ``- [x]``."""

    text: str
    done: bool
    raw: str = ""  # original line including terminator, for round-trip


@dataclass
class BacklogItem:
    """A non-checkbox backlog bullet (or structured backlog entry)."""

    text: str
    raw: str = ""


@dataclass
class Iteration:
    """A versioned iteration section (``### vX.Y.Z - Title``)."""

    version: str
    title: str
    goal: Optional[str] = None
    status: Optional[str] = None
    tasks: List[Task] = field(default_factory=list)
    # Ordered body for round-trip (tasks + interleaved prose, including Goal lines)
    body: List[Union[Task, ProseBlock]] = field(default_factory=list)
    header_raw: str = ""

    @property
    def done_count(self) -> int:
        return sum(1 for t in self.tasks if t.done)

    @property
    def total_count(self) -> int:
        return len(self.tasks)

    @property
    def is_complete(self) -> bool:
        """Heuristic completeness for filters / current-iteration selection."""
        status = (self.status or "").upper()
        if status:
            if any(k in status for k in ("FAILED", "REOPEN", "BLOCKED")):
                return False
            if any(k in status for k in ("COMPLETE", "CLOSED", "DONE")):
                if self.tasks and self.done_count < self.total_count:
                    return False
                return True
            if any(k in status for k in ("ACTIVE", "IN PROGRESS", "NEXT", "WIP")):
                return False
        if self.tasks:
            return self.done_count == self.total_count
        # No tasks and no complete-ish status → treat as open shell
        return False

    @property
    def is_open(self) -> bool:
        return not self.is_complete

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "title": self.title,
            "goal": self.goal,
            "status": self.status,
            "is_complete": self.is_complete,
            "progress": {
                "done": self.done_count,
                "total": self.total_count,
            },
            "tasks": [
                {
                    "text": t.text,
                    "done": t.done,
                }
                for t in self.tasks
            ],
        }


@dataclass
class MajorSection:
    """Powernote-style ``## vX.Y — Title`` major container (holds iterations)."""

    version: str
    title: str
    description: Optional[str] = None
    header_raw: str = ""
    children: List[Any] = field(default_factory=list)  # Iteration | ProseBlock


@dataclass
class BacklogSection:
    """Backlog / Future (Backlog) section with freeform items."""

    title: str
    header_raw: str = ""
    items: List[Union[BacklogItem, ProseBlock]] = field(default_factory=list)


PlanNode = Union[MajorSection, Iteration, BacklogSection, ProseBlock]


@dataclass
class Plan:
    """Full PLAN.md document as an ordered tree of nodes."""

    title: str = ""
    blocks: List[PlanNode] = field(default_factory=list)
    path: Optional[Path] = None

    def all_iterations(self) -> List[Iteration]:
        out: List[Iteration] = []
        for block in self.blocks:
            if isinstance(block, Iteration):
                out.append(block)
            elif isinstance(block, MajorSection):
                for child in block.children:
                    if isinstance(child, Iteration):
                        out.append(child)
        return out

    def find_iteration(self, version: str) -> Optional[Iteration]:
        key = _norm_version(version)
        for it in self.all_iterations():
            if _norm_version(it.version) == key:
                return it
        return None

    def current_iteration(self) -> Optional[Iteration]:
        """
        Resolve the *current* iteration agents should work on.

        Priority:
        1. Explicit markers: status/title contains "current" (e.g. ``(current)``).
        2. ``## Current Status`` table prose with a ``**current**`` row pointing
           at a version that still exists in the plan.
        3. First open iteration that still has incomplete checkbox tasks.
        4. First open iteration shell.
        5. Last iteration (plan fully complete / empty).
        """
        iterations = self.all_iterations()
        if not iterations:
            return None

        # 1) Explicit (current) on the iteration itself
        marked: List[Iteration] = []
        for it in iterations:
            blob = f"{it.status or ''} {it.title}".lower()
            if re.search(r"\bcurrent\b", blob):
                marked.append(it)
        if marked:
            # Prefer an open marked iter; else the last marked (most recent tag)
            for it in marked:
                if it.is_open:
                    return it
            return marked[-1]

        # 2) Current Status table in freeform prose
        from_table = self._current_from_status_table()
        if from_table is not None:
            return from_table

        # 3) First open with remaining tasks
        for it in iterations:
            if it.is_open and any(not t.done for t in it.tasks):
                return it
        # 4) First open shell
        for it in iterations:
            if it.is_open:
                return it
        # 5) Fallback
        return iterations[-1]

    def _current_from_status_table(self) -> Optional[Iteration]:
        """Parse ``| vX.Y.Z | **current** — … |`` rows from prose blocks."""
        # version cell then a cell containing **current** (markdown bold)
        row_re = re.compile(
            r"\|\s*(v?\d+\.\d+(?:\.\d+)?(?:[-–][^\s|]*)?)\s*\|[^|\n]*\*\*current\*\*",
            re.IGNORECASE,
        )
        for block in self.blocks:
            raw = getattr(block, "raw", None)
            if not raw or "current" not in raw.lower():
                continue
            # Prefer the last **current** row in the block (table grows downward)
            hits = row_re.findall(raw)
            if not hits:
                continue
            version = hits[-1].strip()
            it = self.find_iteration(version)
            if it is not None:
                return it
            # try stripping suffix after first three version parts already handled
        return None

    def all_backlog_items(self) -> List[BacklogItem]:
        items: List[BacklogItem] = []
        for block in self.blocks:
            if isinstance(block, BacklogSection):
                for entry in block.items:
                    if isinstance(entry, BacklogItem):
                        items.append(entry)
        return items

    def find_tasks(self, text: str) -> List[dict[str, Any]]:
        """Case-insensitive substring match over task text."""
        needle = text.lower().strip()
        hits: List[dict[str, Any]] = []
        for it in self.all_iterations():
            for t in it.tasks:
                if needle in t.text.lower():
                    hits.append(
                        {
                            "version": it.version,
                            "iteration_title": it.title,
                            "text": t.text,
                            "done": t.done,
                        }
                    )
        return hits


def _norm_version(version: str) -> str:
    v = version.strip().lower()
    if not v.startswith("v"):
        v = "v" + v
    return v


def iter_container_children(node: Any) -> Iterable[Any]:
    if isinstance(node, MajorSection):
        return node.children
    return ()
