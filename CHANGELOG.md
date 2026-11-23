# Changelog

## 0.11.0 — 2026-11-23

Bulk operations.

- **`apply_ops`** — a new tool that applies a list of *different* mutations in
  one write. Each op is `{"op": "<tool name>", ...that tool's arguments}`, the
  14 op names are the existing mutating tools, and they run in order so
  create → populate → close works in one call. If any op fails **nothing is
  written**, and the error names the op by position
  (`failed_op: {"i": 3, "op": "close_iteration"}`), so `PLAN.md` is never left
  half-updated by a turn-end that went wrong partway.
- `version` is inherited by ops that address an existing iteration and resolved
  **once** before the first op, so a `close_iteration` in the batch cannot
  silently redirect the ops after it. `create_major` / `create_iteration` always
  need their own; `add_to_backlog` / `append_prose` take none. `agent` is
  inherited only where the underlying tool accepts one, and never by
  `update_task`, which would otherwise relabel another agent's work.
- `dry_run` applies a batch in memory and reports it without writing, raising
  everything a real call would.
- Addressing by index in an iteration where an earlier op in the same batch
  removed or deferred a row is refused, naming both ops: those positions have
  shifted. Appending never shifts, so index-after-add still works.
- The result carries `check_plan`'s verdict (`check.ok`, `check.issue_count`),
  so a batch that leaves the document dirty says so without another call.
- `write_plan_file` now writes via a temp file and `os.replace`, so a crash
  mid-write cannot truncate `PLAN.md` — it matters more now that one write
  carries a whole turn.
- `append_prose` separates a new block from the section above it, keeping one
  batch byte-identical to the same ops called one at a time.
- `_file_lock` is re-entrant, and the MCP `instructions` tell every client to
  send turn-end bookkeeping as a single `apply_ops` call.
- Format and rules: [docs/BULK.md](docs/BULK.md). 25 tools.

## 0.10.0 — 2026-10-29

Miniplan turn report.

- The server's MCP `instructions` now define the **miniplan**: a turn-end task
  report in PLAN.md's own format, printed in the chat and never written to a
  file. It is the `show_miniplan` block pasted verbatim with its checkboxes
  flipped, followed by an `## Off-plan` section for quick items the turn is
  tracking that are not in `PLAN.md`, each marked `-> plan`, `-> backlog` or
  `-> drop`. Every client (Claude Code, Codex, Cursor, Grok, ...) receives it at
  initialize.
- `show_miniplan` description says it seeds the turn-end report.
- `docs/MINIPLAN.md` owns the format, template and example.
- Project skill `miniplan` shipped for four agents — `.claude/skills/`,
  `.cursor/skills/`, `.codex/skills/`, `.grok/skills/` — plus
  `.cursor/rules/miniplan.mdc` and a repo-root `AGENTS.md`.

## 0.9.0 — 2026-10-08

Turn-end status view for every agent.

- The server now sends MCP `instructions` at initialize, so every client (Claude Code,
  Codex, Cursor, ...) gets the same rules: open a session with `show_miniplan`, register
  and tick work through powerplan, and end each major turn by pasting
  `show_current_iteration` verbatim in a code block.
- `show_current_iteration` description says the same.

## 0.8.0 — 2026-09-19

Miniplan.

- `show_miniplan(version?, before?, after?)` — the plan's own format as the
  agent view: the current (or named) iteration as raw PLAN.md text under its
  major header, with the neighbouring iterations collapsed to their header
  lines. Session opener for PowerFlow (D11: PLAN.md first and last).

## 0.7.0 — 2026-08-26

Batch mutations.

- `add_tasks(version, tasks)` — append several checkbox tasks in one locked
  write. Prefer this over repeated `add_task`. Shared `done` / `agent` apply
  to every item; empty list or blank items refuse the whole batch.
- Arity-independent mutations: `complete_task`, `reopen_task`, `remove_task`,
  and `defer_task` accept `indexes[]` or `tasks[]` for several items in one
  write (resolve-all then apply; cap 100; duplicates refused). `update_task`
  takes `changes[]` of `{text, index|task, expect?}`. `add_to_backlog` takes
  `texts[]`. Singular `index`/`task`/`text` still work. No new `*_tasks` tools.

## 0.6.1 — 2026-08-22

- MCP Registry namespace is `io.github.CynaCons/powerplan` (GitHub org casing;
  lowercase `cynacons` is rejected by OIDC).

## 0.6.0 — 2026-08-22

Public distribution.

- PyPI project name `powerplan-mcp` (PyPI `powerplan` is an unrelated Windows
  powercfg wrapper). Import and MCP server name stay `powerplan`.
- Console script `powerplan-mcp` so `uvx powerplan-mcp` starts the stdio server.
- `server.json` for official MCP Registry namespace `io.github.cynacons/powerplan`.
- README and site lead with the public install path.
- Tag-triggered publish workflow: PyPI trusted publishing, then `mcp-publisher`.
- Pin the Python MCP SDK to `mcp>=1.0.0,<2` (v2 changed the Server API).

## 0.5.1 — 2026-08-10

Task editing CRUD: `update_task` / `remove_task` / `defer_task` with text or
1-based `index`, plus an optional `expect` compare-and-swap guard.

## 0.5.0 — 2026-08-07

Backlog is always the last section of a plan. Mutations insert before it and
normalize a misplaced backlog.

## 0.3.2

Site polish and GitHub Pages deploy.

## 0.3.1

Scroll-driven “how agents use powerplan” story.

## 0.3.0

Plan example gallery on the landing page.

## 0.2.2

Lifecycle finish: `start_iteration` / `close_iteration` / `check_plan`; dogfood
this repo’s PLAN.md through the tools.

## 0.2.1

`create_plan` bootstrap tool.

## 0.2.0

Optional `plan_path` on every tool; default walk-up from cwd.

## 0.1.3

Lifecycle tools and minimal `check_plan`.

## 0.1.2

Mutation tools, optional `[agent: …]` tags, surgical writer.

## 0.1.1

Read/show tools.

## 0.1.0

Server scaffold, plan model, tolerant parser.
