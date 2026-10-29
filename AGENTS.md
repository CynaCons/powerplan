# Agent rules — powerplan

`PLAN.md` is the backbone of this repo and is written **only** through the
powerplan MCP tools (`uvx powerplan-mcp`). Never hand-edit it.

- **Session start:** `show_miniplan` (or `get_current_iteration`). Do not read
  all of `PLAN.md`.
- **During the turn:** register work as tasks before doing it; tick with
  `complete_task` once it is done and verified.
- **Turn end:** print a **miniplan** — see [docs/MINIPLAN.md](docs/MINIPLAN.md)
  — then paste `show_current_iteration` verbatim in a ``` code block.
- **Releasing:** [docs/RELEASING.md](docs/RELEASING.md).

Skills: `.claude/skills/`, `.cursor/skills/`, `.codex/skills/`, `.grok/skills/`
(`miniplan`, `release-powerplan`). `.cursor/rules/miniplan.mdc` mirrors the
miniplan rule for Cursor rule-based setups.
