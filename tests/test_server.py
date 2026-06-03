"""MCP server: tool registration + that each tool delegates to the report layer."""
from __future__ import annotations

import asyncio

from flowgauge import server
from flowgauge.schemas import ReportResult

EXPECTED_TOOLS = {
    "traffic_overview",
    "acquisition",
    "landing_pages",
    "page_engagement",
    "conversions",
}


def _registered_tool_names() -> list[str]:
    """Read registered tool names across FastMCP versions (sync manager or async)."""
    tm = getattr(server.mcp, "_tool_manager", None)
    if tm is not None and hasattr(tm, "list_tools"):
        return [t.name for t in tm.list_tools()]
    return [t.name for t in asyncio.run(server.mcp.list_tools())]


def test_exactly_the_expected_tools_are_registered():
    names = set(_registered_tool_names())
    assert EXPECTED_TOOLS <= names, f"missing: {EXPECTED_TOOLS - names}"
    # No accidental extras (e.g. a half-wired flow_paths leaking in before v0.3).
    assert names == EXPECTED_TOOLS, f"unexpected: {names - EXPECTED_TOOLS}"


def test_tool_delegates_to_report_and_dumps(monkeypatch):
    sentinel = ReportResult(summary="ok", date_range="a..b", notes=["n"])
    captured = {}

    monkeypatch.setattr(server, "_ctx", lambda: ("CLIENT", "CFG"))

    def fake_report(client, cfg, *args, **kwargs):
        captured["client"] = client
        captured["cfg"] = cfg
        return sentinel

    monkeypatch.setattr(server.reports, "traffic_overview", fake_report)
    out = server.traffic_overview(start="7daysAgo", end="today")

    assert captured == {"client": "CLIENT", "cfg": "CFG"}
    assert out == sentinel.model_dump()
    assert out["summary"] == "ok" and out["notes"] == ["n"]


def test_ctx_is_lazy_and_cached(monkeypatch):
    # _ctx loads config once and reuses the client.
    server._cfg = None
    server._client = None
    loads = {"n": 0}

    class FakeCfg:
        ga_property = "properties/1"

    def fake_load(*a, **k):
        loads["n"] += 1
        return FakeCfg()

    monkeypatch.setattr(server, "load_config", fake_load)
    monkeypatch.setattr(server, "GA4Client", lambda prop: f"client:{prop}")

    c1, cfg1 = server._ctx()
    c2, cfg2 = server._ctx()
    assert c1 == c2 == "client:properties/1"
    assert cfg1 is cfg2
    assert loads["n"] == 1  # loaded once, then cached

    server._cfg = None
    server._client = None
