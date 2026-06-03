"""Config loading, env resolution, and property-name normalization."""
from __future__ import annotations

from pathlib import Path

import pytest

from flowgauge.config import FlowGaugeConfig, load_config


def test_ga_property_normalizes_bare_id():
    assert FlowGaugeConfig(property_id="123456789").ga_property == "properties/123456789"


def test_ga_property_passes_through_full_resource_name():
    assert FlowGaugeConfig(property_id="properties/42").ga_property == "properties/42"


def test_defaults_are_sane():
    cfg = FlowGaugeConfig(property_id="1")
    assert cfg.report_defaults.lookback_days == 28
    assert cfg.report_defaults.cardinality_cap == 50
    assert cfg.bigquery.enabled is False
    assert cfg.conversions == [] and cfg.channels == {}


def test_load_config_explicit_path(tmp_path: Path):
    p = tmp_path / "c.yaml"
    p.write_text("property_id: '999'\nbrand_domains: [example.com]\n")
    cfg = load_config(str(p))
    assert cfg.ga_property == "properties/999"
    assert cfg.brand_domains == ["example.com"]


def test_load_config_falls_back_to_env(tmp_path: Path, monkeypatch):
    p = tmp_path / "env.yaml"
    p.write_text("property_id: '7'\n")
    monkeypatch.setenv("FLOWGAUGE_CONFIG", str(p))
    cfg = load_config()  # no explicit path -> reads $FLOWGAUGE_CONFIG
    assert cfg.property_id == "7"


def test_load_config_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "nope.yaml"))
