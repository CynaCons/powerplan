"""Backlog-last invariant: the backlog is always the final section (v0.5.0)."""

from __future__ import annotations

from pathlib import Path

from powerplan import mutations as m
from powerplan.plan_model import BacklogSection, Iteration, MajorSection, ProseBlock
from powerplan.plan_parser import parse_plan, parse_plan_file
from powerplan.plan_writer import write_plan


def _block_kinds(plan) -> list[str]:
    return [type(b).__name__ for b in plan.blocks]


def _backlog_pos(plan) -> int:
    for i, b in enumerate(plan.blocks):
        if isinstance(b, BacklogSection):
            return i
    return -1


def test_major_created_after_backlog_lands_before_it():
    """The reported bug: backlog first, then a major → major must precede it."""
    plan = m.empty_plan("Demo")
    m.add_to_backlog(plan, "Idea A")
    m.create_major(plan, "v0.2", "Editor rewrite")
    m.create_iteration(plan, "v0.2.1", "Parser cleanup", major="v0.2")
    m.add_task(plan, "v0.2.1", "Rewrite tokenizer")

    kinds = _block_kinds(plan)
    assert kinds[-1] == "BacklogSection", kinds
    assert "MajorSection" in kinds
    assert kinds.index("MajorSection") < _backlog_pos(plan)


def test_top_level_iteration_after_backlog_lands_before_it():
    plan = m.empty_plan("Demo")
    m.add_to_backlog(plan, "Idea A")
    m.create_iteration(plan, "v0.1.0", "Scaffold")

    kinds = _block_kinds(plan)
    assert kinds[-1] == "BacklogSection", kinds
    assert kinds.index("Iteration") < _backlog_pos(plan)


def test_prose_and_separator_stay_above_backlog():
    plan = m.empty_plan("Demo")
    m.add_to_backlog(plan, "Idea A")
    m.append_prose(plan, "## Current Status\n")
    m.add_separator(plan)

    assert _block_kinds(plan)[-1] == "BacklogSection"
    text = write_plan(plan)
    assert text.index("## Current Status") < text.index("- Idea A")


def test_backlog_additions_still_append_within_section():
    plan = m.empty_plan("Demo")
    m.add_to_backlog(plan, "Idea A")
    m.create_major(plan, "v0.2", "Later")
    m.add_to_backlog(plan, "Idea B")

    items = [i.text for i in plan.all_backlog_items()]
    assert items == ["Idea A", "Idea B"]
    assert _block_kinds(plan)[-1] == "BacklogSection"


def test_normalize_relocates_already_broken_plan(tmp_path: Path):
    """Existing plans written before the fix are healed on the next mutation."""
    broken = (
        "# Demo\n"
        "\n"
        "## Backlog\n"
        "- Idea A\n"
        "\n"
        "## v0.2 — Editor rewrite\n"
        "\n"
        "### v0.2.1 — Parser cleanup\n"
        "- [ ] Rewrite tokenizer\n"
    )
    path = tmp_path / "PLAN.md"
    # write_bytes: write_text would translate \n to \r\n on Windows
    path.write_bytes(broken.encode("utf-8"))

    # Parse alone must not rewrite anything (round-trip guarantee holds)
    assert write_plan(parse_plan_file(path)) == broken

    # Any mutation heals the ordering
    m.mutate_and_save(path, lambda p: m.complete_task(p, "v0.2.1", "Rewrite tokenizer"))

    healed = path.read_text(encoding="utf-8")
    assert healed.index("## v0.2") < healed.index("## Backlog")
    assert healed.rstrip().endswith("- Idea A")
    assert "- [x] Rewrite tokenizer" in healed

    reparsed = parse_plan(healed)
    assert _block_kinds(reparsed)[-1] == "BacklogSection"


def test_blank_line_before_appended_headers():
    plan = m.empty_plan("Demo")
    m.add_to_backlog(plan, "Idea A")
    m.create_major(plan, "v0.2", "Editor rewrite")
    m.create_iteration(plan, "v0.2.1", "Parser cleanup", major="v0.2")
    m.normalize_plan(plan)

    text = write_plan(plan)
    assert "\n\n## v0.2 — Editor rewrite\n" in text
    assert "\n\n### v0.2.1 — Parser cleanup\n" in text
    assert "\n\n## Future (Backlog)\n" in text
    # No header ever jammed onto a preceding content line
    for line in text.splitlines():
        assert not line.startswith("- Idea A##")


