"""Mutation API + powernote-style formatting tests."""

from __future__ import annotations

from pathlib import Path

from powerplan import mutations as m
from powerplan.plan_parser import parse_plan
from powerplan.plan_writer import write_plan


def test_powernote_style_headers():
    assert m.format_major_header("v0.1", "Foundation") == "## v0.1 — Foundation\n"
    assert (
        m.format_iteration_header("v0.1.0", "Scaffold")
        == "### v0.1.0 — Scaffold\n"
    )
    assert m.format_task_line("do thing", done=True) == "- [x] do thing\n"
    assert m.format_blockquote("hello") == "> hello\n"


def test_create_major_iteration_tasks_roundtrip(tmp_path: Path):
    plan = m.empty_plan("Demo Plan")
    m.set_preamble(
        plan,
        "# Demo Plan\n\n**Goal:** Prove mutations.\n\n---\n\n",
    )
    m.create_major(plan, "v0.1", "Foundation", description="First slice")
    m.create_iteration(
        plan, "v0.1.0", "Scaffold", major="v0.1", goal="Boot the app"
    )
    m.add_task(plan, "v0.1.0", "Init project", done=True)
    m.add_task(plan, "v0.1.0", "Wire stores", done=False, agent="grok-4.5")
    m.complete_task(plan, "v0.1.0", "Wire stores")

    text = write_plan(plan)
    assert "## v0.1 — Foundation" in text
    assert "> First slice" in text
    assert "### v0.1.0 — Scaffold" in text
    assert "**Goal:** Boot the app" in text
    assert "- [x] Init project" in text
    assert "- [x] Wire stores" in text

    path = tmp_path / "PLAN.md"
    path.write_text(text, encoding="utf-8")
    again = parse_plan(path.read_text(encoding="utf-8"))
    it = again.find_iteration("v0.1.0")
    assert it is not None
    assert it.done_count == 2
    assert it.total_count == 2


def test_recreate_powernote_preserves_content_backlog_last():
    """
    Full PowerNote PLAN rebuild via the mutation-driven recreate script.

    Until v0.5.0 this asserted a byte-identical rebuild. PowerNote's plan puts
    ``## Future (Backlog)`` mid-document with further majors after it, and the
    backlog-last invariant deliberately relocates that section — so the
    guarantee is now: no content is lost, and rebuild and source converge to
    the same normalized document.
    """
    source = Path(r"C:\dev\private-repo\PowerNote\PLAN.md")
    if not source.is_file():
        return  # skip if machine lacks private clone
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.recreate_plan import rebuild

    from powerplan.plan_parser import parse_plan_file

    text = rebuild(source)
    src = source.read_text(encoding="utf-8")

    # Every line survives the rebuild, only section order changes
    assert sorted(text.splitlines()) == sorted(src.splitlines())

    # Backlog ends up last in the rebuilt document
    rebuilt = parse_plan(text)
    assert type(rebuilt.blocks[-1]).__name__ == "BacklogSection"

    # Both sides normalize to exactly the same bytes
    norm_rebuild = write_plan(m.normalize_plan(rebuilt))
    norm_source = write_plan(m.normalize_plan(parse_plan_file(source)))
    assert norm_rebuild.replace("\r\n", "\n") == norm_source.replace("\r\n", "\n")


def test_current_iteration_prefers_current_marker():
    from powerplan.plan_parser import parse_plan

    md = """# Demo

## v0.1 — A
### v0.1.0 — Old open
- [ ] leftover planned work

## Current Status

| Iteration | Status |
|-----------|--------|
| v0.1.0 | shipped |
| v0.2.0 | **current** — active work |

## v0.2 — B
### v0.2.0 — Real current (current)
- [ ] do the thing
"""
    plan = parse_plan(md)
    cur = plan.current_iteration()
    assert cur is not None
    assert cur.version == "v0.2.0"
    assert "current" in cur.title.lower() or cur.is_open


def test_current_from_status_table_without_title_marker():
    from powerplan.plan_parser import parse_plan

    md = """# Demo

## v0.1 — A
### v0.1.0 — Planned later
- [ ] not current

## Current Status
| v0.1.0 | done |
| v0.2.0 | **current** — focus |

## v0.2 — B
### v0.2.0 — Focus work
- [ ] ship it
"""
    plan = parse_plan(md)
    cur = plan.current_iteration()
    assert cur is not None
    assert cur.version == "v0.2.0"
