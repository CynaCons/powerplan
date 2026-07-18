"""PLAN.md discovery: walk up from cwd (or start) to the nearest PLAN.md."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .plan_parser import parse_plan_file
from .plan_model import Plan


def resolve_plan_path(
    plan_path: Optional[Union[str, Path]] = None,
    *,
    start: Optional[Union[str, Path]] = None,
    must_exist: bool = True,
    default_name: str = "PLAN.md",
) -> Path:
    """
    Resolve which PLAN.md path a tool should use.

    - If ``plan_path`` is set: expand/resolve relative to cwd (or absolute).
      When ``must_exist`` is True, the file must already exist.
      When False, parent directory must exist (file may be created).
    - If omitted: walk up from ``start`` (default cwd) for nearest ``PLAN.md``.
      If none found and ``must_exist`` is False, return ``cwd / default_name``.
    """
    if plan_path is not None and str(plan_path).strip() != "":
        p = Path(plan_path).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
        if must_exist:
            if not p.is_file():
                raise FileNotFoundError(
                    f"plan_path does not exist: {p}. "
                    "Use create_plan(plan_path=...) to bootstrap a new plan."
                )
            return p
        # Creating: parent must exist
        if not p.parent.is_dir():
            raise FileNotFoundError(f"Parent directory does not exist: {p.parent}")
        return p

    cur = Path(start).expanduser().resolve() if start is not None else Path.cwd().resolve()
    if cur.is_file():
        cur = cur.parent

    for directory in [cur, *cur.parents]:
        candidate = directory / default_name
        if candidate.is_file():
            return candidate

    if must_exist:
        raise FileNotFoundError(
            f"No PLAN.md found walking up from {cur}. "
            "Pass plan_path= to override, or call create_plan first."
        )
    return cur / default_name


def find_plan_md(
    start: Optional[Union[str, Path]] = None,
    plan_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Resolve an existing PLAN.md (must exist)."""
    return resolve_plan_path(plan_path, start=start, must_exist=True)


def load_plan(
    start: Optional[Union[str, Path]] = None,
    plan_path: Optional[Union[str, Path]] = None,
) -> Plan:
    """Discover PLAN.md and parse it into a Plan model."""
    path = find_plan_md(start=start, plan_path=plan_path)
    return parse_plan_file(path)
