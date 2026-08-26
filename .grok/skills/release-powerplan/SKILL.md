---
name: release-powerplan
description: >
  Ship a new powerplan MCP version to PyPI (powerplan-mcp) and the official MCP
  Registry (io.github.CynaCons/powerplan). Use when releasing, publishing,
  tagging, bumping the package version, updating the MCP listing, or when the
  user says "publish to PyPI", "publish to the registry", "cut a release",
  "uvx powerplan-mcp", or runs /release-powerplan.
---

# Release powerplan

Before any version bump or tag, read [docs/RELEASING.md](../../../docs/RELEASING.md).
That file owns names, URLs, workflow filenames, and failure history. Do not
copy those tables into this skill.

## Do

1. Confirm the product change is on `main` and `python -m pytest -q` is green.
2. Bump the version in every file listed under **Version files** in `docs/RELEASING.md`.
3. Commit, `git push origin main`, tag `vX.Y.Z`, push the tag, `gh release create`.
4. **Always** start publish yourself — do not wait for the tag `push` event
   (agent pushes often do not trigger workflows):
   `gh workflow run Publish --ref vX.Y.Z`
   then `gh run watch <id> --exit-status`.
   If `site/**` changed, also `gh workflow run "Deploy Landing Page"`.
5. Verify PyPI and the MCP Registry URLs in `docs/RELEASING.md`.
6. Record progress with powerplan tools (`complete_task` / `close_iteration`).
   Do not hand-edit `PLAN.md`.

## Constraints

- PyPI project is `powerplan-mcp`. MCP server name and import stay `powerplan`.
- Registry name is `io.github.CynaCons/powerplan` (GitHub org casing).
- Publish channel is PyPI + MCP Registry. Not npm.
- Never retag a version that already has a wheel on PyPI.
- Never remove `mcp-name: io.github.CynaCons/powerplan` from `README.md`.
- Site (`site/`) deploys separately; a tag is not a Pages deploy.
