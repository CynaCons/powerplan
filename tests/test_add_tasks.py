"""Batch add_tasks: one mutation, many checkbox lines."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from powerplan import mutations as m
from powerplan.plan_parser import parse_plan
from powerplan.server import call_tool, list_tools


def _seed(plan: m.Plan | None = None) -> m.Plan:
    plan = plan or m.empty_plan("Demo")
    m.set_preamble(plan, "# Demo\n\n---\n\n")
    m.create_major(plan, "v0.1", "A")
    m.create_iteration(plan, "v0.1.0", "Work", major="v0.1")
    return plan


def test_add_tasks_appends_in_order():
    plan = _seed()
    added = m.add_tasks(plan, "v0.1.0", ["alpha", "beta", "gamma"])
    assert [t.text for t in added] == ["alpha", "beta", "gamma"]
    it = plan.find_iteration("v0.1.0")
    assert [t.text for t in it.tasks] == ["alpha", "beta", "gamma"]
    assert all(not t.done for t in it.tasks)
    text = m.write_plan(plan)
    assert "- [ ] alpha\n- [ ] beta\n- [ ] gamma\n" in text


def test_add_tasks_shared_done_and_agent():
    plan = _seed()
    m.add_tasks(plan, "v0.1.0", ["one", "two"], done=True, agent="grok-4.6")
    it = plan.find_iteration("v0.1.0")
    assert all(t.done for t in it.tasks)
    assert all("[agent: grok-4.6]" in t.text for t in it.tasks)
    raw = m.write_plan(plan)
    assert "- [x] one [agent: grok-4.6]\n" in raw
    assert "- [x] two [agent: grok-4.6]\n" in raw


def test_add_tasks_empty_list_refuses():
    plan = _seed()
    with pytest.raises(ValueError, match="non-empty"):
        m.add_tasks(plan, "v0.1.0", [])
    assert plan.find_iteration("v0.1.0").tasks == []


def test_add_tasks_blank_item_refuses_whole_batch():
    plan = _seed()
    m.add_task(plan, "v0.1.0", "keep me")
    with pytest.raises(ValueError, match=r"tasks\[2\]"):
        m.add_tasks(plan, "v0.1.0", ["ok", "  ", "also"])
    assert [t.text for t in plan.find_iteration("v0.1.0").tasks] == ["keep me"]


def test_add_tasks_missing_iteration():
    plan = _seed()
    with pytest.raises(ValueError, match="not found"):
        m.add_tasks(plan, "v9.9.9", ["x"])


def test_add_tasks_does_not_bury_separator_blank_lines(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    m.mutate_and_save(path, lambda p: m.add_to_backlog(p, "Idea A"))
    m.mutate_and_save(path, lambda p: m.create_major(p, "v0.2", "M"))
    m.mutate_and_save(path, lambda p: m.create_iteration(p, "v0.2.1", "I", major="v0.2"))
    m.mutate_and_save(
        path, lambda p: m.add_tasks(p, "v0.2.1", [f"task {n}" for n in range(4)])
    )

    text = path.read_text(encoding="utf-8")
    block = text[text.index("### v0.2.1") :]
    assert "\n\n- [ ]" not in block, f"blank line between tasks:\n{block!r}"
    it = parse_plan(text).find_iteration("v0.2.1")
    assert [t.text for t in it.tasks] == [f"task {n}" for n in range(4)]


def test_add_tasks_one_write(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path, seed_major=True)
    m.mutate_and_save(
        path, lambda p: m.add_tasks(p, "v0.1.0", ["a", "b", "c"], agent="bot")
    )
    it = parse_plan(path.read_text(encoding="utf-8")).find_iteration("v0.1.0")
    # create_plan seeds "Define first tasks"
    assert [t.text for t in it.tasks][-3:] == [
        "a [agent: bot]",
        "b [agent: bot]",
        "c [agent: bot]",
    ]


def test_list_tools_exposes_add_tasks():
    names = {t.name for t in asyncio.run(list_tools())}
    assert "add_task" in names
    assert "add_tasks" in names


def test_mcp_add_tasks_returns_indexes(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    payload = asyncio.run(
        call_tool(
            "add_tasks",
            {
                "version": "v0.1.0",
                "tasks": ["first extra", "second extra"],
                "plan_path": str(path),
            },
        )
    )
    body = payload[0].text
    import json

    data = json.loads(body)
    assert data["success"] is True
    assert data["added"] == 2
    assert [t["index"] for t in data["tasks"]] == [2, 3]
    assert data["tasks"][0]["text"] == "first extra"
