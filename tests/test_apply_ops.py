"""Heterogeneous atomic batches — apply_ops (v0.11.0)."""

from __future__ import annotations

import asyncio
import json

import pytest

from powerplan import mutations as m
from powerplan.plan_parser import parse_plan_file
from powerplan.server import call_tool, list_tools


def _plan(*tasks: str, version: str = "v0.1.0"):
    plan = m.empty_plan("Demo")
    m.create_major(plan, "v0.1", "Foundation")
    m.create_iteration(plan, version, "Scaffold", major="v0.1")
    for t in tasks:
        m.add_task(plan, version, t)
    return plan


def _saved(tmp_path, *tasks: str):
    plan = _plan(*tasks)
    path = tmp_path / "PLAN.md"
    m.save_plan(plan, path)
    return path


def _texts(plan, version="v0.1.0"):
    return [t.text for t in plan.find_iteration(version).tasks]


def _done(plan, version="v0.1.0"):
    return [t.done for t in plan.find_iteration(version).tasks]


def _call(path, **kw):
    out = asyncio.run(call_tool("apply_ops", {"plan_path": str(path), **kw}))
    return json.loads(out[0].text)


# --------------------------------------------------------------------------
# applying
# --------------------------------------------------------------------------

def test_a_whole_turn_end_in_one_batch():
    plan = _plan("alpha", "beta", "gamma")
    result = m.apply_ops(
        plan,
        [
            {"op": "complete_task", "version": "v0.1.0", "indexes": [1, 2]},
            {"op": "add_tasks", "version": "v0.1.0", "tasks": ["delta", "epsilon"]},
            {"op": "add_to_backlog", "texts": ["later one", "later two"]},
            {"op": "create_iteration", "version": "v0.1.1", "title": "Next", "major": "v0.1"},
            {"op": "complete_task", "version": "v0.1.0", "indexes": [3, 4, 5]},
            {"op": "close_iteration", "version": "v0.1.0", "stamp": "2026-11-23"},
        ],
    )
    assert result["applied"] == 6
    assert _done(plan) == [True] * 5
    it = plan.find_iteration("v0.1.0")
    assert it.status == "COMPLETE"
    assert "2026-11-23" in it.title
    assert plan.find_iteration("v0.1.1") is not None
    assert result["check"] == {"ok": True, "issue_count": 0}


def test_ops_apply_in_order_and_see_earlier_changes():
    """create → populate → close, which only works if ops are sequential."""
    plan = _plan()
    m.apply_ops(
        plan,
        [
            {"op": "create_iteration", "version": "v0.1.1", "title": "Next", "major": "v0.1"},
            {"op": "add_tasks", "version": "v0.1.1", "tasks": ["one", "two"]},
            {"op": "complete_task", "version": "v0.1.1", "indexes": [1, 2]},
            {"op": "close_iteration", "version": "v0.1.1"},
        ],
    )
    it = plan.find_iteration("v0.1.1")
    assert [t.text for t in it.tasks] == ["one", "two"]
    assert it.status == "COMPLETE"


def test_ops_span_several_iterations_in_one_write():
    plan = _plan("a")
    m.create_iteration(plan, "v0.1.1", "Next", major="v0.1")
    m.add_task(plan, "v0.1.1", "b")
    m.apply_ops(
        plan,
        [
            {"op": "complete_task", "version": "v0.1.0", "index": 1},
            {"op": "complete_task", "version": "v0.1.1", "index": 1},
        ],
    )
    assert _done(plan, "v0.1.0") == [True]
    assert _done(plan, "v0.1.1") == [True]


def test_per_op_summary_reports_counts_and_positions():
    plan = _plan("a", "b")
    result = m.apply_ops(
        plan,
        [
            {"op": "complete_task", "version": "v0.1.0", "indexes": [1, 2]},
            {"op": "append_prose", "text": "## Notes\n"},
        ],
    )
    assert result["ops"][0] == {
        "i": 0, "op": "complete_task", "version": "v0.1.0", "count": 2,
    }
    assert result["ops"][1] == {"i": 1, "op": "append_prose"}


def test_result_carries_the_lint_report():
    """A force-close leaving open tasks is reported without a second call."""
    plan = _plan("a", "b")
    result = m.apply_ops(
        plan, [{"op": "close_iteration", "version": "v0.1.0", "force": True}]
    )
    assert result["check"]["ok"] is False
    assert result["check"]["issue_count"] >= 1


