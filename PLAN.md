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
- [ ] README agent guide: preferred tools (`get_current_iteration` / `get_iteration` first; avoid full-file reads)
- [ ] MCP registration snippets (`.mcp.json` / `claude mcp add`) for projects
- [ ] Install in two reference projects; agent-docs rule that powerplan is the sanctioned PLAN.md writer
- [ ] Smoke test: a coordinator agent drives one real iteration via powerplan only

## v0.2 — Plan path + bootstrap (no PLAN.md yet)

**Goal:** Every tool takes optional `plan_path`; default = walk-up from cwd. Agents can create a plan when none exists.

### v0.2.0 — Universal `plan_path` contract (audit + harden)
- [ ] Audit: every MCP tool schema includes optional `plan_path` (read + mutate + lifecycle)
- [ ] Default discovery: walk-up from cwd to nearest `PLAN.md` when `plan_path` omitted
- [ ] Explicit `plan_path` may be relative or absolute; resolve against cwd
- [ ] Mutations: if `plan_path` points at a missing file, error unless tool is `create_plan` (clear message)
- [ ] Tests: cwd discovery, override path, missing path error shape
- [ ] Docs: one-line rule — optional plan_path on every call; default = project PLAN.md

### v0.2.1 — `create_plan` bootstrap tool
- [ ] Tool `create_plan(title, goal?, philosophy?, plan_path?, force?)`
- [ ] Default path when omitted: `./PLAN.md` in cwd
- [ ] Writes powernote-style skeleton: H1, Goal/Philosophy, `---`, optional v0.1 shell
- [ ] Refuse to overwrite existing PLAN.md unless `force=true`
- [ ] Return JSON: path, created, skeleton summary
- [ ] Tests: create in temp dir; force overwrite; no-clobber default
- [ ] Agent guidance: if tools fail with no PLAN.md → create_plan then continue

### v0.2.2 — Lifecycle finish (carry from v0.1.3)
- [ ] `start_iteration` / `close_iteration` with header honesty
- [ ] `check_plan` structure lint
- [ ] Dogfood: operate this PLAN.md only via powerplan tools

## v0.3 — GitHub Pages: plans as the hero (examples + motion)

**Goal:** Site leads with **real plan examples** and a scroll/animated story of an agent calling MCP to grow and update a plan.

### v0.3.0 — Plan example gallery (static first)
- [ ] Curate 2–3 example plans as site fixtures (greenfield skeleton, mid-project + Current Status on top, multi-major history mini)
- [ ] Site section **Examples**: render plans as readable markdown panels (highlighted), not only product prose
- [ ] Caption each example: when to use it
- [ ] Link "Open raw" to fixture files in the repo
- [ ] Mobile-friendly stacked layout

### v0.3.1 — Animated MCP story (scroll-driven)
- [ ] Section **How agents use powerplan** — scrollytelling or stepped animation
- [ ] Story frames:
  1. No PLAN.md → `create_plan`
  2. Skeleton appears in example pane
  3. Tool chips: `create_major` / `create_iteration` / `add_task`
  4. Plan pane grows (lines animate in)
  5. `complete_task` → checkbox ticks
  6. `get_current_iteration` shows scoped JSON — agent never needed the whole file
- [ ] Framer Motion / CSS scroll steps; reduced-motion = static storyboard
- [ ] No multi-MB GIFs; keep Pages lightweight

### v0.3.2 — Site polish + deploy
- [ ] Lead narrative with examples; tools table secondary
- [ ] Integration copy: plan_path + create_plan + dual MCP with PowerSpawn
- [ ] Deploy Pages; visual QA desktop + mobile
- [ ] `npm run build` green; CI site job passes

## v0.4 — PowerSpawn coordination link (backlog)
- [ ] Default `agent` from PowerSpawn spawn id when tools run under a worker
- [ ] `plan_status_for_agents` compact context payload for spawn prompts
- [ ] `check_plan` as pre-commit/CI recipe docs

## Backlog
- Move **Current Status** to top of managed template (powernote convention)
- `update_task` / `remove_task` / `defer_task`
- ASCII gantt timeline view with dates (powerplan skill parity)
- Multi-plan workspaces (monorepos with nested PLAN.md files)
- Plan → GitHub issues export (one-way)
- Optional: structured tool output for Current Status section
