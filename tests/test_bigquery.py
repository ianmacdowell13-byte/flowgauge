"""BigQuery backend: the disabled-by-default guard and the v0.3 stubs."""
from __future__ import annotations

import pytest

from flowgauge import bigquery
from flowgauge.config import BigQueryConfig, FlowGaugeConfig


def _cfg(**bq) -> FlowGaugeConfig:
    return FlowGaugeConfig(property_id="1", bigquery=BigQueryConfig(**bq))


def test_disabled_by_default_raises_with_guidance():
    with pytest.raises(bigquery.BigQueryDisabled) as exc:
        bigquery.flow_paths(_cfg(), "28daysAgo", "today")
    assert "BigQuery is not configured" in str(exc.value)


def test_enabled_but_missing_project_or_dataset_still_raises():
    with pytest.raises(bigquery.BigQueryDisabled):
        bigquery.funnel(_cfg(enabled=True), ["a", "b"], "28daysAgo", "today")
    with pytest.raises(bigquery.BigQueryDisabled):
        bigquery.funnel(_cfg(enabled=True, project="p"), ["a", "b"], "28daysAgo", "today")


def test_fully_configured_reaches_the_not_implemented_stub():
    cfg = _cfg(enabled=True, project="p", dataset="analytics_1")
    # Passes the _require guard, then hits the v0.3 stub.
    with pytest.raises(NotImplementedError):
        bigquery.flow_paths(cfg, "28daysAgo", "today")
    with pytest.raises(NotImplementedError):
        bigquery.funnel(cfg, ["home", "checkout"], "28daysAgo", "today")
