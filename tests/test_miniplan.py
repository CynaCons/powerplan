"""show_miniplan: the plan's own format as the agent view (v0.8.0)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from powerplan import mutations as m
from powerplan.plan_parser import parse_plan
from powerplan.server import call_tool, list_tools
from powerplan.views import show_miniplan

FIXTURES = Path(__file__).parent / "fixtures"


def _seed() -> m.Plan:
    """Two majors, four iterations; v0.2.0 is the first open one (current)."""
    plan = m.empty_plan("Demo")
    m.set_preamble(plan, "# Demo\n\n**Goal:** demo\n\n---\n\n")
    m.create_major(plan, "v0.1", "Foundation", description="first")
    m.create_iteration(plan, "v0.1.0", "Scaffold", major="v0.1", goal="stand up")
    m.add_tasks(plan, "v0.1.0", ["a", "b"], done=True)
    m.create_iteration(plan, "v0.1.1", "Views", major="v0.1")
    m.add_tasks(plan, "v0.1.1", ["c"], done=True)
    m.create_major(plan, "v0.2", "Second")
    m.create_iteration(plan, "v0.2.0", "Current work", major="v0.2", goal="do it")
    m.add_tasks(plan, "v0.2.0", ["d", "e"])
    m.create_iteration(plan, "v0.2.1", "Later", major="v0.2")
    m.add_tasks(plan, "v0.2.1", ["f"])
    return plan


def test_default_is_current_iteration_with_neighbour_headers():
    plan = _seed()
    out = show_miniplan(plan)
    assert out == (
        "## v0.1 — Foundation\n"
        "### v0.1.1 — Views\n"
        "## v0.2 — Second\n"
        "### v0.2.0 — Current work\n"
        "**Goal:** do it\n"
        "- [ ] d\n"
        "- [ ] e\n"
        "### v0.2.1 — Later\n"
    )


def test_explicit_version_and_zero_context():
    plan = _seed()
    out = show_miniplan(plan, "v0.1.0", before=0, after=0)
    assert out == (
        "## v0.1 — Foundation\n"
        "### v0.1.0 — Scaffold\n"
        "**Goal:** stand up\n"
        "- [x] a\n"
        "- [x] b\n"
    )


def test_wider_context_crosses_majors_and_clamps_at_ends():
    plan = _seed()
    out = show_miniplan(plan, "v0.2.1", before=2, after=5)
    assert out == (
        "## v0.1 — Foundation\n"
        "### v0.1.1 — Views\n"
        "## v0.2 — Second\n"
        "### v0.2.0 — Current work\n"
        "\n"  # the target keeps its own raw padding
        "### v0.2.1 — Later\n"
        "- [ ] f\n"
    )


def test_top_level_iterations_without_a_major():
    plan = m.empty_plan("Flat")
    m.set_preamble(plan, "# Flat\n\n")
    m.create_iteration(plan, "v0.1.0", "One")
    m.add_tasks(plan, "v0.1.0", ["x"], done=True)
    m.create_iteration(plan, "v0.1.1", "Two")
    m.add_tasks(plan, "v0.1.1", ["y"])
    out = show_miniplan(plan)
    assert out == (
        "### v0.1.0 — One\n"
        "\n"
        "### v0.1.1 — Two\n"
        "- [ ] y\n"
    )


def test_missing_version_raises_and_empty_plan_returns_blank():
    plan = _seed()
    with pytest.raises(ValueError, match="Iteration not found"):
        show_miniplan(plan, "v9.9.9")
    assert show_miniplan(m.empty_plan("Empty")) == ""


@pytest.mark.parametrize("fixture", ["powernote_PLAN.md", "powerplanner_PLAN.md"])
def test_snippet_is_a_verbatim_slice_of_the_source(fixture: str):
    text = (FIXTURES / fixture).read_text(encoding="utf-8")
    plan = parse_plan(text)
    it = plan.current_iteration()
    assert it is not None
    out = show_miniplan(plan, before=0, after=0)
    # The full iteration block appears in the source exactly once, unchanged
    # (CRLF and all) — the miniplan is a slice, not a rendering.
    block = out[out.index(it.header_raw):]
    assert text.count(block) == 1


def test_mcp_tool_listed_and_callable():
    tools = asyncio.run(list_tools())
    names = {t.name for t in tools}
    assert "show_miniplan" in names
    schema = next(t for t in tools if t.name == "show_miniplan").inputSchema
    assert {"version", "before", "after", "plan_path"} <= set(schema["properties"])


def test_mcp_call_tool_default_and_error(tmp_path: Path):
    plan_path = tmp_path / "PLAN.md"
    m.write_plan_file(_seed(), plan_path)

    res = asyncio.run(call_tool("show_miniplan", {"plan_path": str(plan_path)}))
    assert res[0].text.startswith("## v0.1 — Foundation\n### v0.1.1 — Views\n")
    assert "- [ ] d\n- [ ] e\n" in res[0].text

    res = asyncio.run(
        call_tool("show_miniplan", {"plan_path": str(plan_path), "version": "v7.0.0"})
    )
    assert '"success": false' in res[0].text
    assert "Iteration not found" in res[0].text
