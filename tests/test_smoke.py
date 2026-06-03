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
