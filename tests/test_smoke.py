"""Smoke tests — no live GA4 calls. CI runs these against fixtures only."""
from __future__ import annotations

from pathlib import Path

from flowgauge import __version__
from flowgauge.config import FlowGaugeConfig, load_config


def test_version():
    assert __version__


def test_example_config_loads():
    example = Path(__file__).resolve().parents[1] / "config" / "flowgauge.config.example.yaml"
    cfg = load_config(str(example))
    assert isinstance(cfg, FlowGaugeConfig)
    assert cfg.ga_property.startswith("properties/")
    # The example declares at least one conversion (the generalization layer).
    assert cfg.conversions, "example config should define conversions"


def test_channel_override_relabels_rows():
    from flowgauge.config import ChannelRule, FlowGaugeConfig
    from flowgauge.reports import _apply_channel_overrides
    from flowgauge.schemas import Row

    cfg = FlowGaugeConfig(
        property_id="1",
        channels={"Social-Short-Form": ChannelRule(source_contains=["tiktok"])},
    )
    rows = [Row(dimensions={"sessionSourceMedium": "tiktok / referral"}, metrics={"sessions": 10})]
    out = _apply_channel_overrides(rows, "sessionSourceMedium", cfg)
    assert out[0].dimensions["sessionSourceMedium"] == "Social-Short-Form"


def test_channel_override_merges_duplicate_relabels():
    """Multiple sources collapsing to one custom channel must merge into a single
    row — additive metrics summed, ratios weighted by sessions (the old bug left
    duplicate rows)."""
    from flowgauge.config import ChannelRule, FlowGaugeConfig
    from flowgauge.reports import _apply_channel_overrides
    from flowgauge.schemas import Row

    cfg = FlowGaugeConfig(
        property_id="1",
        channels={"Social-Short-Form": ChannelRule(source_contains=["tiktok", "ig"])},
    )
    rows = [
        Row(dimensions={"sessionSourceMedium": "tiktok / referral"},
            metrics={"sessions": 10.0, "keyEvents": 4.0, "engagementRate": 0.6}),
        Row(dimensions={"sessionSourceMedium": "ig / social"},
            metrics={"sessions": 30.0, "keyEvents": 6.0, "engagementRate": 0.8}),
        Row(dimensions={"sessionSourceMedium": "google / organic"},
            metrics={"sessions": 5.0, "keyEvents": 1.0, "engagementRate": 0.5}),
    ]
    out = _apply_channel_overrides(rows, "sessionSourceMedium", cfg)
    labels = [r.dimensions["sessionSourceMedium"] for r in out]

    assert labels.count("Social-Short-Form") == 1          # merged, not duplicated
    assert labels[0] == "Social-Short-Form"                # sorted by sessions desc
    ssf = next(r for r in out if r.dimensions["sessionSourceMedium"] == "Social-Short-Form")
    assert ssf.metrics["sessions"] == 40.0                 # 10 + 30
    assert ssf.metrics["keyEvents"] == 10.0                # 4 + 6
    assert abs(ssf.metrics["engagementRate"] - 0.75) < 1e-9  # (0.6*10 + 0.8*30) / 40


# --- conversions: per-conversion breakdown -------------------------------------

class _FakeClient:
    """Stand-in for GA4Client: returns canned rows and records each call."""

    def __init__(self, handler):
        self._handler = handler
        self.calls: list[dict] = []

    def run_report(self, dimensions, metrics, start_date, end_date,
                   order_by_metric=None, limit=50, dim_filters=None, dim_contains=None):
        self.calls.append({"metrics": metrics,
                           "dim_filters": dim_filters or {},
                           "dim_contains": dim_contains or {}})
        return self._handler(metrics[0], dim_filters or {}, dim_contains or {})


def _conv_cfg():
    """Inline config so these tests don't depend on the example file's values."""
    from flowgauge.config import Conversion, ConversionMatch, FlowGaugeConfig
    return FlowGaugeConfig(
        property_id="1",
        conversions=[
            Conversion(name="store_clickout", match=ConversionMatch(
                event_name="click", params_contains={"link_domain": "fourthwall"})),
            Conversion(name="patreon_clickout", match=ConversionMatch(
                event_name="click", params_contains={"link_domain": "patreon.com"})),
            Conversion(name="key_event", match=ConversionMatch(key_event=True)),
        ],
    )


def test_conversions_splits_by_named_conversion():
    from flowgauge import reports
    from flowgauge.schemas import Row

    def handler(metric, exact, contains):
        if metric == "eventCount" and contains.get("customEvent:link_domain") == "patreon.com":
            return ([Row(dimensions={"sessionDefaultChannelGroup": "Organic Social"},
                         metrics={"eventCount": 40.0}),
                     Row(dimensions={"sessionDefaultChannelGroup": "Direct"},
                         metrics={"eventCount": 10.0})], False)
        if metric == "eventCount":           # store_clickout -> fourthwall: no hits
            return ([], False)
        if metric == "keyEvents":            # key_event match: all key events
            return ([Row(dimensions={"sessionDefaultChannelGroup": "Organic Search"},
                         metrics={"keyEvents": 290.0})], False)
        return ([], False)

    client = _FakeClient(handler)
    result = reports.conversions(client, _conv_cfg())

    # eventName is an exact filter; link_domain is a substring (contains) filter.
    exact_sent = [c["dim_filters"] for c in client.calls]
    contains_sent = [c["dim_contains"] for c in client.calls]
    assert {"eventName": "click"} in exact_sent
    assert {"customEvent:link_domain": "fourthwall"} in contains_sent
    assert {"customEvent:link_domain": "patreon.com"} in contains_sent
    assert {} in exact_sent and {} in contains_sent  # key_event: no filters

    by_conv: dict[str, int] = {}
    for r in result.rows:
        by_conv[r.dimensions["conversion"]] = by_conv.get(r.dimensions["conversion"], 0) + int(r.metrics["count"])
    assert by_conv.get("patreon_clickout") == 50
    assert by_conv.get("key_event") == 290
    assert "store_clickout" not in by_conv          # zero hits -> no rows
    assert "patreon_clickout: 50" in result.summary
    assert "Top: key_event" in result.summary
    assert result.notes == []


def test_conversions_isolates_a_failing_conversion():
    from flowgauge import reports
    from flowgauge.schemas import Row

    def handler(metric, exact, contains):
        if contains.get("customEvent:link_domain") == "fourthwall":
            raise RuntimeError("link_domain not registered as a custom dimension")
        if metric == "keyEvents":
            return ([Row(dimensions={"sessionDefaultChannelGroup": "Direct"},
                         metrics={"keyEvents": 12.0})], False)
        return ([], False)

    result = reports.conversions(_FakeClient(handler), _conv_cfg())

    assert any("store_clickout" in n for n in result.notes)
    assert any(r.dimensions["conversion"] == "key_event" for r in result.rows)


def test_dimension_filter_exact_and_contains():
    from google.analytics.data_v1beta.types import Filter

    from flowgauge.ga4_client import _build_dimension_filter

    assert _build_dimension_filter({}, {}) is None

    one = _build_dimension_filter({"eventName": "click"}, {})
    assert one.filter.field_name == "eventName"
    assert one.filter.string_filter.value == "click"

    both = _build_dimension_filter({"eventName": "click"},
                                   {"customEvent:link_domain": "patreon.com"})
    assert len(both.and_group.expressions) == 2
    contains_clause = both.and_group.expressions[1].filter.string_filter
    assert contains_clause.value == "patreon.com"
    assert contains_clause.match_type == Filter.StringFilter.MatchType.CONTAINS
