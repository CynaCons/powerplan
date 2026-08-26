"""Arity-independent batch mutations (v0.7.1)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from powerplan import mutations as m
from powerplan.plan_parser import parse_plan
from powerplan.server import call_tool, list_tools


def _plan(*tasks: str, version: str = "v0.1.0"):
    plan = m.empty_plan("Demo")
    m.create_major(plan, "v0.1", "Foundation")
    m.create_iteration(plan, version, "Scaffold", major="v0.1")
    for t in tasks:
        m.add_task(plan, version, t)
    return plan


def _texts(plan, version="v0.1.0"):
    return [t.text for t in plan.find_iteration(version).tasks]


def _done(plan, version="v0.1.0"):
    return [t.done for t in plan.find_iteration(version).tasks]


def test_complete_indexes_ticks_those_rows():
    plan = _plan("a", "b", "c", "d")
    m.complete_task(plan, "v0.1.0", indexes=[1, 3])
    assert _done(plan) == [True, False, True, False]
    assert _texts(plan) == ["a", "b", "c", "d"]


def test_complete_tasks_by_text():
    plan = _plan("alpha", "beta", "gamma")
    m.complete_task(plan, "v0.1.0", tasks=["gamma", "alpha"])
    assert _done(plan) == [True, False, True]


def test_complete_already_done_is_idempotent():
    plan = _plan("a", "b")
    m.complete_task(plan, "v0.1.0", indexes=[1, 2])
    m.complete_task(plan, "v0.1.0", indexes=[1, 2])
    assert _done(plan) == [True, True]


def test_reopen_indexes():
    plan = _plan("a", "b", "c")
    m.complete_task(plan, "v0.1.0", indexes=[1, 2, 3])
    m.reopen_task(plan, "v0.1.0", indexes=[1, 3])
    assert _done(plan) == [False, True, False]


def test_remove_indexes_resolve_then_apply():
    plan = _plan("a", "b", "c", "d")
    m.remove_task(plan, "v0.1.0", indexes=[1, 3])
    assert _texts(plan) == ["b", "d"]


def test_defer_indexes_resolve_then_apply():
    plan = _plan("a", "b", "c", "d")
    m.defer_task(plan, "v0.1.0", indexes=[1, 3], reason="later")
    assert _texts(plan) == ["b", "d"]
    backlog = [i.text for i in plan.all_backlog_items()]
    assert any("a (" in x and "later" in x for x in backlog)
    assert any("c (" in x and "later" in x for x in backlog)


def test_duplicate_indexes_refused():
    plan = _plan("a", "b")
    with pytest.raises(ValueError, match="duplicate"):
        m.complete_task(plan, "v0.1.0", indexes=[1, 1])
    assert _done(plan) == [False, False]


def test_duplicate_text_targets_refused():
    plan = _plan("alpha", "beta")
    with pytest.raises(ValueError, match="duplicate"):
        m.complete_task(plan, "v0.1.0", tasks=["alpha", "alp"])
    assert _done(plan) == [False, False]


def test_mix_index_and_indexes_refused():
    plan = _plan("a", "b")
    with pytest.raises(ValueError, match="not both"):
        m.complete_task(plan, "v0.1.0", index=1, indexes=[2])
    assert _done(plan) == [False, False]


def test_mix_index_and_task_refused():
    plan = _plan("a", "b")
    with pytest.raises(ValueError, match="not both"):
        m.complete_task(plan, "v0.1.0", index=1, tasks=["b"])
    assert _done(plan) == [False, False]


def test_expect_rejected_on_array():
    plan = _plan("a", "b")
    with pytest.raises(ValueError, match="expect is only valid"):
        m.complete_task(plan, "v0.1.0", indexes=[1], expect="a")


def test_update_changes_atomic_expect():
    plan = _plan("alpha", "beta", "gamma")
    with pytest.raises(ValueError, match="expect mismatch"):
        m.update_task(
            plan,
            "v0.1.0",
            changes=[
                {"index": 1, "text": "A"},
                {"index": 2, "text": "B", "expect": "nope"},
            ],
        )
    assert _texts(plan) == ["alpha", "beta", "gamma"]


def test_update_changes_rewrites_in_order():
    plan = _plan("alpha", "beta", "gamma")
    m.update_task(
        plan,
        "v0.1.0",
        changes=[
            {"index": 3, "text": "C"},
            {"task": "alpha", "text": "A"},
        ],
    )
    assert _texts(plan) == ["A", "beta", "C"]


def test_update_rejects_mixing_changes_and_singular():
    plan = _plan("alpha")
    with pytest.raises(ValueError, match="not both"):
        m.update_task(
            plan, "v0.1.0", text="A", index=1, changes=[{"index": 1, "text": "B"}]
        )


def test_add_to_backlog_texts_order():
    plan = _plan("keep")
    items = m.add_to_backlog(plan, texts=["one", "two", "three"])
    assert [i.text for i in items] == ["one", "two", "three"]
    assert [i.text for i in plan.all_backlog_items()] == ["one", "two", "three"]


def test_add_to_backlog_blank_item_refuses():
    plan = _plan("keep")
    m.add_to_backlog(plan, "keep me")
    with pytest.raises(ValueError, match=r"texts\[2\]"):
        m.add_to_backlog(plan, texts=["ok", "  ", "also"])
    assert [i.text for i in plan.all_backlog_items()] == ["keep me"]


def test_batch_cap():
    plan = _plan(*[f"t{i}" for i in range(5)])
    with pytest.raises(ValueError, match="cap of 100"):
        m.complete_task(plan, "v0.1.0", indexes=list(range(1, 102)))


def test_batch_does_not_write_on_error(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="duplicate"):
        m.mutate_and_save(
            path, lambda p: m.complete_task(p, "v0.1.0", indexes=[1, 1])
        )
    assert path.read_bytes() == before


def test_scalar_complete_still_works():
    plan = _plan("alpha", "beta")
    m.complete_task(plan, "v0.1.0", "beta")
    assert _done(plan) == [False, True]


def test_list_tools_exposes_indexes_and_changes():
    tools = {t.name: t for t in asyncio.run(list_tools())}
    complete = tools["complete_task"].inputSchema["properties"]
    assert "indexes" in complete
    assert "tasks" in complete
    update = tools["update_task"].inputSchema["properties"]
    assert "changes" in update
    backlog = tools["add_to_backlog"].inputSchema["properties"]
    assert "texts" in backlog


def test_mcp_complete_indexes_returns_updated(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    m.mutate_and_save(
        path, lambda p: m.add_tasks(p, "v0.1.0", ["one", "two", "three"])
    )
    payload = asyncio.run(
        call_tool(
            "complete_task",
            {"version": "v0.1.0", "indexes": [2, 4], "plan_path": str(path)},
        )
    )
    data = json.loads(payload[0].text)
    assert data["success"] is True
    assert data["updated"] == 2
    assert [t["index"] for t in data["tasks"]] == [2, 4]
    it = parse_plan(path.read_text(encoding="utf-8")).find_iteration("v0.1.0")
    assert [t.done for t in it.tasks] == [False, True, False, True]


def test_mcp_remove_indexes_keeps_unselected(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    m.mutate_and_save(path, lambda p: m.add_tasks(p, "v0.1.0", ["a", "b", "c"]))
    payload = asyncio.run(
        call_tool(
            "remove_task",
            {"version": "v0.1.0", "indexes": [1, 3], "plan_path": str(path)},
        )
    )
    data = json.loads(payload[0].text)
    assert data["success"] is True
    assert data["updated"] == 2
    it = parse_plan(path.read_text(encoding="utf-8")).find_iteration("v0.1.0")
    # create_plan seeds "Define first tasks" as index 1; add_tasks appends a,b,c
    assert [t.text for t in it.tasks] == ["a", "c"]
