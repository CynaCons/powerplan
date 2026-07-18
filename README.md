# powerplan

**PLAN.md as the operational backbone of agentic development.**

`powerplan` is a standalone [MCP](https://modelcontextprotocol.io) server that
gives coordinators and worker agents a **human-language API** over your
project’s `PLAN.md`: show progress, create iterations, complete tasks, keep the
header truthful — without freeform file thrash.

| | |
|---|---|
| **Server name** | `powerplan` |
| **Status** | v0.2.2 — create_plan, mutations, lifecycle, check_plan ([PLAN.md](PLAN.md)) |
| **PRD** | [PRD.md](PRD.md) |
| **Site** | [GitHub Pages](https://cynacons.github.io/powerplan/) |
| **Pairs with** | [PowerSpawn](https://github.com/CynaCons/PowerSpawn) (optional submodule) |

---

## Why

Agents often edit `PLAN.md` by hand. Headers drift, “COMPLETE” gets stamped
without proof, and multi-agent swarms step on each other. powerplan is the
**single writer**: tolerant reader, surgical writer, optional `[agent: …]` tags.

---

## Install

### Option A — clone + editable install

```bash
git clone https://github.com/CynaCons/powerplan.git
cd powerplan
pip install -e ".[dev]"
```

### Option B — via PowerSpawn (submodule)

Projects that already use PowerSpawn can pull powerplan automatically:

```bash
git submodule update --init --recursive   # if PowerSpawn vendors powerplan/
```

Then point MCP at `powerplan/powerplan_server.py` or `python -m powerplan`
with `PYTHONPATH` including the submodule root.

### Option C — path-only (no install)

```bash
python /path/to/powerplan/powerplan_server.py
```

---

## MCP registration

### Claude Code / project `.mcp.json`

```json
{
  "mcpServers": {
    "powerplan": {
      "command": "python",
      "args": ["-m", "powerplan"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Grok (`~/.grok/config.toml` or project config)

```toml
[mcp_servers.powerplan]
command = "python"
args = ["-m", "powerplan"]
env = { PYTHONUNBUFFERED = "1" }
enabled = true
```

### Alongside PowerSpawn

```json
{
  "mcpServers": {
    "powerplan": {
      "command": "python",
      "args": ["-m", "powerplan"]
    },
    "powerspawn": {
      "command": "python",
      "args": ["-m", "powerspawn.mcp_server"]
    }
  }
}
```

Register **both** as separate servers — nesting in a monorepo does not merge MCPs.

---

## Tools (v0.2.2)

**Every tool accepts optional `plan_path`** (relative or absolute). Default: walk
up from cwd to the nearest `PLAN.md`.

| Tool | Behavior |
|------|----------|
| `create_plan` | Bootstrap `./PLAN.md` (or `plan_path`) when missing; `force` to overwrite |
| `get_current_iteration` | **Preferred for agents** — scoped JSON for current work |
| `get_iteration` | JSON for one version (tasks, progress) |
| `list_iterations` / `find_task` / `get_backlog` | Navigate without full-file reads |
| `create_major` / `create_iteration` / `add_task` / … | Surgical mutations |
| `complete_task` / `reopen_task` | Checkbox updates; optional `[agent: id]` |
| `start_iteration` / `close_iteration` | ACTIVE/current vs COMPLETE lifecycle |
| `check_plan` | Structure lint |
| `show_plan` / `show_current_iteration` | Compact human skim (not a full dump) |

Agent rule: prefer `get_current_iteration` / `get_iteration` over reading all of PLAN.md.
If no plan exists → `create_plan` first.

---

## Managed plan format

| Construct | Pattern |
|-----------|---------|
| Major | `## vX.Y — Title` |
| Iteration | `### vX.Y.Z — Title` |
| Goal | `**Goal:** …` |
| Tasks | `- [ ]` / `- [x]` |
| Backlog | `## Backlog` |

Phase-like headers and other prose are **preserved as opaque blocks** (tolerant
reader). See PRD for principles (single writer, no evidence journal in the tool).

---

## Development

```bash
pip install -e ".[dev]"
pytest -q
python -m powerplan   # stdio MCP (use with an MCP client)
```

Landing page:

```bash
cd site && npm ci && npm run dev
```

---

## License

MIT — see [LICENSE](LICENSE).
