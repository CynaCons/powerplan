# Miniplan

A **miniplan** is a turn-end task report an agent prints in the chat, written in
PLAN.md's own conventions. It is a snapshot and a scratchpad — never a plan, and
never a file.

`show_miniplan` (the MCP tool, v0.8.0) returns a read-only slice of `PLAN.md`.
A miniplan is what the agent *does* with that slice during a turn: flips
checkboxes, adds whatever else it is tracking, and reports the result.

This file owns the format. The agent skills under `.claude/`, `.cursor/`,
`.codex/` and `.grok/` point here and must not copy the template.

## Rules

1. **Chat only.** Print the miniplan in the reply. Never write it to a file —
   not in the repo, not in a scratch directory, not in `.powerplan/`.
2. **Seed from the plan.** Call `show_miniplan` and paste the returned iteration
   block verbatim: same goal text, same task text, same order. Flip checkboxes
   to this turn's real state. Byte-for-byte, so the block is always diffable
   against the live plan. To change the wording, use `update_task` and re-seed.
3. **Off-plan items are first-class.** Anything the turn is tracking that
   `PLAN.md` does not know about goes under `## Off-plan`, in the same checkbox
   format. Quick, temporary, exploratory items belong here with no ceremony and
   no commitment that they ever reach the plan.
4. **Give each off-plan item a disposition** before the turn ends: `→ plan`,
   `→ backlog`, or `→ drop`. `→ drop` is a normal outcome and needs no
   justification. An undecided off-plan item means the turn is not finished.
5. **Keep the two halves apart.** Plan-backed tasks and off-plan items never mix
   in one section; that is how scratch leaks into the plan.
6. **Sync the plan.** `complete_task` for each tick in the iteration block,
   `add_tasks` for `→ plan`, `add_to_backlog` for `→ backlog`. Batch the calls.
   `PLAN.md` changes only through powerplan tools, never by hand.
7. **Then the status view.** The miniplan does not replace the turn-end rule:
   follow it with `show_current_iteration` pasted verbatim in a code block.
8. **Fresh every turn.** Re-seed from `show_miniplan`; never carry a stale
   miniplan forward.

## Template

~~~markdown
# Miniplan — <iteration or turn label>
**Source:** PLAN.md § <major> → <iteration> · **Agent:** <id> · <timestamp>
**Status:** <n>/<m> plan · <n>/<m> off-plan

<the show_miniplan block, verbatim, checkboxes flipped>

## Off-plan
> Tracked this turn only. Not in PLAN.md unless marked → plan / → backlog.
- [x] <quick item> → drop
- [ ] <item worth keeping> → backlog

## Sync
- [ ] complete_task ×<n>
- [ ] add_to_backlog ×<n>
~~~

Drop the `## Off-plan` section when there is nothing off-plan, and the `## Sync`
section once the calls are made.

## Example

~~~markdown
# Miniplan — v0.9.0 turn
**Source:** PLAN.md § v0.9 → v0.9.0 · **Agent:** claude-opus-5 · 2026-10-29T14:03Z
**Status:** 2/4 plan · 2/3 off-plan

### v0.9.0 — Server instructions: status view at the end of each major turn
**Goal:** Every MCP client connected to powerplan is told, at initialize, to end
each major turn with show_current_iteration pasted verbatim in a code block;
release 0.9.0 to PyPI + MCP Registry.
- [x] server.py: INSTRUCTIONS sent at initialize (server.py:53-60)
- [x] Test: initialize over stdio returns the instructions (pytest -q green)
- [ ] Bump version files to 0.9.0 (pyproject, __init__, server.json, test_packaging, CHANGELOG, README)
- [ ] Release per docs/RELEASING.md: push, tag, GitHub release, Publish run

## Off-plan
> Tracked this turn only. Not in PLAN.md unless marked → plan / → backlog.
- [x] read docs/RELEASING.md → drop
- [x] check no Publish run already queued → drop
- [ ] check_plan should warn on a future-dated header → backlog

## Sync
- [ ] complete_task ×2
- [ ] add_to_backlog ×1
~~~
