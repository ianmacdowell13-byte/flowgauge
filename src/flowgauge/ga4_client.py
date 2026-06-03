"""Thin wrapper over the GA4 Data API (properties.runReport).

Auth uses Application Default Credentials — set GOOGLE_APPLICATION_CREDENTIALS
to the service-account key path. The service account needs Viewer on the
GA4 property. Scope: https://www.googleapis.com/auth/analytics.readonly
"""
from __future__ import annotations

from .schemas import Row


class GA4Client:
    def __init__(self, ga_property: str) -> None:
        self.ga_property = ga_property
        self._client = None  # lazily created

    def _data_client(self):
        if self._client is None:
            # Imported lazily so the package imports without creds present.
            from google.analytics.data_v1beta import BetaAnalyticsDataClient

            self._client = BetaAnalyticsDataClient()
        return self._client

    def run_report(
        self,
        dimensions: list[str],
        metrics: list[str],
        start_date: str,
        end_date: str,
        order_by_metric: str | None = None,
        limit: int = 50,
    ) -> tuple[list[Row], bool]:
        """Run a GA4 report. Returns (rows, sampled)."""
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            MetricType,
            OrderBy,
            RunReportRequest,
        )

        req = RunReportRequest(
            property=self.ga_property,
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit,
        )
        if order_by_metric:
            req.order_bys = [
                OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=True)
            ]

        resp = self._data_client().run_report(req)

        dim_headers = [h.name for h in resp.dimension_headers]
        met_headers = [h.name for h in resp.metric_headers]
        rows: list[Row] = []
        for r in resp.rows:
            dims = {dim_headers[i]: v.value for i, v in enumerate(r.dimension_values)}
            mets = {met_headers[i]: _to_float(v.value) for i, v in enumerate(r.metric_values)}
            rows.append(Row(dimensions=dims, metrics=mets))

        sampled = any(getattr(md, "samplingMetadatas", None) for md in resp.metadata.__dict__.values()) \
            if resp.metadata else False
        return rows, bool(sampled)


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
