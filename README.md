<!-- mcp-name: io.github.CynaCons/powerplan -->

# powerplan

**PLAN.md as the operational backbone of agentic development.**

`powerplan` is an [MCP](https://modelcontextprotocol.io) server that gives
coordinators and worker agents a human-language API over your project’s
`PLAN.md`: show progress, create iterations, complete tasks, keep the header
truthful — without freeform file thrash.

mcp-name: io.github.CynaCons/powerplan

| | |
|---|---|
| **MCP server name** | `powerplan` |
| **PyPI** | [`powerplan-mcp`](https://pypi.org/project/powerplan-mcp/) (`powerplan` is a different, unrelated package) |
| **Registry** | `io.github.CynaCons/powerplan` |
| **Status** | v0.6.1 — public package + registry listing ([PLAN.md](PLAN.md)) |
| **Site** | [GitHub Pages](https://cynacons.github.io/powerplan/) |
| **Pairs with** | [PowerSpawn](https://github.com/CynaCons/PowerSpawn) (optional) |

---

## Install

You need [uv](https://docs.astral.sh/uv/) (provides `uvx`) or Python 3.10+.

```bash
uvx powerplan-mcp
```

That is the stdio MCP server. Point your client at it:

### Claude Code / Cursor / `.mcp.json`

```json
{
  "mcpServers": {
    "powerplan": {
      "command": "uvx",
      "args": ["powerplan-mcp"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Claude Desktop

Same block in `claude_desktop_config.json` (`mcpServers`).

### Grok (`~/.grok/config.toml` or project config)

```toml
[mcp_servers.powerplan]
command = "uvx"
args = ["powerplan-mcp"]
env = { PYTHONUNBUFFERED = "1", PYTHONIOENCODING = "utf-8" }
enabled = true
```

### pip (no uv)

```bash
pip install powerplan-mcp
```

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

---

## Agent guide

Prefer scoped tools. Do **not** read all of `PLAN.md` to figure out what to do.

1. If tools fail with “no PLAN.md” → `create_plan` first.
2. `get_current_iteration` — what to work on now (JSON).
3. `get_iteration(version)` — one iteration’s tasks and progress.
4. Mutate with `add_task` / `complete_task` / `start_iteration` / `close_iteration`.
5. `show_plan` is a human skim, not a dump.

Every tool accepts optional `plan_path` (relative or absolute). Default: walk up
from cwd to the nearest `PLAN.md`.

Optional `agent` on mutations writes a trailing `[agent: id]` tag on the touched line.

---

## Why

Agents often edit `PLAN.md` by hand. Headers drift, “COMPLETE” gets stamped
without proof, and multi-agent swarms step on each other. powerplan is the
**single writer**: tolerant reader, surgical writer, optional `[agent: …]` tags.

---

## Tools

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

---

## Managed plan format

| Construct | Pattern |
|-----------|---------|
| Major | `## vX.Y — Title` |
| Iteration | `### vX.Y.Z — Title` |
| Goal | `**Goal:** …` |
| Tasks | `- [ ]` / `- [x]` |
| Backlog | `## Backlog` |

Phase-like headers and other prose are **preserved as opaque blocks**.

---

## From source

Clone, editable install, or PowerSpawn submodule — for contributors.

```bash
git clone https://github.com/CynaCons/powerplan.git
cd powerplan
pip install -e ".[dev]"
python -m powerplan          # same stdio server
# or: powerplan-mcp
```

PowerSpawn can vendor this repo as a git submodule. Register **both** MCP
servers — they do not merge:

```json
{
  "mcpServers": {
    "powerplan": {
      "command": "uvx",
      "args": ["powerplan-mcp"]
    },
    "powerspawn": {
      "command": "python",
      "args": ["-m", "powerspawn.mcp_server"]
    }
  }
}
```

Path-only (no install): `python /path/to/powerplan/powerplan_server.py`

Landing page: `cd site && npm ci && npm run dev`

---

## Releasing (maintainers)

Full procedure, identities, and failure history: **[docs/RELEASING.md](docs/RELEASING.md)**.
Agent checklist: project skill `release-powerplan` (`/release-powerplan`).

Short path: bump every version file listed in that guide → `pytest -q` → tag
`vX.Y.Z` → push the tag. `.github/workflows/publish.yml` uploads `powerplan-mcp`
to PyPI, then `server.json` to the MCP Registry as `io.github.CynaCons/powerplan`.

---

## License

MIT — see [LICENSE](LICENSE).
