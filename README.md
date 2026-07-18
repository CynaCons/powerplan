# powerplan

**PLAN.md as the operational backbone of agentic development.**

`powerplan` is a standalone [MCP](https://modelcontextprotocol.io) server that
gives coordinators and worker agents a **human-language API** over your
project’s `PLAN.md`: show progress, create iterations, complete tasks, keep the
header truthful — without freeform file thrash.

| | |
|---|---|
| **Server name** | `powerplan` |
| **Status** | v0.1.1 — read tools shipped; mutations next ([PLAN.md](PLAN.md)) |
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

## Tools (v0.1.1)

| Tool | Behavior |
|------|----------|
| `show_plan` | ASCII overview of majors + iterations with progress |
| `show_current_iteration` | Detail of the active / first-open iteration |
| `get_iteration` | Structured JSON for one version |
| `list_iterations` | Filter: open / complete / all |
| `get_backlog` | Backlog items |
| `find_task` | Substring search over tasks |

Every tool accepts optional `plan_path`; otherwise powerplan walks up from cwd
to the nearest `PLAN.md`.

Mutations (`create_iteration`, `complete_task`, …) land in **v0.1.2+**.

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