# --------------------------------------------------------------------------
# atomicity
# --------------------------------------------------------------------------

def test_a_failing_op_writes_nothing(tmp_path):
    """The headline guarantee: no half-updated PLAN.md."""
    path = _saved(tmp_path, "a", "b")
    before = path.read_bytes()

    result = _call(
        path,
        ops=[
            {"op": "complete_task", "version": "v0.1.0", "index": 1},
            {"op": "add_tasks", "version": "v0.1.0", "tasks": ["c"]},
            {"op": "close_iteration", "version": "v0.1.0"},  # open tasks remain
        ],
    )
    assert result["success"] is False
    assert result["written"] is False
    assert result["applied"] == 0
    assert result["failed_op"] == {"i": 2, "op": "close_iteration"}
    assert path.read_bytes() == before


def test_a_malformed_op_writes_nothing(tmp_path):
    path = _saved(tmp_path, "a")
    before = path.read_bytes()
    result = _call(
        path,
        ops=[
            {"op": "complete_task", "version": "v0.1.0", "index": 1},
            {"op": "not_a_tool"},
        ],
    )
    assert result["success"] is False
    assert result["written"] is False
    assert path.read_bytes() == before


def test_one_write_lands_the_whole_batch(tmp_path):
    path = _saved(tmp_path, "a", "b")
    result = _call(
        path,
        agent="claude-opus-5",
        ops=[
            {"op": "complete_task", "version": "v0.1.0", "indexes": [1, 2]},
            {"op": "add_to_backlog", "text": "later"},
            {"op": "close_iteration", "version": "v0.1.0", "stamp": "2026-11-23"},
        ],
    )
    assert result["success"] is True and result["written"] is True
    reparsed = parse_plan_file(path)
    assert _done(reparsed) == [True, True]
    assert reparsed.find_iteration("v0.1.0").status == "COMPLETE"
    assert any("later" in i.text for i in reparsed.all_backlog_items())


def test_the_write_leaves_no_temp_file_behind(tmp_path):
    path = _saved(tmp_path, "a")
    _call(path, ops=[{"op": "complete_task", "version": "v0.1.0", "index": 1}])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["PLAN.md"]


# --------------------------------------------------------------------------
# dry_run
# --------------------------------------------------------------------------

def test_dry_run_reports_but_does_not_write(tmp_path):
    path = _saved(tmp_path, "a", "b")
    before = path.read_bytes()
    result = _call(
        path,
        dry_run=True,
        ops=[
            {"op": "complete_task", "version": "v0.1.0", "indexes": [1, 2]},
            {"op": "close_iteration", "version": "v0.1.0"},
        ],
    )
    assert result["success"] is True
    assert result["dry_run"] is True and result["written"] is False
    assert result["applied"] == 2
    assert path.read_bytes() == before


def test_dry_run_still_raises_what_a_real_call_would(tmp_path):
    path = _saved(tmp_path, "a", "b")
    result = _call(
        path, dry_run=True, ops=[{"op": "close_iteration", "version": "v0.1.0"}]
    )
    assert result["success"] is False
    assert result["failed_op"] == {"i": 0, "op": "close_iteration"}


def test_dry_run_fails_the_same_way_on_a_missing_plan(tmp_path):
    result = _call(
        tmp_path / "PLAN.md",
        dry_run=True,
        ops=[{"op": "append_prose", "text": "x\n"}],
    )
    assert result["success"] is False
    assert result["error_type"] == "FileNotFoundError"


def test_mutate_and_save_dry_run_skips_only_the_write(tmp_path):
    path = _saved(tmp_path, "a")
    before = path.read_bytes()
    plan = m.mutate_and_save(
        path, lambda p: m.add_task(p, "v0.1.0", "b"), dry_run=True
    )
    assert _texts(plan) == ["a", "b"]          # mutated in memory
    assert path.read_bytes() == before          # but not on disk


# --------------------------------------------------------------------------
# version / agent defaults
# --------------------------------------------------------------------------

def test_version_is_inherited_by_ops_that_address_an_iteration():
    plan = _plan("a")
    m.create_iteration(plan, "v0.1.1", "Next", major="v0.1")
    m.apply_ops(
        plan,
        [{"op": "add_task", "text": "b"}, {"op": "complete_task", "tasks": ["b"]}],
        version="v0.1.0",
    )
    assert _texts(plan) == ["a", "b"] and _done(plan) == [False, True]


