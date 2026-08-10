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
- [x] `complete_task(version, task, agent?)` — tick only; no evidence parameter
- [x] `reopen_task(version, task, agent?)`
- [x] `start_iteration` (header auto-sync), `close_iteration` (reports open tasks; requires `force=true` to close over them; stamps date)
- [x] `check_plan` minimal structure lint: version monotonicity, malformed checkboxes/sections, header/active-iteration drift
- [x] Dogfood switch: this PLAN.md now operated via powerplan tools only
- [x] Smoke test: full iteration lifecycle driven through tools; `check_plan` green

### v0.1.4 — Packaging + adoption
- [ ] README agent guide: preferred tools (`get_current_iteration` / `get_iteration` first; avoid full-file reads)
- [ ] MCP registration snippets (`.mcp.json` / `claude mcp add`) for projects
- [ ] Install in two reference projects; agent-docs rule that powerplan is the sanctioned PLAN.md writer
- [ ] Smoke test: a coordinator agent drives one real iteration via powerplan only

## v0.2 — Plan path + bootstrap (no PLAN.md yet)

**Goal:** Every tool takes optional `plan_path`; default = walk-up from cwd. Agents can create a plan when none exists.

### v0.2.0 — Universal `plan_path` contract (audit + harden)
- [x] Audit: every MCP tool schema includes optional `plan_path` (read + mutate + lifecycle)
- [x] Default discovery: walk-up from cwd to nearest `PLAN.md` when `plan_path` omitted
- [x] Explicit `plan_path` may be relative or absolute; resolve against cwd
- [x] Mutations: if `plan_path` points at a missing file, error unless tool is `create_plan` (clear message)
- [x] Tests: cwd discovery, override path, missing path error shape
- [x] Docs: one-line rule — optional plan_path on every call; default = project PLAN.md

### v0.2.1 — `create_plan` bootstrap tool
- [x] Tool `create_plan(title, goal?, philosophy?, plan_path?, force?)`
- [x] Default path when omitted: `./PLAN.md` in cwd
- [x] Writes powernote-style skeleton: H1, Goal/Philosophy, `---`, optional v0.1 shell
- [x] Refuse to overwrite existing PLAN.md unless `force=true`
- [x] Return JSON: path, created, skeleton summary
- [x] Tests: create in temp dir; force overwrite; no-clobber default
- [x] Agent guidance: if tools fail with no PLAN.md → create_plan then continue

### v0.2.2 — Lifecycle finish (carry from v0.1.3)
- [x] `start_iteration` / `close_iteration` with header honesty
- [x] `check_plan` structure lint
- [x] Dogfood: operate this PLAN.md only via powerplan tools

## v0.3 — GitHub Pages: plans as the hero (examples + motion)

**Goal:** Site leads with **real plan examples** and a scroll/animated story of an agent calling MCP to grow and update a plan.

### v0.3.0 — Plan example gallery (static first)
- [x] Curate 2–3 example plans as site fixtures (greenfield skeleton, mid-project + Current Status on top, multi-major history mini)
- [x] Site section **Examples**: render plans as readable markdown panels (highlighted), not only product prose
- [x] Caption each example: when to use it
- [x] Link "Open raw" to fixture files in the repo
- [x] Mobile-friendly stacked layout

### v0.3.1 — Animated MCP story (scroll-driven)
- [x] Section **How agents use powerplan** — scrollytelling or stepped animation
- [x] Story frames:
  1. No PLAN.md → `create_plan`
  2. Skeleton appears in example pane
  3. Tool chips: `create_major` / `create_iteration` / `add_task`
  4. Plan pane grows (lines animate in)
  5. `complete_task` → checkbox ticks
  6. `get_current_iteration` shows scoped JSON — agent never needed the whole file
- [x] Framer Motion / CSS scroll steps; reduced-motion = static storyboard
- [x] No multi-MB GIFs; keep Pages lightweight

### v0.3.2 — Site polish + deploy
- [x] Lead narrative with examples; tools table secondary
- [x] Integration copy: plan_path + create_plan + dual MCP with PowerSpawn
- [x] Deploy Pages; visual QA desktop + mobile
- [x] `npm run build` green; CI site job passes

## v0.4 — PowerSpawn coordination link (backlog)
- [ ] Default `agent` from PowerSpawn spawn id when tools run under a worker
- [ ] `plan_status_for_agents` compact context payload for spawn prompts
- [ ] `check_plan` as pre-commit/CI recipe docs

## v0.5 — Plan structure invariants
> Ordering guarantees the writer must uphold regardless of mutation order.

### v0.5.0 — Backlog pinned last (2026-08-07) (COMPLETE)
**Goal:** The backlog section is always the final block of a plan; new majors, iterations and prose are inserted before it, and existing plans with a misplaced backlog are normalized on mutation.
- [x] `_insert_top_level(plan, node)` helper: insert before the first BacklogSection, else append
- [x] `create_major` / `create_iteration` / `append_prose` / `add_separator` route through the helper
- [x] Normalize existing plans: relocate a misplaced backlog to the end on mutation (unmutated parse→write stays byte-identical)
- [x] Blank line before appended `##` / `###` headers (no jammed sections)
- [x] `check_plan` lint rule: warn when content follows the backlog section
- [x] Tests: backlog-then-major ordering, normalization of an already-broken plan, round-trip fixtures still byte-identical

### v0.5.1 — Task editing CRUD
**Goal:** Address tasks by text (existing matcher) with an optional 1-based index within the iteration as disambiguator; optional `expect` guard gives compare-and-swap safety on destructive edits. No task IDs, no line numbers.

- [ ] `_resolve_task(it, task?, index?, expect?)` shared resolver — exactly one of task/index required
- [ ] `update_task(version, task?, index?, text, expect?, agent?)` — rewrites text, preserves done state
- [ ] `remove_task(version, task?, index?, expect?)` — drops from both `tasks` and `body`
- [ ] `defer_task(version, task?, index?, reason?)` — move task to backlog with optional reason suffix
- [ ] Retrofit optional `index` onto `complete_task` / `reopen_task`; expose 1-based `index` in `get_iteration` payload
- [ ] Tests: index/text equivalence, `expect` mismatch refuses edit, ambiguous text error, defer round-trip, agent tags preserved

## Backlog
- Move **Current Status** to top of managed template (powernote convention)
- `update_task` / `remove_task` / `defer_task`
- ASCII gantt timeline view with dates (powerplan skill parity)
- Multi-plan workspaces (monorepos with nested PLAN.md files)
- Plan → GitHub issues export (one-way)
- Optional: structured tool output for Current Status section
- `recreate_plan.py` byte-identity now requires a backlog-last source; PowerNote's plan was normalized (backlog moved below v0.27, redundant `---` dropped) to restore it
