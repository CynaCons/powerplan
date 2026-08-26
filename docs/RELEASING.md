# Releasing powerplan

How to ship a new version of the **powerplan** MCP to PyPI and the official
MCP Registry. This file is the source of truth. The project skill
`.grok/skills/release-powerplan/SKILL.md` is the agent checklist; it must not
fork these facts.

Read this before tagging. Do not invent a second package name, registry
namespace, or publish channel.

---

## What we ship, and why

powerplan is a **Python stdio MCP**. It writes the user’s local `PLAN.md`.
There is no hosted/remote MCP and no npm package.

| Identity | Value | Why |
|----------|--------|-----|
| GitHub | [CynaCons/powerplan](https://github.com/CynaCons/powerplan) (public) | Source, Actions, Releases, Pages |
| GitHub repo id | `1304953873` | `server.json` `repository.id` |
| MCP **server** name | `powerplan` | `Server("powerplan")` in `powerplan/server.py` |
| Python **import** | `powerplan` | `python -m powerplan` |
| Console scripts | `powerplan-mcp` and `powerplan` | both → `powerplan.server:run_sync` |
| **PyPI** project | [`powerplan-mcp`](https://pypi.org/project/powerplan-mcp/) | PyPI name `powerplan` is an unrelated Windows `powercfg` wrapper |
| **MCP Registry** name | `io.github.CynaCons/powerplan` | GitHub OIDC namespace; **org casing must match `CynaCons`** |
| `mcp-name` proof | `mcp-name: io.github.CynaCons/powerplan` in `README.md` | Registry fetches the PyPI README and requires this exact string |
| Public run command | `uvx powerplan-mcp` | `uvx` is uv’s `npx`: ephemeral install + run the console script |
| pip fallback | `pip install powerplan-mcp` then `python -m powerplan` | no uv required |
| Site | https://cynacons.github.io/powerplan/ | Vite app in `site/`; **separate** workflow from package publish |
| Python MCP SDK | `mcp>=1.0.0,<2` | SDK v2 removed `Server.list_tools`; CI will fail if unpinned |

We publish **Python to PyPI**, then metadata to the MCP Registry. We do **not**
publish to npm. The registry is a catalog; it does not host the code.

`uvx` comes from [uv](https://docs.astral.sh/uv/). Clients that lack uv should
use the pip snippet in the README.

---

## Version files (keep equal)

Bump **all** of these to the same `X.Y.Z` (no leading `v` except the git tag):

1. `pyproject.toml` → `[project] version`
2. `powerplan/__init__.py` → `__version__` (the MCP server version is this import)
3. `server.json` → top-level `version` **and** `packages[0].version`
4. `tests/test_packaging.py` → `test_package_version_aligned` expected string
5. `CHANGELOG.md` → new `## X.Y.Z` section at the top
6. `README.md` → status row (`vX.Y.Z — …`)

Git tag and GitHub Release title use a leading **`v`**: `vX.Y.Z`.

`tests/test_packaging.py` also asserts:

- console scripts `powerplan-mcp` and `powerplan`
- `server.json` name `io.github.CynaCons/powerplan`, PyPI id `powerplan-mcp`
- README contains `mcp-name: io.github.CynaCons/powerplan`

Do not remove the HTML comment `<!-- mcp-name: io.github.CynaCons/powerplan -->`
at the top of `README.md`.

---

## One-time setup (already done)

Do **not** redo these unless they were deleted.

### PyPI trusted publisher

No API token in the repo. GitHub Actions OIDC publishes the wheel.

- PyPI owner: `CynaCons`
- Project: `powerplan-mcp`
- Publisher: GitHub, owner `CynaCons`, repo `powerplan`
- Workflow filename: **`publish.yml`** (must match `.github/workflows/publish.yml`)
- Environment: **empty** (the workflow does not set `environment:`)

Manage at https://pypi.org/manage/account/publishing/  
First publish used a **pending publisher**; after 0.6.0 succeeded it became a
normal trusted publisher on the project.

If a future run fails with `invalid-publisher` / `Publisher with matching
claims was not found`, the workflow name, owner, repo, or environment drifted
from this table.

### MCP Registry

No stored token. The same `publish.yml` job runs:

```text
./mcp-publisher login github-oidc
./mcp-publisher publish
```

OIDC grants `io.github.CynaCons/*`. Publishing `io.github.cynacons/powerplan`
(lowercase) returns **403**. That was 0.6.0; 0.6.1 corrected the name.

GitHub org membership for the publishing identity must stay such that Actions
on `CynaCons/powerplan` can mint that namespace (public org membership if GitHub
starts requiring it).

### GitHub

- Actions permissions on `publish.yml`: `id-token: write`, `contents: read`
- Topics already set: `mcp`, `mcp-server`, `agents`, `plan`, `python`
- Pages: `.github/workflows/deploy-site.yml` on `site/**` (not on tags)

---

## Routine release (every version)

Work on `main`, via powerplan tools for `PLAN.md`.

1. **Land the product change** on `main`. CI (`.github/workflows/ci.yml`) must
   be green: `pip install -e ".[dev]"` then `pytest -q`.
2. **Bump versions** in the list above. Changelog first line is the new section.
3. **Local smoke**
   ```bash
   python -m pytest -q
   ```
   Optional: JSON-RPC `tools/list` against `python -m powerplan` (22 tools as of
   0.6.x).
4. **Commit** the version bump (conventional: `chore: release X.Y.Z` or
   `feat(vX.Y.Z): …`).
5. **Tag and push**
   ```bash
   git push origin main
   git tag vX.Y.Z
   git push origin vX.Y.Z
   gh release create vX.Y.Z --title "vX.Y.Z — <one line>" --notes-file CHANGELOG.md
   ```
   Pushing the tag is what starts `.github/workflows/publish.yml`.
6. **Watch**
   ```bash
   gh run watch --repo CynaCons/powerplan --exit-status
   ```
   The job: test → `python -m build` → PyPI (`skip-existing: true`) → sleep 45s
   (PyPI must serve the new README) → `mcp-publisher` → registry.
7. **Verify**
   - https://pypi.org/project/powerplan-mcp/ — version is `X.Y.Z`
   - https://pypi.org/pypi/powerplan-mcp/json — `info.version`
   - https://registry.modelcontextprotocol.io/v0/servers?search=powerplan —
     `name` is `io.github.CynaCons/powerplan`, `version` is `X.Y.Z`,
     `_meta.….status` is `active`
8. **Site copy** (only if install/docs snippets changed): `site/` hero and
   Integration still say `uvx powerplan-mcp`. Pages deploys itself from `main`
   when `site/**` changes.

Never move or reuse a tag that already published a wheel. If 0.6.1 is on PyPI,
the next release is **0.6.2** (or 0.7.0), not a retag of 0.6.1.

---

## What `publish.yml` does

Trigger: push of tags `v*`, or `workflow_dispatch`.

| Step | Notes |
|------|--------|
| Checkout | Tag SHA, so `server.json` version must already match the tag |
| Python 3.12 | Same as CI |
| `pip install -e ".[dev]" build` | Tests need the editable console scripts |
| `python -m pytest -q` | Includes packaging tests |
| `python -m build` | sdist + wheel in `dist/` |
| `pypa/gh-action-pypi-publish` | Trusted publishing; `skip-existing: true` so a retry does not fail if the wheel is already on PyPI |
| `sleep 45` | Registry ownership check reads PyPI README; too-early publish 403s/fails validation |
| `mcp-publisher login github-oidc` + `publish` | Uploads repo-root `server.json` |

Manual registry-only (wheel already on PyPI, need a new `server.json`):

```bash
mcp-publisher login github
mcp-publisher publish
```

That device-login path is for a human laptop. Agents on GitHub Actions must use
OIDC as in the workflow.

---

## Failures we have already hit

| Symptom | Cause | Fix |
|---------|--------|-----|
| CI/test collection: `Server` has no `list_tools` | `pip` resolved `mcp` 2.x | Keep `mcp>=1.0.0,<2` |
| PyPI `invalid-publisher` | Trusted publisher missing or workflow name/env mismatch | Workflow file **must** be `publish.yml`; environment must stay unset |
| Registry `403` “You have permission to publish: `io.github.CynaCons/*`” | `server.json` / README used `io.github.cynacons/powerplan` | Use `CynaCons` exactly; bump a **new** PyPI version so the README proof updates |
| Registry “package validation failed” | PyPI README lacks `mcp-name: io.github.CynaCons/powerplan`, or sleep was too short | Keep both the HTML comment and the visible line in README; keep the 45s wait |
| Wanted `pip install powerplan` | Name taken | Always `powerplan-mcp` on PyPI |
| Tag `v*` push did not queue `publish.yml` | Observed on `v0.7.0` | `gh workflow run Publish --ref vX.Y.Z` (workflow_dispatch is already on the workflow) |

---

## Related workflows (not the package)

| Workflow | When | What |
|----------|------|------|
| `.github/workflows/ci.yml` | push/PR `main` | pytest |
| `.github/workflows/deploy-site.yml` | push `site/**` or `workflow_dispatch` | GitHub Pages |
| `.github/workflows/publish.yml` | tag `v*` | PyPI + MCP Registry |

Site install copy lives in `site/src/components/Hero.tsx` and `Integration.tsx`.
Changing those does not publish a new wheel.

---

## History (first public cut, 2026-08-22)

- **0.6.0** — first PyPI upload (`powerplan-mcp`). Registry publish failed on
  namespace casing.
- **0.6.1** — README + `server.json` use `io.github.CynaCons/powerplan`. PyPI
  and registry both succeeded. Listing is **active**.
- **0.7.0** — batch mutations (`add_tasks`, arity-independent `indexes`/`tasks` /
  `changes` / `texts`). PyPI + registry both succeeded. Tag push did not start
  `publish.yml`; dispatched with `gh workflow run Publish --ref v0.7.0`.

GitHub Releases: `v0.6.0`, `v0.6.1`, `v0.7.0`.
