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


CONV_CHANNEL_DIM = "sessionDefaultChannelGroup"


def _match_to_query(match) -> tuple[str, dict[str, str], dict[str, str]] | None:
    """Map a ConversionMatch to (metric, exact_filters, contains_filters), or
    None if unusable.

    - key_event: true        -> ("keyEvents", {}, {})  — all key events.
    - event_name (+ params)  -> ("eventCount", {eventName=…, customEvent:<p>=…},
                                  {customEvent:<p>=… for substring matches})
    Event params are queried as event-scoped custom dimensions, so each param
    must be registered as a custom dimension in GA4 (else the API rejects it).
    """
    if match.key_event:
        return "keyEvents", {}, {}
    if match.event_name:
        exact = {"eventName": match.event_name}
        exact.update({f"customEvent:{k}": v for k, v in match.params.items()})
        contains = {f"customEvent:{k}": v for k, v in match.params_contains.items()}
        return "eventCount", exact, contains
    return None


def conversions(client: GA4Client, cfg: FlowGaugeConfig, start=None, end=None) -> ReportResult:
    """Count each config-defined conversion per channel.

    Every ``Conversion.match`` becomes its own GA4 query (see ``_match_to_query``);
    result rows are tagged ``{conversion, channel} -> {count}`` so store vs.
    Patreon vs. key-event success is finally separable. A single bad conversion
    (e.g. an unregistered custom dimension) is reported in ``notes`` instead of
    sinking the whole report.
    """
    s, e = _range(cfg, start, end)
    cap = cfg.report_defaults.cardinality_cap

    if not cfg.conversions:
        return ReportResult(
            summary="No conversions configured — add some under `conversions:` in your config.",
            date_range=f"{s}..{e}", rows=[], sampled=False,
        )

    all_rows: list[Row] = []
    notes: list[str] = []
    totals: dict[str, int] = {}
    sampled_any = False

    for conv in cfg.conversions:
        query = _match_to_query(conv.match)
        if query is None:
            notes.append(f"{conv.name}: match needs key_event or event_name — skipped.")
            totals[conv.name] = 0
            continue
        metric, exact_filters, contains_filters = query

        try:
            rows, sampled = client.run_report(
                [CONV_CHANNEL_DIM], [metric], s, e,
                order_by_metric=metric, limit=cap,
                dim_filters=exact_filters, dim_contains=contains_filters,
            )
        except Exception as exc:  # noqa: BLE001 — isolate per-conversion failures
            notes.append(
                f"{conv.name}: query failed ({type(exc).__name__}). If it filters event "
                f"params, register them as event-scoped custom dimensions in GA4."
            )
            totals[conv.name] = 0
            continue

        sampled_any = sampled_any or sampled
        conv_total = 0
        for r in rows:
            count = r.metrics.get(metric, 0.0)
            all_rows.append(Row(
                dimensions={"conversion": conv.name,
                            "channel": r.dimensions.get(CONV_CHANNEL_DIM, "(unknown)")},
                metrics={"count": count},
            ))
            conv_total += int(count)
        totals[conv.name] = conv_total

    leader = max(totals, key=lambda n: totals[n]) if any(totals.values()) else "none yet"
    breakdown = ", ".join(f"{c.name}: {totals.get(c.name, 0)}" for c in cfg.conversions)
    return ReportResult(
        summary=f"Conversions by channel — {breakdown}. Top: {leader}.",
        date_range=f"{s}..{e}", rows=all_rows, sampled=sampled_any, notes=notes,
    )


# Ratio/average metrics can't be summed when merging rows — recombine each as a
# weighted average by its base metric (sessions).
_WEIGHTED_BY = {
    "engagementRate": "sessions",
    "bounceRate": "sessions",
    "averageSessionDuration": "sessions",
}


def _merge_rows_by_dim(rows: list[Row], dim: str) -> list[Row]:
    """Combine rows sharing the same ``dim`` value (first-seen order preserved).

    Additive metrics are summed; ratio/average metrics are recombined as a
    weighted average by their base metric. A value that appears only once passes
    through unchanged.
    """
    order: list[str] = []
    groups: dict[str, list[Row]] = {}
    for r in rows:
        key = r.dimensions.get(dim, "")
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(r)

    merged: list[Row] = []
    for key in order:
        bucket = groups[key]
        if len(bucket) == 1:
            merged.append(bucket[0])
            continue
        metrics: dict[str, float] = {}
        for m in {name for row in bucket for name in row.metrics}:
            weight = _WEIGHTED_BY.get(m)
            if weight:
                den = sum(row.metrics.get(weight, 0.0) for row in bucket)
                if den:
                    metrics[m] = sum(row.metrics.get(m, 0.0) * row.metrics.get(weight, 0.0)
                                     for row in bucket) / den
                else:  # no weights to go on — fall back to a plain mean
                    vals = [row.metrics.get(m, 0.0) for row in bucket]
                    metrics[m] = sum(vals) / len(vals)
            else:
                metrics[m] = sum(row.metrics.get(m, 0.0) for row in bucket)
        merged.append(Row(dimensions={**bucket[0].dimensions, dim: key}, metrics=metrics))
    return merged


def _apply_channel_overrides(rows: list[Row], dim: str, cfg: FlowGaugeConfig) -> list[Row]:
    """Relabel rows matching a custom channel rule, then merge the collapsed
    duplicates so each custom channel is a single, correctly-aggregated row."""
    if not cfg.channels:
        return rows
    for r in rows:
        val = (r.dimensions.get(dim) or "").lower()
        for label, rule in cfg.channels.items():
            if any(tok.lower() in val for tok in rule.source_contains):
                r.dimensions[dim] = label
                break
    merged = _merge_rows_by_dim(rows, dim)
    merged.sort(key=lambda r: r.metrics.get("sessions", 0.0), reverse=True)
    return merged
