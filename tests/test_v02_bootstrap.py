"""v0.2 plan_path, create_plan, lifecycle, check_plan."""

from __future__ import annotations

from pathlib import Path

import pytest

from powerplan.discovery import find_plan_md, resolve_plan_path
from powerplan import mutations as m
from powerplan.plan_parser import parse_plan_file
from powerplan.plan_writer import write_plan


def test_resolve_plan_path_override(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "custom" / "PLAN.md"
    target.parent.mkdir()
    target.write_text("# X\n", encoding="utf-8")
    p = resolve_plan_path("custom/PLAN.md", must_exist=True)
    assert p == target.resolve()


def test_resolve_missing_must_exist_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="create_plan"):
        resolve_plan_path("nope/PLAN.md", must_exist=True)


def test_resolve_default_cwd_walk(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    plan = tmp_path / "PLAN.md"
    plan.write_text("# Root\n", encoding="utf-8")
    monkeypatch.chdir(nested)
    found = find_plan_md()
    assert found == plan.resolve()


def test_create_plan_no_clobber(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", goal="Ship", plan_path=path)
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "# Demo" in text
    assert "**Goal:** Ship" in text
    assert "### v0.1.0" in text
    with pytest.raises(FileExistsError):
        m.create_plan(title="Other", plan_path=path, force=False)
    m.create_plan(title="Forced", plan_path=path, force=True)
    assert "# Forced" in path.read_text(encoding="utf-8")


def test_mutate_missing_file_errors(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    with pytest.raises(FileNotFoundError, match="create_plan"):
        m.mutate_and_save(path, lambda p: None, allow_create=False)


def test_start_close_iteration_and_check(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Life", goal="Cycle", plan_path=path)
    plan = parse_plan_file(path)
    m.create_iteration(plan, "v0.1.1", "Next", major="v0.1")
    m.add_task(plan, "v0.1.1", "work item", done=False)
    write_plan_file = __import__("powerplan.plan_writer", fromlist=["write_plan_file"]).write_plan_file
    write_plan_file(plan, path)

    def start(p):
        m.start_iteration(p, "v0.1.1")

    m.mutate_and_save(path, start)
    plan = parse_plan_file(path)
    cur = plan.current_iteration()
    assert cur is not None
    assert cur.version == "v0.1.1"
    assert "current" in cur.title.lower() or (cur.status or "").upper() == "ACTIVE"

    with pytest.raises(ValueError, match="open task"):
        m.mutate_and_save(path, lambda p: m.close_iteration(p, "v0.1.1", force=False))

    m.mutate_and_save(path, lambda p: m.complete_task(p, "v0.1.1", "work item"))
    m.mutate_and_save(
        path, lambda p: m.close_iteration(p, "v0.1.1", force=False, stamp="2026-07-18")
    )
    plan = parse_plan_file(path)
    it = plan.find_iteration("v0.1.1")
    assert it is not None
    assert it.is_complete
    report = m.check_plan(plan)
    assert report["ok"] is True
    assert report["iteration_count"] >= 2


def test_check_plan_flags_complete_with_open():
    from powerplan.plan_parser import parse_plan

    md = """# T
### v0.1.0 — Done (COMPLETE)
- [ ] still open
"""
    report = m.check_plan(parse_plan(md))
    assert report["ok"] is False
    assert any(i["code"] == "complete_with_open_tasks" for i in report["issues"])