def test_version_defaults_to_the_current_iteration():
    plan = _plan("a")
    m.start_iteration(plan, "v0.1.0")
    result = m.apply_ops(plan, [{"op": "add_task", "text": "b"}])
    assert result["resolved_version"] == "v0.1.0"
    assert _texts(plan) == ["a", "b"]


def test_the_default_is_resolved_once_so_closing_cannot_move_later_ops():
    """
    close_iteration strips the (current) marker, so a per-op lookup would send
    the following add somewhere else. The default is pinned before op 0.
    """
    plan = _plan("a")
    m.start_iteration(plan, "v0.1.0")
    m.create_iteration(plan, "v0.1.1", "Next", major="v0.1")
    m.apply_ops(
        plan,
        [
            {"op": "complete_task", "version": "v0.1.0", "index": 1},
            {"op": "close_iteration", "version": "v0.1.0"},
            {"op": "add_task", "text": "landed here"},
        ],
    )
    assert _texts(plan, "v0.1.0") == ["a", "landed here"]
    assert _texts(plan, "v0.1.1") == []


def test_version_is_never_inherited_by_the_create_ops():
    for op in ("create_major", "create_iteration"):
        with pytest.raises(ValueError, match="never inherited"):
            m.apply_ops(_plan("a"), [{"op": op, "title": "T"}], version="v0.1.0")


def test_versionless_ops_reject_a_version_key():
    for op, extra in (("append_prose", {"text": "x\n"}), ("add_to_backlog", {"text": "x"})):
        with pytest.raises(ValueError, match="unknown key"):
            m.apply_ops(_plan("a"), [{"op": op, "version": "v0.1.0", **extra}])


def test_no_version_and_no_current_iteration_is_a_clear_error():
    plan = m.empty_plan("Demo")
    with pytest.raises(ValueError, match="version is required"):
        m.apply_ops(plan, [{"op": "add_task", "text": "x"}])


def test_agent_default_reaches_ops_that_accept_one():
    plan = _plan()
    m.apply_ops(
        plan,
        [{"op": "add_tasks", "version": "v0.1.0", "tasks": ["a"]}],
        agent="claude-opus-5",
    )
    assert _texts(plan) == ["a [agent: claude-opus-5]"]


def test_agent_default_does_not_relabel_an_update():
    """
    update_task rewrites [agent: x] whenever agent is not None, so the batch
    default must not reach it — otherwise it silently reassigns authorship.
    """
    plan = _plan()
    m.add_task(plan, "v0.1.0", "written by codex", agent="codex")
    m.apply_ops(
        plan,
        [{"op": "update_task", "version": "v0.1.0", "index": 1, "text": "revised"}],
        agent="claude-opus-5",
    )
    assert _texts(plan) == ["revised [agent: codex]"]


def test_an_explicit_agent_on_update_task_still_works():
    plan = _plan()
    m.add_task(plan, "v0.1.0", "written by codex", agent="codex")
    m.apply_ops(
        plan,
        [{
            "op": "update_task", "version": "v0.1.0", "index": 1,
            "text": "revised", "agent": "claude-opus-5",
        }],
    )
    assert _texts(plan) == ["revised [agent: claude-opus-5]"]


def test_agent_default_is_not_passed_to_ops_without_the_parameter():
    """create_iteration's schema advertises agent but the function has none."""
    plan = _plan()
    m.apply_ops(
        plan,
        [{"op": "create_iteration", "version": "v0.1.1", "title": "Next", "major": "v0.1"}],
        agent="claude-opus-5",
    )
    assert plan.find_iteration("v0.1.1") is not None


# --------------------------------------------------------------------------
# shape validation
# --------------------------------------------------------------------------

def test_unknown_op_names_the_known_ones():
    with pytest.raises(ValueError, match="not a known operation"):
        m.apply_ops(_plan("a"), [{"op": "tick_everything"}])


def test_unknown_key_is_refused_with_its_op_index():
    with pytest.raises(ValueError, match=r"ops\[1\] \(complete_task\): unknown key"):
        m.apply_ops(
            _plan("a"),
            [
                {"op": "add_task", "version": "v0.1.0", "text": "b"},
                {"op": "complete_task", "version": "v0.1.0", "index": 1, "typo": 1},
            ],
        )


