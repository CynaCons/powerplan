# powerplan — Implementation Plan

**Goal:** Ship an MCP server that makes PLAN.md the operational backbone of
agentic development. See [PRD.md](PRD.md).

**Philosophy:** Single writer. Evidence or it didn't happen (process, not MCP
enforcement). Tolerant reader, surgical writer. Lightweight optional agent tags.
Dogfood: this PLAN.md is operated by powerplan itself from v0.1.3 on.

**Repo:** standalone [github.com/CynaCons/powerplan](https://github.com/CynaCons/powerplan);
PowerSpawn vendors this repo as a git submodule.

**Stack:** Python 3.10+ (same as PowerSpawn), `mcp` SDK, stdlib parser — no new
heavy deps.

---

## v0.1 — Core server (read → write → lifecycle)

### v0.1.0 — Server scaffold + plan model + parser
- [x] `powerplan/` package: `plan_model.py` (MajorSection/Iteration/Task/Backlog dataclasses), `plan_parser.py`, `plan_writer.py` (pytest green)
- [x] `powerplan_server.py` entry point (MCP stdio server, own name `powerplan`) (import + list_tools OK)
- [x] Discovery: walk up from cwd to nearest PLAN.md; `plan_path` override on every tool (test_discovery_explicit_path)
- [x] Tolerant parser: `## vX.Y`/`### vX.Y.Z` iterations, `- [ ]`/`- [x]` tasks, `**Goal:**` lines, backlog section; phase-like headers and unrecognized prose preserved as opaque blocks (powerplanner + powernote fixtures)
- [x] Round-trip tests: powerplanner PLAN.md and powernote PLAN.md parse + rewrite byte-identical when no mutation (pytest byte-identical)
- [x] Smoke test: server starts, `show_plan` renders both reference plans (ASCII overview; tools registered)

### v0.1.1 — Read/show tools
- [x] `show_plan` (ASCII overview with progress %), `show_current_iteration` (ASCII detail) (smoke on fixtures)
- [x] `get_iteration`, `list_iterations(filter)`, `get_backlog`, `find_task` (MCP tools list; model helpers tested)
- [x] Smoke test: outputs verified against powerplanner + powernote plans (pytest green)

### v0.1.2 — Mutation tools + optional agent tags + surgical writer
- [x] `create_major` / `create_iteration` (version uniqueness), `set_iteration_goal`
- [x] `add_task` / `complete_task` / `reopen_task` / `add_to_backlog` / `append_prose`
- [x] Optional `agent` on mutation tools → trailing tag `[agent: <id>]` on touched lines
- [x] Surgical writes + file lock (`mutate_and_save`); powernote-style `—` headers
- [x] Parser: unversioned `##` sections (Planned / Current Status) no longer swallow prior iteration tasks
- [x] Smoke: recreate PowerNote PLAN.md via mutations → `temp.md` byte-identical (CRLF-preserving)
- [ ] `update_task` / `remove_task` / `defer_task(reason?)` (remaining CRUD niceties)


### v0.1.3 — Lifecycle + minimal check_plan
- [ ] `complete_task(version, task, agent?)` — tick only; no evidence parameter
- [ ] `reopen_task(version, task, agent?)`
- [ ] `start_iteration` (header auto-sync), `close_iteration` (reports open tasks; requires `force=true` to close over them; stamps date)
- [ ] `check_plan` minimal structure lint: version monotonicity, malformed checkboxes/sections, header/active-iteration drift
- [ ] Dogfood switch: this PLAN.md now operated via powerplan tools only
- [ ] Smoke test: full iteration lifecycle driven through tools; `check_plan` green

### v0.1.4 — Packaging + adoption
- [ ] README section in PowerSpawn: what powerplan is + agentic workflow guide
- [ ] MCP registration snippets (`.mcp.json` / `claude mcp add`) for projects
- [ ] Install in two reference projects; agent-docs rule that powerplan is the sanctioned PLAN.md writer
- [ ] Smoke test: a coordinator agent drives one real iteration via powerplan only

## v0.2 — PowerSpawn coordination link (backlog)
- [ ] Default `agent` from PowerSpawn spawn id when tools run under a worker
- [ ] `plan_status_for_agents` compact context payload for spawn prompts
- [ ] `check_plan` as pre-commit/CI recipe docs

## Backlog
- ASCII gantt timeline view with dates (powerplan skill parity)
- Multi-plan workspaces (monorepos with nested PLAN.md files)
- Plan → GitHub issues export (one-way)
