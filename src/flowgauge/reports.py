"""Opinionated report builders.

These map the three creator questions to concrete GA4 dimension/metric sets,
using the canonical field names (see docs/SPEC.md Appendix B). The *opinion*
lives here and in the traffic-health skill; ga4_client stays generic.
"""
from __future__ import annotations

from .config import FlowGaugeConfig
from .ga4_client import GA4Client
from .schemas import ReportResult, Row

# Canonical GA4 Data API field names (pin against the Metadata API in tests).
TRAFFIC_METRICS = ["sessions", "totalUsers", "newUsers", "engagementRate", "averageSessionDuration"]
ACQ_DIMENSIONS = {
    "channel": "sessionDefaultChannelGroup",
    "source_medium": "sessionSourceMedium",
    "campaign": "sessionCampaignName",
}


def _range(cfg: FlowGaugeConfig, start: str | None, end: str | None) -> tuple[str, str]:
    return (start or f"{cfg.report_defaults.lookback_days}daysAgo", end or "today")


def traffic_overview(client: GA4Client, cfg: FlowGaugeConfig, start=None, end=None) -> ReportResult:
    s, e = _range(cfg, start, end)
    rows, sampled = client.run_report(["date"], TRAFFIC_METRICS, s, e, limit=400)
    total = sum(r.metrics.get("sessions", 0) for r in rows)
    return ReportResult(
        summary=f"{int(total)} sessions from {s} to {e} across {len(rows)} days.",
        date_range=f"{s}..{e}", rows=rows, sampled=sampled,
    )


def acquisition(client: GA4Client, cfg: FlowGaugeConfig, breakdown="channel", start=None, end=None) -> ReportResult:
    s, e = _range(cfg, start, end)
    dim = ACQ_DIMENSIONS.get(breakdown, ACQ_DIMENSIONS["channel"])
    metrics = ["sessions", "totalUsers", "engagementRate", "keyEvents"]
    rows, sampled = client.run_report([dim], metrics, s, e, order_by_metric="sessions",
                                      limit=cfg.report_defaults.cardinality_cap)
    rows = _apply_channel_overrides(rows, dim, cfg)
    top = rows[0].dimensions.get(dim) if rows else "n/a"
    return ReportResult(
        summary=f"Top {breakdown} by sessions: {top}.",
        date_range=f"{s}..{e}", rows=rows, sampled=sampled,
    )


def landing_pages(client: GA4Client, cfg: FlowGaugeConfig, start=None, end=None) -> ReportResult:
    s, e = _range(cfg, start, end)
    metrics = ["sessions", "engagementRate", "bounceRate", "keyEvents"]
    rows, sampled = client.run_report(["landingPage"], metrics, s, e, order_by_metric="sessions",
                                      limit=cfg.report_defaults.cardinality_cap)
    return ReportResult(
        summary=f"{len(rows)} landing pages. Watch high-session / low-engagement rows for leaks.",
        date_range=f"{s}..{e}", rows=rows, sampled=sampled,
    )


def page_engagement(client: GA4Client, cfg: FlowGaugeConfig, start=None, end=None) -> ReportResult:
    s, e = _range(cfg, start, end)
    metrics = ["screenPageViews", "userEngagementDuration", "eventCount"]
    rows, sampled = client.run_report(["pagePath"], metrics, s, e, order_by_metric="screenPageViews",
                                      limit=cfg.report_defaults.cardinality_cap)
    return ReportResult(summary=f"{len(rows)} pages by views.", date_range=f"{s}..{e}",
                        rows=rows, sampled=sampled)


def conversions(client: GA4Client, cfg: FlowGaugeConfig, start=None, end=None) -> ReportResult:
    """Resolve config-defined conversions to event counts, by channel.

    TODO(v0.1): translate each Conversion.match into a GA4 FilterExpression on
    eventName + event params (or isKeyEvent) and aggregate per channel.
    """
    s, e = _range(cfg, start, end)
    names = [c.name for c in cfg.conversions] or ["(none configured)"]
    rows, sampled = client.run_report(["sessionDefaultChannelGroup"], ["keyEvents", "sessions"], s, e,
                                      order_by_metric="keyEvents", limit=cfg.report_defaults.cardinality_cap)
    return ReportResult(
        summary=f"Conversions tracked: {', '.join(names)} (channel breakdown shown).",
        date_range=f"{s}..{e}", rows=rows, sampled=sampled,
        notes=["TODO: per-conversion event filtering — see reports.conversions()"],
    )


def _apply_channel_overrides(rows: list[Row], dim: str, cfg: FlowGaugeConfig) -> list[Row]:
    """Relabel rows whose source matches a custom channel rule from config."""
    if not cfg.channels:
        return rows
    for r in rows:
        val = (r.dimensions.get(dim) or "").lower()
        for label, rule in cfg.channels.items():
            if any(tok.lower() in val for tok in rule.source_contains):
                r.dimensions[dim] = label
                break
    return rows
