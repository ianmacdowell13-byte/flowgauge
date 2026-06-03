"""GA4Client.run_report: response parsing, sampling detection, and request wiring.

No network: we inject a fake low-level data client and capture the built request.
"""
from __future__ import annotations

from flowgauge.ga4_client import GA4Client
from helpers import ga4_response


class _CapturingDataClient:
    def __init__(self, response):
        self._response = response
        self.request = None

    def run_report(self, req):
        self.request = req
        return self._response


def _client_with(response) -> tuple[GA4Client, _CapturingDataClient]:
    client = GA4Client("properties/123")
    fake = _CapturingDataClient(response)
    client._client = fake  # bypass lazy BetaAnalyticsDataClient construction
    return client, fake


def test_parses_rows_into_dim_and_metric_maps():
    resp = ga4_response(
        dim_headers=["date"],
        met_headers=["sessions", "totalUsers"],
        rows=[(["20260601"], ["12", "9"]), (["20260602"], ["3", "3"])],
    )
    client, _ = _client_with(resp)
    rows, sampled = client.run_report(["date"], ["sessions", "totalUsers"], "28daysAgo", "today")

    assert sampled is False
    assert [r.dimensions["date"] for r in rows] == ["20260601", "20260602"]
    assert rows[0].metrics == {"sessions": 12.0, "totalUsers": 9.0}


def test_non_numeric_metric_coerces_to_zero():
    resp = ga4_response(["channel"], ["sessions"], [(["Direct"], ["(other)"])])
    client, _ = _client_with(resp)
    rows, _ = client.run_report(["channel"], ["sessions"], "7daysAgo", "today")
    assert rows[0].metrics["sessions"] == 0.0


def test_sampling_metadata_sets_the_flag():
    resp = ga4_response(["date"], ["sessions"], [(["20260601"], ["1"])], sampled=True)
    client, _ = _client_with(resp)
    _, sampled = client.run_report(["date"], ["sessions"], "7daysAgo", "today")
    assert sampled is True


def test_request_carries_property_limit_order_and_filters():
    resp = ga4_response(["channel"], ["eventCount"], [])
    client, fake = _client_with(resp)
    client.run_report(
        ["sessionDefaultChannelGroup"], ["eventCount"], "28daysAgo", "today",
        order_by_metric="eventCount", limit=25,
        dim_filters={"eventName": "click"},
        dim_contains={"customEvent:link_domain": "patreon.com"},
    )
    req = fake.request
    assert req.property == "properties/123"
    assert req.limit == 25
    assert req.metrics[0].name == "eventCount"
    assert req.order_bys[0].metric.metric_name == "eventCount"
    assert req.order_bys[0].desc is True
    # exact + contains became an AND group of two clauses
    assert len(req.dimension_filter.and_group.expressions) == 2


def test_no_filters_leaves_request_filter_unset():
    resp = ga4_response(["date"], ["sessions"], [])
    client, fake = _client_with(resp)
    client.run_report(["date"], ["sessions"], "7daysAgo", "today")
    # No dimension_filter was assigned (proto default is an empty message).
    assert not fake.request.dimension_filter.filter.field_name
