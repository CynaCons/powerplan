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
        """Active / first-open iteration with remaining work (else last)."""
        iterations = self.all_iterations()
        if not iterations:
            return None
        # Prefer first open iteration that still has incomplete checkbox tasks
        for it in iterations:
            if it.is_open and any(not t.done for t in it.tasks):
                return it
        # Then first open shell (status/empty)
        for it in iterations:
            if it.is_open:
                return it
        return iterations[-1]

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
