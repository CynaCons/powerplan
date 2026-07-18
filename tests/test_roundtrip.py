"""Round-trip and model tests for powerplan parser/writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from powerplan.plan_parser import parse_plan, parse_plan_file
from powerplan.plan_writer import write_plan
from powerplan.views import show_plan, show_current_iteration
from powerplan.discovery import find_plan_md

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PP_PLAN = FIXTURES / "powerplanner_PLAN.md"
PN_PLAN = FIXTURES / "powernote_PLAN.md"


@pytest.fixture(scope="module")
def powerplanner_bytes() -> bytes:
    return PP_PLAN.read_bytes()


@pytest.fixture(scope="module")
def powernote_bytes() -> bytes:
    return PN_PLAN.read_bytes()


def test_fixtures_exist():
    assert PP_PLAN.is_file(), f"missing fixture {PP_PLAN}"
    assert PN_PLAN.is_file(), f"missing fixture {PN_PLAN}"


def test_powerplanner_roundtrip_byte_identical(powerplanner_bytes: bytes):
    text = powerplanner_bytes.decode("utf-8")
    plan = parse_plan(text, path=PP_PLAN)
    out = write_plan(plan)
    assert out.encode("utf-8") == powerplanner_bytes


def test_powernote_roundtrip_byte_identical(powernote_bytes: bytes):
    text = powernote_bytes.decode("utf-8")
    plan = parse_plan(text, path=PN_PLAN)
    out = write_plan(plan)
    assert out.encode("utf-8") == powernote_bytes


def test_powerplanner_model_basics():
    plan = parse_plan_file(PP_PLAN)
    iterations = plan.all_iterations()
    assert len(iterations) >= 30, f"expected many iterations, got {len(iterations)}"

    # Known early iteration
    it = plan.find_iteration("v2.3.2")
    assert it is not None
    assert "Native Core" in it.title
    assert it.goal is not None
    assert "Loadable add-in" in it.goal
    assert it.total_count >= 5
    assert it.done_count == it.total_count
    assert it.is_complete

    # Tasks exist overall
    total_tasks = sum(i.total_count for i in iterations)
    assert total_tasks >= 100

    # Phase is not a model type; phase-like headers preserved as opaque prose
    assert not any(b.__class__.__name__ == "Phase" for b in plan.blocks)
    phase_prose = [
        b
        for b in plan.blocks
        if b.__class__.__name__ == "ProseBlock" and "Phase" in getattr(b, "raw", "")
    ]
    assert len(phase_prose) >= 5

    # Backlog present
    backlog = plan.all_backlog_items()
    assert len(backlog) >= 3

    # show_plan produces non-empty ASCII (iterations only; phase prose omitted)
    ascii_view = show_plan(plan)
    assert "v2.3.2" in ascii_view
    assert "[" in ascii_view and "/" in ascii_view


def test_powernote_model_basics():
    plan = parse_plan_file(PN_PLAN)
    iterations = plan.all_iterations()
    assert len(iterations) >= 50, f"expected many iterations, got {len(iterations)}"

    it = plan.find_iteration("v0.1.0")
    assert it is not None
    assert "Scaffold" in it.title or "scaffold" in it.title.lower()
    assert it.total_count >= 5
    assert it.done_count == it.total_count

    # Majors present
    majors = [b for b in plan.blocks if b.__class__.__name__ == "MajorSection"]
    assert len(majors) >= 5
    assert majors[0].version.lower().startswith("v0.")

    # Future backlog
    backlog = plan.all_backlog_items()
    assert len(backlog) >= 3

    ascii_view = show_plan(plan)
    assert "v0.1" in ascii_view
    assert "v0.1.0" in ascii_view


def test_goal_extraction_powerplanner():
    plan = parse_plan_file(PP_PLAN)
    it = plan.find_iteration("v2.5.0")
    assert it is not None
    assert it.goal
    assert "PowerPlanner pixels" in it.goal or "pixels" in it.goal.lower()


def test_find_task_and_current():
    plan = parse_plan_file(PP_PLAN)
    hits = plan.find_tasks("overlay")
    assert len(hits) >= 1
    cur = plan.current_iteration()
    assert cur is not None
    detail = show_current_iteration(plan)
    assert cur.version in detail


def test_discovery_explicit_path(tmp_path: Path):
    target = tmp_path / "PLAN.md"
    target.write_text("# Demo\n\n### v0.0.1 - X\n- [ ] a\n", encoding="utf-8")
    found = find_plan_md(plan_path=target)
    assert found == target.resolve()

    # walk-up from nested cwd
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    found2 = find_plan_md(start=nested)
    assert found2 == target.resolve()


def test_parse_plan_file_matches_parse_plan(powerplanner_bytes: bytes):
    plan_a = parse_plan_file(PP_PLAN)
    plan_b = parse_plan(powerplanner_bytes.decode("utf-8"), path=PP_PLAN)
    assert write_plan(plan_a) == write_plan(plan_b)
    assert len(plan_a.all_iterations()) == len(plan_b.all_iterations())
