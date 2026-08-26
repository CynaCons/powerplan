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
- [x] `update_task` / `remove_task` / `defer_task(reason?)` (remaining CRUD niceties)


### v0.1.3 — Lifecycle + minimal check_plan
- [x] `complete_task(version, task, agent?)` — tick only; no evidence parameter
- [x] `reopen_task(version, task, agent?)`
- [x] `start_iteration` (header auto-sync), `close_iteration` (reports open tasks; requires `force=true` to close over them; stamps date)
- [x] `check_plan` minimal structure lint: version monotonicity, malformed checkboxes/sections, header/active-iteration drift
- [x] Dogfood switch: this PLAN.md now operated via powerplan tools only
- [x] Smoke test: full iteration lifecycle driven through tools; `check_plan` green

### v0.1.4 — Packaging + adoption (absorbed into v0.6) (COMPLETE)

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

### v0.5.1 — Task editing CRUD (2026-08-10) (COMPLETE)
**Goal:** Address tasks by text (existing matcher) with an optional 1-based index within the iteration as disambiguator; optional `expect` guard gives compare-and-swap safety on destructive edits. No task IDs, no line numbers.

- [x] `_resolve_task(it, task?, index?, expect?)` shared resolver — exactly one of task/index required
- [x] `update_task(version, task?, index?, text, expect?, agent?)` — rewrites text, preserves done state
- [x] `remove_task(version, task?, index?, expect?)` — drops from both `tasks` and `body`
- [x] `defer_task(version, task?, index?, reason?)` — move task to backlog with optional reason suffix
- [x] Retrofit optional `index` onto `complete_task` / `reopen_task`; expose 1-based `index` in `get_iteration` payload
- [x] Tests: index/text equivalence, `expect` mismatch refuses edit, ambiguous text error, defer round-trip, agent tags preserved

## v0.6 — Public distribution
> Stranger-installable package: PyPI name `powerplan-mcp` (PyPI `powerplan` is taken), `uvx` entry, official MCP Registry listing, README/site rewritten for people who have never seen this repo.

### v0.6.0 — PyPI package `powerplan-mcp` + uvx entry (2026-08-22) (COMPLETE)
**Goal:** Publishable Python package a stranger can run with `uvx powerplan-mcp`. Keep MCP server name and import as `powerplan`. PyPI project name cannot be `powerplan` (taken by a Windows powercfg wrapper).
- [x] PyPI project name `powerplan-mcp` (PyPI `powerplan` is taken); keep Python import and MCP server name `powerplan` [agent: grok-4.6]
- [x] Console script `powerplan-mcp` so `uvx powerplan-mcp` starts the stdio server [agent: grok-4.6]
- [x] pyproject.toml: classifiers, keywords, project.urls; version string matches the release we will tag [agent: grok-4.6]
- [x] Smoke: `python -m powerplan` and `powerplan-mcp` both speak MCP stdio (list_tools) [agent: grok-4.6]

### v0.6.1 — Official MCP Registry listing (2026-08-22) (COMPLETE)
**Goal:** List `io.github.cynacons/powerplan` on the official MCP Registry so clients and aggregators can discover it. Requires the PyPI package from v0.6.0.
- [x] `server.json` for `io.github.cynacons/powerplan` pointing at the PyPI package, stdio transport [agent: grok-4.6]
- [x] README includes `mcp-name: io.github.cynacons/powerplan` (PyPI ownership proof for the registry) [agent: grok-4.6]
- [x] Document `mcp-publisher login github` + `publish` for maintainers [agent: grok-4.6]
- [x] Publish to the official MCP Registry once the PyPI package is live [agent: grok-4.6]

### v0.6.2 — README + site for strangers (2026-08-22) (COMPLETE)
**Goal:** Lead with a 30-second install path. Clone, editable install, and PowerSpawn submodule move under “from source.” Absorb leftover v0.1.4 agent-guide and MCP snippet work.
- [x] README rewrite: `uvx powerplan-mcp` first; clone / editable / PowerSpawn under from-source [agent: grok-4.6]
- [x] Agent guide: prefer `get_current_iteration` / `get_iteration`; `create_plan` if missing; avoid full-file reads [agent: grok-4.6]
- [x] MCP snippets: Claude Code `.mcp.json`, Claude Desktop, Cursor, Grok (`uvx` / `uv run --with`) [agent: grok-4.6]
- [x] Site hero + Integration: replace `pip install -e ".[dev]"` with the public `uvx` path [agent: grok-4.6]

