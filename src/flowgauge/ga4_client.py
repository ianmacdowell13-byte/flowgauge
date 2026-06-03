"""Thin wrapper over the GA4 Data API (properties.runReport).

Auth uses Application Default Credentials via ``google.auth.default()``:

- **Primary:** a user login — ``gcloud auth application-default login`` with the
  ``analytics.readonly`` scope (leave ``GOOGLE_APPLICATION_CREDENTIALS`` unset).
- **Alternative:** a pre-2026 service-account key — set
  ``GOOGLE_APPLICATION_CREDENTIALS`` to its path.

Either way the only permission required is GA4 **Viewer**. See README → Authentication.
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
        dim_filters: dict[str, str] | None = None,
        dim_contains: dict[str, str] | None = None,
    ) -> tuple[list[Row], bool]:
        """Run a GA4 report. Returns (rows, sampled).

        ``dim_filters`` are exact dimension equalities; ``dim_contains`` are
        substring matches. Both map field name -> value and are AND-ed together
        (e.g. exact ``{"eventName": "click"}`` + contains
        ``{"customEvent:link_domain": "patreon.com"}``). Building the
        FilterExpression here keeps callers free of the GA4 SDK types.
        """
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
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
        dimension_filter = _build_dimension_filter(dim_filters or {}, dim_contains or {})
        if dimension_filter is not None:
            req.dimension_filter = dimension_filter
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

        meta = resp.metadata
        sampled = bool(meta and getattr(meta, "sampling_metadatas", None))
        return rows, sampled


def _build_dimension_filter(exact: dict[str, str], contains: dict[str, str]):
    """Build an AND-grouped dimension FilterExpression from exact + substring
    matches. Returns None if both are empty; a bare Filter for a single clause.
    """
    from google.analytics.data_v1beta.types import Filter, FilterExpression, FilterExpressionList

    StringFilter = Filter.StringFilter
    exprs: list = []
    for field, value in exact.items():
        exprs.append(FilterExpression(
            filter=Filter(field_name=field, string_filter=StringFilter(value=value))
        ))
    for field, value in contains.items():
        exprs.append(FilterExpression(
            filter=Filter(field_name=field, string_filter=StringFilter(
                value=value, match_type=StringFilter.MatchType.CONTAINS))
        ))

    if not exprs:
        return None
    if len(exprs) == 1:
        return exprs[0]
    return FilterExpression(and_group=FilterExpressionList(expressions=exprs))


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
