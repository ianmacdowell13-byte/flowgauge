"""Report builders (the non-conversion ones) with a fake client — field choices,
date-window defaults, cardinality caps, and summaries."""
from __future__ import annotations

from flowgauge import reports
from flowgauge.config import FlowGaugeConfig, ReportDefaults
from flowgauge.schemas import Row
from helpers import FakeReportClient


def _cfg(**kw) -> FlowGaugeConfig:
    return FlowGaugeConfig(property_id="1", report_defaults=ReportDefaults(**kw))


def test_traffic_overview_sums_sessions_and_states_window():
    rows = [Row(dimensions={"date": "20260601"}, metrics={"sessions": 10.0}),
            Row(dimensions={"date": "20260602"}, metrics={"sessions": 5.0})]
    client = FakeReportClient(rows=rows)
    res = reports.traffic_overview(client, _cfg(), None, None)

    assert "15 sessions" in res.summary
    assert res.date_range == "28daysAgo..today"          # lookback default applied
    assert client.calls[0]["dimensions"] == ["date"]
    assert "engagementRate" in client.calls[0]["metrics"]


def test_explicit_dates_override_the_lookback_default():
    client = FakeReportClient(rows=[])
    reports.traffic_overview(client, _cfg(lookback_days=7), "2026-05-01", "2026-05-31")
    assert client.calls[0]["start"] == "2026-05-01"
    assert client.calls[0]["end"] == "2026-05-31"


def test_acquisition_breakdown_picks_dimension_and_honors_cap():
    client = FakeReportClient(rows=[Row(dimensions={"sessionSourceMedium": "ig / social"},
                                        metrics={"sessions": 9.0})])
    res = reports.acquisition(client, _cfg(cardinality_cap=12), breakdown="source_medium")
    assert client.calls[0]["dimensions"] == ["sessionSourceMedium"]
    assert client.calls[0]["limit"] == 12
    assert client.calls[0]["order_by_metric"] == "sessions"
    assert "ig / social" in res.summary


def test_acquisition_unknown_breakdown_falls_back_to_channel():
    client = FakeReportClient(rows=[])
    reports.acquisition(client, _cfg(), breakdown="nonsense")
    assert client.calls[0]["dimensions"] == ["sessionDefaultChannelGroup"]


def test_landing_pages_uses_landing_page_dim_and_leak_hint():
    client = FakeReportClient(rows=[Row(dimensions={"landingPage": "/"}, metrics={"sessions": 3.0})])
    res = reports.landing_pages(client, _cfg())
    assert client.calls[0]["dimensions"] == ["landingPage"]
    assert "bounceRate" in client.calls[0]["metrics"]
    assert "leak" in res.summary.lower()


def test_page_engagement_orders_by_views():
    client = FakeReportClient(rows=[])
    reports.page_engagement(client, _cfg())
    assert client.calls[0]["dimensions"] == ["pagePath"]
    assert client.calls[0]["order_by_metric"] == "screenPageViews"


def test_conversions_with_no_config_returns_helpful_summary():
    client = FakeReportClient(rows=[])
    res = reports.conversions(client, _cfg())  # cfg has no conversions
    assert "No conversions configured" in res.summary
    assert res.rows == []
    assert client.calls == []  # short-circuits before any query