### v0.6.3 — Release, changelog, optional dogfood
**Goal:** Tagged public release with changelog and GitHub topics. Optional: install in two reference projects with the agent-docs rule that powerplan is the sanctioned PLAN.md writer.
- [x] CHANGELOG.md covering shipped versions through this release [agent: grok-4.6]
- [x] GitHub Release + topics (`mcp`, `agents`, `plan`) [agent: grok-4.6]
- [x] Optional: tag → PyPI publish workflow [agent: grok-4.6]
- [ ] Optional: install in two reference projects; agent-docs rule that powerplan is the sanctioned PLAN.md writer [agent: grok-4.6]
- [x] Maintainer release guide (docs/RELEASING.md) + project skill for future MCP publishes [agent: grok-4.6]

## v0.7 — Batch mutations
> Agents can append several tasks in one locked write instead of N add_task round-trips.

### v0.7.0 — add_tasks batch append (2026-08-26) (COMPLETE)
**Goal:** One MCP call appends many checkbox tasks to an iteration in a single locked write. Prefer this over repeated add_task.
- [x] add_tasks mutation: list of texts, one write, shared done/agent; refuse empty list or blank items (no partial write) [agent: grok-4.6]
- [x] MCP tool add_tasks (tasks: string[], minItems 1) + richer JSON (added count, indexes) [agent: grok-4.6]
- [x] Tests: order preserved, atomic refuse, agent/done, insert-before-trailing-blanks, list_tools exposes add_tasks [agent: grok-4.6]
- [x] README / PRD / site tools table / CHANGELOG Unreleased [agent: grok-4.6]

### v0.7.1 — Arity-independent batch mutations (2026-08-26) (COMPLETE)
**Goal:** complete/reopen/remove/defer/update/add_to_backlog accept one or many items on the same tool, one locked write, atomic resolve-then-apply.
- [x] Address kernel: _normalize_address + _resolve_many (cap 100, dups, resolve-then-apply) [agent: grok-4.6]
- [x] complete/reopen/remove/defer accept indexes[] or tasks[] [agent: grok-4.6]
- [x] update_task(changes[]) + add_to_backlog(texts[]) [agent: grok-4.6]
- [x] MCP schemas + _mutate_result richer JSON (updated + original indexes) [agent: grok-4.6]
- [x] Tests: resolve-then-apply, dups, mixed addressing, atomic expect, cap, MCP call_tool [agent: grok-4.6]
- [x] README / PRD / site tools / CHANGELOG Unreleased [agent: grok-4.6]

### v0.7.2 — Publish 0.7.0 to PyPI + MCP Registry (2026-08-26) (COMPLETE)
**Goal:** Tag v0.7.0 so publish.yml uploads powerplan-mcp 0.7.0 to PyPI and io.github.CynaCons/powerplan to the MCP Registry.
- [x] Bump version files to 0.7.0 (pyproject, __init__, server.json, test_packaging, CHANGELOG, README) [agent: grok-4.6]
- [x] pytest -q green (packaging asserts 0.7.0) [agent: grok-4.6]
- [x] Commit feat(v0.7.0), push main, tag v0.7.0, gh release create [agent: grok-4.6]
- [x] Watch publish.yml; verify PyPI 0.7.0 and registry io.github.CynaCons/powerplan [agent: grok-4.6]

### v0.7.3 — Agent releases dispatch Publish (2026-08-26) (COMPLETE)
**Goal:** Do not wait for a tag push event. After tagging, always gh workflow run Publish --ref vX.Y.Z. Document why agent git push does not start CI/Publish.
- [x] RELEASING.md + skill: dispatch Publish is a required step, not a fallback [agent: grok-4.6]
- [x] publish.yml comment + concurrency; ci.yml workflow_dispatch [agent: grok-4.6]

## Backlog
- Move **Current Status** to top of managed template (powernote convention)
- Backlog item CRUD: `update_backlog_item` / `remove_backlog_item` (iteration tasks got this in v0.5.1; backlog entries are still append-only)
- ASCII gantt timeline view with dates (powerplan skill parity)
- Multi-plan workspaces (monorepos with nested PLAN.md files)
- Plan → GitHub issues export (one-way)
- Optional: structured tool output for Current Status section
- `recreate_plan.py` byte-identity now requires a backlog-last source; PowerNote's plan was normalized (backlog moved below v0.27, redundant `---` dropped) to restore it
