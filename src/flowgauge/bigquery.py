"""Optional BigQuery backend for TRUE UX flow (session paths + funnels).

The GA4 Data API cannot return ordered session paths or funnels; only the
free GA4 -> BigQuery event export can. These functions are no-ops unless
`bigquery.enabled` is set in config.

All queries MUST aggregate — never return user_pseudo_id rows to the model.
"""
from __future__ import annotations

from .config import FlowGaugeConfig
from .schemas import ReportResult


class BigQueryDisabled(RuntimeError):
    pass


def _require(cfg: FlowGaugeConfig):
    if not cfg.bigquery.enabled or not (cfg.bigquery.project and cfg.bigquery.dataset):
        raise BigQueryDisabled(
            "BigQuery is not configured. Enable the GA4 -> BigQuery export and set "
            "bigquery.{enabled,project,dataset} in flowgauge.config.yaml."
        )


def flow_paths(cfg: FlowGaugeConfig, start: str, end: str, from_page: str | None = None) -> ReportResult:
    """Most common ordered page sequences within sessions.

    TODO(v0.3): build the SQL over `events_*` — unnest event_params, order by
    event_timestamp per (user_pseudo_id, ga_session_id), then aggregate the
    top N path strings. Optionally anchor on `from_page`.
    """
    _require(cfg)
    raise NotImplementedError("flow_paths lands in v0.3")


def funnel(cfg: FlowGaugeConfig, steps: list[str], start: str, end: str) -> ReportResult:
    """Step-by-step conversion + drop-off for a declared funnel.

    TODO(v0.3): conditional aggregation across declared steps from the export.
    """
    _require(cfg)
    raise NotImplementedError("funnel lands in v0.3")
