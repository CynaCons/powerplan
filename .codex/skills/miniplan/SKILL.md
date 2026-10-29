---
name: miniplan
description: >
  Render a miniplan — a turn-end task report printed in the chat, in PLAN.md
  format: the current iteration seeded from show_miniplan, plus quick off-plan
  items this turn is tracking. Use when ending a multi-step turn, when asked for
  a "miniplan", "turn tracker" or "task snapshot", or when tracking temporary
  items that are not PLAN.md-worthy yet. Chat output only; never a file.
---

# Miniplan

Read [docs/MINIPLAN.md](../../../docs/MINIPLAN.md). That file owns the format,
the template and the example. Do not copy them into this skill.

A miniplan is a snapshot and a scratchpad, not a plan: the live iteration
verbatim from `show_miniplan` with checkboxes flipped, plus an `## Off-plan`
section for whatever else this turn is tracking.

## Do

1. `show_miniplan` → paste the iteration block verbatim, checkboxes flipped.
2. Put anything not in `PLAN.md` under `## Off-plan`, same checkbox format.
3. Mark each off-plan item `→ plan`, `→ backlog`, or `→ drop`.
4. Print the whole thing in the reply.
5. Sync: `complete_task` for the ticks, `add_tasks` for `→ plan`,
   `add_to_backlog` for `→ backlog`. Batch the calls.
6. Then the turn-end status view: `show_current_iteration`, verbatim, in a code
   block.

## Constraints

- Chat only. Never write a miniplan to a file, in the repo or anywhere else.
- Never hand-edit `PLAN.md`; mutations go through powerplan tools only.
- Plan-backed text is copied byte-for-byte; to reword it use `update_task`.
- Plan tasks and off-plan items never share a section.
- `→ drop` is a normal outcome for an off-plan item. No justification needed.
