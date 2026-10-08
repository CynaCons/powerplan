"""Every MCP client gets the turn-end rule at initialize (v0.9.0)."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys

from powerplan.server import INSTRUCTIONS, list_tools


def test_instructions_carry_the_turn_end_rule():
    assert "show_current_iteration" in INSTRUCTIONS
    assert "end of every major turn" in INSTRUCTIONS
    assert "verbatim" in INSTRUCTIONS
    assert "show_miniplan" in INSTRUCTIONS  # session start


def test_show_current_iteration_description_repeats_the_rule():
    tools = {t.name: t for t in asyncio.run(list_tools())}
    desc = tools["show_current_iteration"].description
    assert "end of every major turn" in desc and "verbatim" in desc


def test_initialize_over_stdio_returns_instructions():
    p = subprocess.Popen([sys.executable, "-m", "powerplan"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8")
    try:
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"}}}) + "\n")
        p.stdin.flush()
        result = json.loads(p.stdout.readline())["result"]
        assert result["serverInfo"]["name"] == "powerplan"
        assert result["instructions"] == INSTRUCTIONS
    finally:
        p.stdin.close()
        p.wait(timeout=10)
