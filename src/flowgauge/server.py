"""FlowGauge MCP server.

Exposes a small, opinionated set of GA4 tools. Run with `flowgauge`
(stdio transport) and point an MCP client at it. See README.md.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import reports
from .config import FlowGaugeConfig, load_config
from .ga4_client import GA4Client

mcp = FastMCP("flowgauge")

_cfg: FlowGaugeConfig | None = None
_client: GA4Client | None = None


def _ctx() -> tuple[GA4Client, FlowGaugeConfig]:
    global _cfg, _client
    if _cfg is None:
        _cfg = load_config()
        _client = GA4Client(_cfg.ga_property)
    assert _client is not None
    return _client, _cfg


@mcp.tool()
def traffic_overview(start: str | None = None, end: str | None = None) -> dict:
    """Sessions, users, new users, and engagement over time."""
    client, cfg = _ctx()
    return reports.traffic_overview(client, cfg, start, end).model_dump()


@mcp.tool()
def acquisition(breakdown: str = "channel", start: str | None = None, end: str | None = None) -> dict:
    """Where traffic comes from. breakdown = channel | source_medium | campaign."""
    client, cfg = _ctx()
    return reports.acquisition(client, cfg, breakdown, start, end).model_dump()


@mcp.tool()
def landing_pages(start: str | None = None, end: str | None = None) -> dict:
    """Landing pages by sessions, engagement, bounce, and conversions."""
    client, cfg = _ctx()
    return reports.landing_pages(client, cfg, start, end).model_dump()


@mcp.tool()
def page_engagement(start: str | None = None, end: str | None = None) -> dict:
    """Pages by views, engagement time, and event counts."""
    client, cfg = _ctx()
    return reports.page_engagement(client, cfg, start, end).model_dump()


@mcp.tool()
def conversions(start: str | None = None, end: str | None = None) -> dict:
    """Config-defined conversions (e.g. outbound click-outs), broken down by channel."""
    client, cfg = _ctx()
    return reports.conversions(client, cfg, start, end).model_dump()


# TODO(v0.3): register flow_paths / funnel tools when BigQuery backend ships.


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
