"""Configuration loading and models.

All site-specific behavior is expressed here (loaded from flowgauge.config.yaml),
so the rest of the code stays generic.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ConversionMatch(BaseModel):
    """Predicate that maps a GA4 event to a named, site-defined conversion."""
    event_name: str | None = None
    params: dict[str, str] = Field(default_factory=dict)
    key_event: bool | None = None


class Conversion(BaseModel):
    name: str
    match: ConversionMatch


class ChannelRule(BaseModel):
    source_contains: list[str] = Field(default_factory=list)


class ReportDefaults(BaseModel):
    lookback_days: int = 28
    compare: str = "previous_period"  # previous_period | previous_year | none
    cardinality_cap: int = 50
    currency: str = "USD"


class BigQueryConfig(BaseModel):
    enabled: bool = False
    project: str | None = None
    dataset: str | None = None


class FlowGaugeConfig(BaseModel):
    property_id: str
    timezone: str = "UTC"
    brand_domains: list[str] = Field(default_factory=list)
    conversions: list[Conversion] = Field(default_factory=list)
    channels: dict[str, ChannelRule] = Field(default_factory=dict)
    report_defaults: ReportDefaults = Field(default_factory=ReportDefaults)
    bigquery: BigQueryConfig = Field(default_factory=BigQueryConfig)

    @property
    def ga_property(self) -> str:
        """Return the API resource name, e.g. 'properties/123456789'."""
        pid = str(self.property_id)
        return pid if pid.startswith("properties/") else f"properties/{pid}"


def load_config(path: str | None = None) -> FlowGaugeConfig:
    """Load config from the given path, or $FLOWGAUGE_CONFIG, or ./flowgauge.config.yaml."""
    cfg_path = path or os.environ.get("FLOWGAUGE_CONFIG") or "flowgauge.config.yaml"
    data = yaml.safe_load(Path(cfg_path).read_text())
    return FlowGaugeConfig.model_validate(data)
