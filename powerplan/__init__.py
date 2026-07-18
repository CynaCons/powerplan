"""
powerplan — PLAN.md as the operational backbone of agentic development.

This package provides a tolerant parser, byte-preserving writer, discovery,
and (via powerplan_server.py) an MCP server named ``powerplan``.
"""

from .plan_model import (
    BacklogItem,
    BacklogSection,
    Iteration,
    MajorSection,
    Plan,
    ProseBlock,
    Task,
)
from .plan_parser import parse_plan, parse_plan_file
from .plan_writer import write_plan, write_plan_file
from .discovery import find_plan_md, load_plan

__version__ = "0.2.2"
__all__ = [
    "BacklogItem",
    "BacklogSection",
    "Iteration",
    "MajorSection",
    "Plan",
    "ProseBlock",
    "Task",
    "parse_plan",
    "parse_plan_file",
    "write_plan",
    "write_plan_file",
    "find_plan_md",
    "load_plan",
    "__version__",
]
