"""Task editing CRUD: update / remove / defer, addressing and guards (v0.5.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from powerplan import mutations as m
from powerplan.plan_parser import parse_plan, parse_plan_file
from powerplan.plan_writer import write_plan
from powerplan.views import get_iteration_view


def _plan(*tasks: str, version: str = "v0.1.0"):
    plan = m.empty_plan("Demo")
    m.create_major(plan, "v0.1", "Foundation")
    m.create_iteration(plan, version, "Scaffold", major="v0.1")
    for t in tasks:
        m.add_task(plan, version, t)
    return plan


def _texts(plan, version="v0.1.0"):
    return [t.text for t in plan.find_iteration(version).tasks]


# --------------------------------------------------------------- addressing --


def test_update_by_text_and_by_index_are_equivalent():
    by_text = _plan("alpha", "beta", "gamma")
    m.update_task(by_text, "v0.1.0", task="beta", text="BETA")

    by_index = _plan("alpha", "beta", "gamma")
    m.update_task(by_index, "v0.1.0", index=2, text="BETA")

    assert _texts(by_text) == _texts(by_index) == ["alpha", "BETA", "gamma"]
    assert write_plan(by_text) == write_plan(by_index)


def test_index_is_one_based():
    plan = _plan("alpha", "beta")
    m.update_task(plan, "v0.1.0", index=1, text="first")
    assert _texts(plan) == ["first", "beta"]


@pytest.mark.parametrize("bad", [0, -1, 3, 99])
def test_index_out_of_range_is_rejected(bad):
    plan = _plan("alpha", "beta")
    with pytest.raises(ValueError, match="out of range"):
        m.update_task(plan, "v0.1.0", index=bad, text="x")
    assert _texts(plan) == ["alpha", "beta"]


def test_index_on_empty_iteration():
    plan = _plan()
    with pytest.raises(ValueError, match="no tasks"):
        m.update_task(plan, "v0.1.0", index=1, text="x")


def test_non_integer_index_is_rejected():
    plan = _plan("alpha")
    with pytest.raises(ValueError, match="must be an integer"):
        m.update_task(plan, "v0.1.0", index="two", text="x")


def test_both_task_and_index_rejected():
    plan = _plan("alpha", "beta")
    with pytest.raises(ValueError, match="not both"):
        m.update_task(plan, "v0.1.0", task="alpha", index=1, text="x")


def test_neither_task_nor_index_rejected():
    plan = _plan("alpha")
    with pytest.raises(ValueError, match="One of task or index"):
        m.update_task(plan, "v0.1.0", text="x")


def test_blank_task_string_counts_as_absent():
    plan = _plan("alpha")
    with pytest.raises(ValueError, match="One of task or index"):
        m.update_task(plan, "v0.1.0", task="   ", text="x")


def test_ambiguous_text_still_errors_and_index_disambiguates():
    plan = _plan("wire the parser", "wire the writer")
    with pytest.raises(ValueError, match="Ambiguous"):
        m.update_task(plan, "v0.1.0", task="wire the", text="x")
    # index resolves what text cannot
    m.update_task(plan, "v0.1.0", index=2, text="wire the writer v2")
    assert _texts(plan) == ["wire the parser", "wire the writer v2"]


def test_unknown_text_errors():
    plan = _plan("alpha")
    with pytest.raises(ValueError, match="No task matching"):
        m.update_task(plan, "v0.1.0", task="nope", text="x")


def test_unknown_iteration_errors():
    plan = _plan("alpha")
    with pytest.raises(ValueError, match="Iteration not found"):
        m.update_task(plan, "v9.9.9", index=1, text="x")


# -------------------------------------------------------------- expect guard --


def test_expect_match_allows_edit():
    plan = _plan("alpha", "beta")
    m.update_task(plan, "v0.1.0", index=2, text="BETA", expect="beta")
    assert _texts(plan) == ["alpha", "BETA"]


def test_expect_mismatch_refuses_edit():
    plan = _plan("alpha", "beta")
    with pytest.raises(ValueError, match="expect mismatch"):
        m.update_task(plan, "v0.1.0", index=2, text="BETA", expect="gamma")
    assert _texts(plan) == ["alpha", "beta"]


def test_expect_ignores_agent_tags():
    plan = _plan()
    m.add_task(plan, "v0.1.0", "alpha", agent="opus-5")
    assert "[agent: opus-5]" in _texts(plan)[0]
    # caller need not know about the tag
    m.update_task(plan, "v0.1.0", index=1, text="ALPHA", expect="alpha")
    assert _texts(plan)[0].startswith("ALPHA")


def test_expect_guards_remove_and_defer():
    plan = _plan("alpha", "beta")
    with pytest.raises(ValueError, match="expect mismatch"):
        m.remove_task(plan, "v0.1.0", index=1, expect="beta")
    with pytest.raises(ValueError, match="expect mismatch"):
        m.defer_task(plan, "v0.1.0", index=1, expect="beta")
    assert _texts(plan) == ["alpha", "beta"]


# ------------------------------------------------------------- update_task --


def test_update_preserves_done_state():
    plan = _plan("alpha", "beta")
    m.complete_task(plan, "v0.1.0", "beta")
    m.update_task(plan, "v0.1.0", index=2, text="BETA")
    it = plan.find_iteration("v0.1.0")
    assert it.tasks[1].done is True
    assert "- [x] BETA" in write_plan(plan)


def test_update_keeps_existing_agent_tag():
    plan = _plan()
    m.add_task(plan, "v0.1.0", "alpha", agent="opus-5")
    m.update_task(plan, "v0.1.0", index=1, text="ALPHA")
    assert _texts(plan) == ["ALPHA [agent: opus-5]"]


def test_update_can_override_agent_tag():
    plan = _plan()
    m.add_task(plan, "v0.1.0", "alpha", agent="opus-5")
    m.update_task(plan, "v0.1.0", index=1, text="ALPHA", agent="haiku-4.5")
    assert _texts(plan) == ["ALPHA [agent: haiku-4.5]"]
    assert write_plan(plan).count("[agent:") == 1


def test_update_rejects_empty_text():
    plan = _plan("alpha")
    for bad in ("", "   ", None):
        with pytest.raises(ValueError, match="non-empty"):
            m.update_task(plan, "v0.1.0", index=1, text=bad)
    assert _texts(plan) == ["alpha"]


def test_update_survives_round_trip():
    plan = _plan("alpha", "beta")
    m.update_task(plan, "v0.1.0", index=1, text="alpha rewritten")
    reparsed = parse_plan(write_plan(plan))
    assert _texts(reparsed) == ["alpha rewritten", "beta"]


# ------------------------------------------------------------- remove_task --


def test_remove_drops_from_tasks_and_body():
    plan = _plan("alpha", "beta", "gamma")
    m.remove_task(plan, "v0.1.0", index=2)
    it = plan.find_iteration("v0.1.0")
    assert _texts(plan) == ["alpha", "gamma"]
    body_tasks = [n.text for n in it.body if hasattr(n, "done")]
    assert body_tasks == ["alpha", "gamma"], "body and tasks must stay in sync"
    assert "beta" not in write_plan(plan)


def test_remove_reindexes_remaining_tasks():
    plan = _plan("alpha", "beta", "gamma")
    m.remove_task(plan, "v0.1.0", index=1)
    # what was #2 is now #1
    m.update_task(plan, "v0.1.0", index=1, text="BETA")
    assert _texts(plan) == ["BETA", "gamma"]


def test_remove_identical_text_removes_only_one():
    """Equal-valued tasks must be distinguished by identity, not by value."""
    plan = _plan()
    m.add_task(plan, "v0.1.0", "dup")
    m.add_task(plan, "v0.1.0", "dup")
    assert len(_texts(plan)) == 2
    m.remove_task(plan, "v0.1.0", index=1)
    assert _texts(plan) == ["dup"]
    it = plan.find_iteration("v0.1.0")
    assert len([n for n in it.body if hasattr(n, "done")]) == 1


def test_remove_last_task_leaves_valid_plan():
    plan = _plan("only")
    m.remove_task(plan, "v0.1.0", index=1)
    assert _texts(plan) == []
    reparsed = parse_plan(write_plan(plan))
    assert reparsed.find_iteration("v0.1.0") is not None
    assert m.check_plan(reparsed)["ok"] is True


# -------------------------------------------------------------- defer_task --


def test_defer_moves_task_to_backlog():
    plan = _plan("alpha", "beta")
    m.defer_task(plan, "v0.1.0", index=2)
    assert _texts(plan) == ["alpha"]
    items = [i.text for i in plan.all_backlog_items()]
    assert items == ["beta (deferred from v0.1.0)"]


def test_defer_with_reason():
    plan = _plan("alpha")
    m.defer_task(plan, "v0.1.0", task="alpha", reason="blocked on upstream API")
    items = [i.text for i in plan.all_backlog_items()]
    assert items == ["alpha (deferred from v0.1.0: blocked on upstream API)"]


def test_defer_keeps_backlog_last():
    plan = _plan("alpha")
    m.defer_task(plan, "v0.1.0", index=1)
    assert type(plan.blocks[-1]).__name__ == "BacklogSection"


def test_defer_round_trips():
    plan = _plan("alpha", "beta")
    m.defer_task(plan, "v0.1.0", index=1, reason="later")
    text = write_plan(plan)
    reparsed = parse_plan(text)
    assert _texts(reparsed) == ["beta"]
    assert len(reparsed.all_backlog_items()) == 1


def test_defer_preserves_agent_tag():
    plan = _plan()
    m.add_task(plan, "v0.1.0", "alpha", agent="opus-5")
    m.defer_task(plan, "v0.1.0", index=1)
    items = [i.text for i in plan.all_backlog_items()]
    assert items == ["alpha (deferred from v0.1.0) [agent: opus-5]"]


# ------------------------------------------- retrofit onto lifecycle tools --


def test_complete_and_reopen_accept_index():
    plan = _plan("alpha", "beta")
    m.complete_task(plan, "v0.1.0", index=2)
    assert plan.find_iteration("v0.1.0").tasks[1].done is True
    m.reopen_task(plan, "v0.1.0", index=2)
    assert plan.find_iteration("v0.1.0").tasks[1].done is False


def test_complete_task_positional_text_still_works():
    """Back-compat: existing callers pass task positionally."""
    plan = _plan("alpha", "beta")
    m.complete_task(plan, "v0.1.0", "alpha")
    assert plan.find_iteration("v0.1.0").tasks[0].done is True


def test_complete_task_honours_expect():
    plan = _plan("alpha", "beta")
    with pytest.raises(ValueError, match="expect mismatch"):
        m.complete_task(plan, "v0.1.0", index=1, expect="beta")
    assert plan.find_iteration("v0.1.0").tasks[0].done is False


def test_get_iteration_exposes_one_based_index():
    plan = _plan("alpha", "beta", "gamma")
    payload = json.loads(get_iteration_view(plan, "v0.1.0"))
    assert [t["index"] for t in payload["tasks"]] == [1, 2, 3]
    assert [t["text"] for t in payload["tasks"]] == ["alpha", "beta", "gamma"]
    # the index in the payload is the one the edit tools accept
    m.update_task(plan, "v0.1.0", index=payload["tasks"][1]["index"], text="BETA")
    assert _texts(plan) == ["alpha", "BETA", "gamma"]


# ------------------------------------------------------ end-to-end on disk --


def test_full_cycle_through_mutate_and_save(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    m.mutate_and_save(path, lambda p: m.create_major(p, "v0.2", "M"))
    m.mutate_and_save(path, lambda p: m.create_iteration(p, "v0.2.1", "I", major="v0.2"))
    for t in ("alpha", "beta", "gamma"):
        m.mutate_and_save(path, lambda p, t=t: m.add_task(p, "v0.2.1", t))

    m.mutate_and_save(path, lambda p: m.update_task(p, "v0.2.1", index=1, text="ALPHA"))
    m.mutate_and_save(path, lambda p: m.remove_task(p, "v0.2.1", task="beta"))
    m.mutate_and_save(path, lambda p: m.defer_task(p, "v0.2.1", index=1, reason="later"))

    text = path.read_text(encoding="utf-8")
    plan = parse_plan_file(path)
    assert _texts(plan, "v0.2.1") == ["gamma"]
    assert [i.text for i in plan.all_backlog_items()] == [
        "ALPHA (deferred from v0.2.1: later)"
    ]
    assert type(plan.blocks[-1]).__name__ == "BacklogSection"
    assert "\n\n- [ ]" not in text[text.index("### v0.2.1") :]
    assert m.check_plan(plan)["ok"] is True

    # repeated saves are a fixed point
    before = path.read_bytes()
    for _ in range(3):
        m.mutate_and_save(path, lambda p: None)
    assert path.read_bytes() == before


def test_failed_edit_leaves_file_untouched(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    m.mutate_and_save(path, lambda p: m.create_iteration(p, "v0.1.1", "I"))
    m.mutate_and_save(path, lambda p: m.add_task(p, "v0.1.1", "alpha"))
    before = path.read_bytes()

    for bad in (
        lambda p: m.update_task(p, "v0.1.1", index=99, text="x"),
        lambda p: m.update_task(p, "v0.1.1", index=1, text="x", expect="wrong"),
        lambda p: m.remove_task(p, "v0.1.1", task="nope"),
        lambda p: m.defer_task(p, "v0.1.1", index=42),
    ):
        with pytest.raises(ValueError):
            m.mutate_and_save(path, bad)

    assert path.read_bytes() == before, "a rejected edit must not touch the file"
