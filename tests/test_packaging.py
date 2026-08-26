"""v0.6.0 packaging: PyPI name, console scripts, MCP list_tools."""

from __future__ import annotations

import asyncio
import json
from importlib.metadata import entry_points
from pathlib import Path

from powerplan import __version__
from powerplan.server import SERVER_VERSION, list_tools, run_sync


def test_package_version_aligned():
    assert __version__ == "0.7.0"
    assert SERVER_VERSION == __version__


def test_console_scripts_registered():
    eps = entry_points()
    scripts = eps.select(group="console_scripts") if hasattr(eps, "select") else eps.get("console_scripts", [])
    by_name = {ep.name: ep for ep in scripts}
    assert "powerplan-mcp" in by_name
    assert "powerplan" in by_name
    assert by_name["powerplan-mcp"].value == "powerplan.server:run_sync"
    assert by_name["powerplan"].value == "powerplan.server:run_sync"
    assert by_name["powerplan-mcp"].load() is run_sync


def test_list_tools_exposes_agent_entrypoints():
    tools = asyncio.run(list_tools())
    names = {t.name for t in tools}
    assert "get_current_iteration" in names
    assert "get_iteration" in names
    assert "create_plan" in names
    assert "create_iteration" in names
    assert "add_tasks" in names


def test_server_json_registry_manifest():
    data = json.loads((Path(__file__).resolve().parents[1] / "server.json").read_text(encoding="utf-8"))
    assert data["name"] == "io.github.CynaCons/powerplan"
    pkg = data["packages"][0]
    assert pkg["registryType"] == "pypi"
    assert pkg["identifier"] == "powerplan-mcp"
    assert pkg["version"] == __version__
    assert pkg["transport"]["type"] == "stdio"
    assert data["version"] == __version__


def test_readme_contains_mcp_name_proof():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    assert "mcp-name: io.github.CynaCons/powerplan" in readme