def test_missing_required_key_is_refused():
    with pytest.raises(ValueError, match="missing required key"):
        m.apply_ops(_plan("a"), [{"op": "add_tasks", "version": "v0.1.0"}])


def test_update_task_refuses_the_array_addresses_it_cannot_take():
    """mut.update_task has no tasks/indexes parameters — changes is the bulk form."""
    with pytest.raises(ValueError, match="unknown key"):
        m.apply_ops(
            _plan("a", "b"),
            [{"op": "update_task", "version": "v0.1.0", "indexes": [1], "text": "x"}],
        )


def test_update_task_changes_still_works_in_a_batch():
    plan = _plan("a", "b")
    m.apply_ops(
        plan,
        [{
            "op": "update_task", "version": "v0.1.0",
            "changes": [{"index": 1, "text": "A"}, {"index": 2, "text": "B"}],
        }],
    )
    assert _texts(plan) == ["A", "B"]


def test_ops_must_be_a_non_empty_list():
    for bad in ([], "nope", None, 7):
        with pytest.raises(ValueError, match="non-empty list"):
            m.apply_ops(_plan("a"), bad)


def test_an_op_must_be_an_object_with_an_op_name():
    with pytest.raises(ValueError, match=r"ops\[0\] must be an object"):
        m.apply_ops(_plan("a"), ["complete_task"])
    with pytest.raises(ValueError, match=r"ops\[0\]\.op is required"):
        m.apply_ops(_plan("a"), [{"version": "v0.1.0"}])


def test_the_op_cap_is_enforced_in_the_api_not_only_the_schema():
    ops = [{"op": "add_task", "version": "v0.1.0", "text": f"t{i}"} for i in range(51)]
    with pytest.raises(ValueError, match="exceeds cap of 50 ops"):
        m.apply_ops(_plan(), ops)


def test_a_full_cap_batch_applies():
    ops = [{"op": "add_task", "version": "v0.1.0", "text": f"t{i}"} for i in range(50)]
    plan = _plan()
    assert m.apply_ops(plan, ops)["applied"] == 50
    assert len(_texts(plan)) == 50


def test_shape_is_validated_before_any_mutation_runs():
    """A bad op late in the list leaves the in-memory plan untouched."""
    plan = _plan("a")
    with pytest.raises(ValueError):
        m.apply_ops(
            plan,
            [
                {"op": "complete_task", "version": "v0.1.0", "index": 1},
                {"op": "add_tasks", "version": "v0.1.0"},  # malformed
            ],
        )
    assert _done(plan) == [False]


# --------------------------------------------------------------------------
# index shift
# --------------------------------------------------------------------------

def test_index_addressing_after_a_removal_is_refused():
    with pytest.raises(ValueError, match="indexes have shifted"):
        m.apply_ops(
            _plan("a", "b", "c"),
            [
                {"op": "remove_task", "version": "v0.1.0", "index": 1},
                {"op": "complete_task", "version": "v0.1.0", "index": 2},
            ],
        )


def test_index_addressing_after_a_defer_is_refused():
    with pytest.raises(ValueError, match="indexes have shifted"):
        m.apply_ops(
            _plan("a", "b", "c"),
            [
                {"op": "defer_task", "version": "v0.1.0", "index": 1},
                {"op": "remove_task", "version": "v0.1.0", "indexes": [1]},
            ],
        )


def test_text_addressing_after_a_removal_is_allowed():
    plan = _plan("alpha", "beta", "gamma")
    m.apply_ops(
        plan,
        [
            {"op": "remove_task", "version": "v0.1.0", "task": "alpha"},
            {"op": "complete_task", "version": "v0.1.0", "tasks": ["gamma"]},
        ],
    )
    assert _texts(plan) == ["beta", "gamma"] and _done(plan) == [False, True]


def test_a_removal_in_another_iteration_does_not_block_indexes():
    plan = _plan("a", "b")
    m.create_iteration(plan, "v0.1.1", "Next", major="v0.1")
    m.add_task(plan, "v0.1.1", "x")
    m.apply_ops(
        plan,
        [
            {"op": "remove_task", "version": "v0.1.1", "index": 1},
            {"op": "complete_task", "version": "v0.1.0", "index": 2},
        ],
    )
    assert _done(plan, "v0.1.0") == [False, True]