def test_relocated_backlog_drops_trailing_divider(tmp_path: Path):
    """A `---` separating the backlog from later majors must not trail at EOF."""
    broken = (
        "# Demo\n\n"
        "## Backlog\n"
        "- Idea A\n\n"
        "---\n\n"
        "## v0.2 — Editor rewrite\n\n"
        "### v0.2.1 — Parser cleanup\n"
        "- [ ] Rewrite tokenizer\n"
    )
    path = tmp_path / "PLAN.md"
    path.write_bytes(broken.encode("utf-8"))
    m.mutate_and_save(path, lambda p: m.complete_task(p, "v0.2.1", "Rewrite tokenizer"))

    healed = path.read_text(encoding="utf-8")
    assert healed.index("## v0.2") < healed.index("## Backlog")
    assert healed.rstrip().endswith("- Idea A")
    assert not healed.rstrip().endswith("---")
    assert healed.endswith("\n")


def test_backlog_already_last_keeps_its_content(tmp_path: Path):
    """No relocation → nothing is stripped, even a legitimate trailing rule."""
    good = (
        "# Demo\n\n"
        "## v0.2 — Editor rewrite\n\n"
        "### v0.2.1 — Parser cleanup\n"
        "- [ ] Rewrite tokenizer\n\n"
        "## Backlog\n"
        "- Idea A\n\n"
        "---\n"
    )
    path = tmp_path / "PLAN.md"
    path.write_bytes(good.encode("utf-8"))
    m.mutate_and_save(path, lambda p: m.complete_task(p, "v0.2.1", "Rewrite tokenizer"))

    healed = path.read_text(encoding="utf-8")
    assert healed.rstrip().endswith("---")
    assert "- Idea A" in healed


def test_add_task_does_not_bury_separator_blank_lines(tmp_path: Path):
    """
    Regression: the blank line padded before `## Backlog` is re-parsed into the
    preceding iteration's body. Appending past it buried one blank per call,
    so tasks ended up double-spaced.
    """
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    m.mutate_and_save(path, lambda p: m.add_to_backlog(p, "Idea A"))
    m.mutate_and_save(path, lambda p: m.create_major(p, "v0.2", "M"))
    m.mutate_and_save(path, lambda p: m.create_iteration(p, "v0.2.1", "I", major="v0.2"))
    for n in range(4):
        m.mutate_and_save(path, lambda p, n=n: m.add_task(p, "v0.2.1", f"task {n}"))

    text = path.read_text(encoding="utf-8")
    block = text[text.index("### v0.2.1") :]
    assert "\n\n- [ ]" not in block, f"blank line between tasks:\n{block!r}"

    it = parse_plan(text).find_iteration("v0.2.1")
    assert [t.text for t in it.tasks] == [f"task {n}" for n in range(4)]
    # body order must match tasks order
    assert [b.text for b in it.body if hasattr(b, "done")] == [f"task {n}" for n in range(4)]


def test_add_to_backlog_does_not_accumulate_blanks(tmp_path: Path):
    path = tmp_path / "PLAN.md"
    m.create_plan(title="Demo", plan_path=path)
    for n in range(4):
        m.mutate_and_save(path, lambda p, n=n: m.add_to_backlog(p, f"Idea {n}"))

    text = path.read_text(encoding="utf-8")
    tail = text[text.index("## Future (Backlog)") :]
    assert "\n\n- " not in tail, f"blank line between backlog items:\n{tail!r}"
    assert [i.text for i in parse_plan(text).all_backlog_items()] == [
        f"Idea {n}" for n in range(4)
    ]


def test_normalize_is_idempotent():
    plan = m.empty_plan("Demo")
    m.add_to_backlog(plan, "Idea A")
    m.create_major(plan, "v0.2", "Editor rewrite")

    once = write_plan(m.normalize_plan(plan))
    twice = write_plan(m.normalize_plan(plan))
    assert once == twice


def test_check_plan_flags_content_after_backlog():
    broken = (
        "# Demo\n\n"
        "## Backlog\n"
        "- Idea A\n\n"
        "## v0.2 — Editor rewrite\n\n"
        "### v0.2.1 — Parser cleanup\n"
        "- [ ] Rewrite tokenizer\n"
    )
    report = m.check_plan(parse_plan(broken))
    codes = [i["code"] for i in report["issues"]]
    assert "content_after_backlog" in codes
    assert report["ok"] is False


def test_check_plan_clean_when_backlog_last():
    good = (
        "# Demo\n\n"
        "## v0.2 — Editor rewrite\n\n"
        "### v0.2.1 — Parser cleanup (ACTIVE)\n"
        "- [ ] Rewrite tokenizer\n\n"
        "## Backlog\n"
        "- Idea A\n"
    )
    report = m.check_plan(parse_plan(good))
    codes = [i["code"] for i in report["issues"]]
    assert "content_after_backlog" not in codes


def test_plan_with_no_backlog_still_appends():
    plan = m.empty_plan("Demo")
    m.create_major(plan, "v0.1", "Foundation")
    m.create_major(plan, "v0.2", "Next")

    kinds = _block_kinds(plan)
    assert kinds.count("MajorSection") == 2
    text = write_plan(plan)
    assert text.index("v0.1") < text.index("v0.2")
