# Changelog

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