def test_appending_does_not_shift_so_index_after_add_is_allowed():
    """add_task appends, so existing 1-based positions are untouched."""
    plan = _plan("a")
    m.apply_ops(
        plan,
        [
            {"op": "add_task", "version": "v0.1.0", "text": "b"},
            {"op": "complete_task", "version": "v0.1.0", "index": 1},
        ],
    )
    assert _done(plan) == [True, False]


# --------------------------------------------------------------------------
# MCP surface
# --------------------------------------------------------------------------

def test_apply_ops_is_exposed_with_every_op_in_its_enum():
    tools = {t.name: t for t in asyncio.run(list_tools())}
    assert "apply_ops" in tools
    schema = tools["apply_ops"].inputSchema
    enum = schema["properties"]["ops"]["items"]["properties"]["op"]["enum"]
    assert sorted(enum) == sorted(m._spec_table())
    assert schema["properties"]["ops"]["maxItems"] == m._OPS_CAP
    assert schema["required"] == ["ops"]


def test_every_op_name_is_also_a_real_tool():
    """Op names are tool names, so there is nothing new for a caller to learn."""
    names = {t.name for t in asyncio.run(list_tools())}
    assert set(m._spec_table()) <= names


def test_the_instructions_teach_the_single_call_turn_end():
    from powerplan.server import INSTRUCTIONS

    assert "apply_ops" in INSTRUCTIONS
    assert "nothing is written" in INSTRUCTIONS


def test_the_mcp_result_reports_each_op(tmp_path):
    path = _saved(tmp_path, "a", "b")
    result = _call(
        path,
        ops=[
            {"op": "complete_task", "version": "v0.1.0", "indexes": [1, 2]},
            {"op": "add_to_backlog", "text": "later"},
        ],
    )
    assert result["applied"] == 2
    assert [o["op"] for o in result["ops"]] == ["complete_task", "add_to_backlog"]
    assert result["resolved_version"] == "v0.1.0"
    assert result["check"]["ok"] is True


def test_empty_ops_is_rejected_at_the_server(tmp_path):
    path = _saved(tmp_path, "a")
    result = _call(path, ops=[])
    assert result["success"] is False and "non-empty" in result["error"]


# --------------------------------------------------------------------------
# one batch == N sequential calls
# --------------------------------------------------------------------------

def test_one_batch_is_byte_identical_to_the_same_ops_called_one_by_one(tmp_path):
    """
    A batch does one parse where N calls do N. Re-parsing is what supplies the
    blank line between a section and prose appended after it, so append_prose
    pads its own block instead of relying on that. Pinned here: batching is a
    change in how many writes happen, never in what gets written.
    """
    ops = [
        {"op": "complete_task", "version": "v0.1.0", "indexes": [1, 2]},
        {"op": "add_tasks", "version": "v0.1.0", "tasks": ["c"]},
        {"op": "add_to_backlog", "text": "later"},
        {"op": "create_iteration", "version": "v0.1.1", "title": "Next", "major": "v0.1"},
        {"op": "append_prose", "text": "## Notes\n"},
        {"op": "close_iteration", "version": "v0.1.0", "force": True},
    ]
    singles = [
        lambda p: m.complete_task(p, "v0.1.0", indexes=[1, 2]),
        lambda p: m.add_tasks(p, "v0.1.0", ["c"]),
        lambda p: m.add_to_backlog(p, "later"),
        lambda p: m.create_iteration(p, "v0.1.1", "Next", major="v0.1"),
        lambda p: m.append_prose(p, "## Notes\n"),
        lambda p: m.close_iteration(p, "v0.1.0", force=True),
    ]

    batched = tmp_path / "batched" / "PLAN.md"
    batched.parent.mkdir()
    m.save_plan(_plan("a", "b"), batched)
    m.mutate_and_save(batched, lambda p: m.apply_ops(p, ops))

    seq = tmp_path / "seq" / "PLAN.md"
    seq.parent.mkdir()
    m.save_plan(_plan("a", "b"), seq)
    for fn in singles:
        m.mutate_and_save(seq, fn)

    assert batched.read_bytes() == seq.read_bytes()


def test_appended_prose_is_separated_from_the_section_above_it():
    plan = _plan("a")
    m.apply_ops(
        plan,
        [
            {"op": "create_iteration", "version": "v0.1.1", "title": "Next", "major": "v0.1"},
            {"op": "append_prose", "text": "## Notes\n"},
        ],
    )
    assert "### v0.1.1 — Next\n\n## Notes\n" in m.write_plan(plan)
