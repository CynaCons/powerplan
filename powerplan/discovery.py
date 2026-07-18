"""PLAN.md discovery: walk up from cwd (or start) to the nearest PLAN.md."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .plan_parser import parse_plan_file
from .plan_model import Plan


def find_plan_md(
    start: Optional[Union[str, Path]] = None,
    plan_path: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Resolve the PLAN.md to operate on.

    - If ``plan_path`` is given, use it (must exist).
    - Else walk from ``start`` (default: cwd) up to filesystem root and return
      the first directory that contains a file named ``PLAN.md``.
    """
    if plan_path is not None:
        p = Path(plan_path).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(f"plan_path does not exist: {p}")
        return p

    cur = Path(start).expanduser().resolve() if start is not None else Path.cwd().resolve()
    if cur.is_file():
        cur = cur.parent

    for directory in [cur, *cur.parents]:
        candidate = directory / "PLAN.md"
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        f"No PLAN.md found walking up from {cur}. "
        "Pass plan_path= to override."
    )


def load_plan(
    start: Optional[Union[str, Path]] = None,
    plan_path: Optional[Union[str, Path]] = None,
) -> Plan:
    """Discover PLAN.md and parse it into a Plan model."""
    path = find_plan_md(start=start, plan_path=plan_path)
    return parse_plan_file(path)
