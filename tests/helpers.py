"""Shared, importable test helpers. No live GA4 calls anywhere in the suite.

Imported as ``from helpers import ...`` — pytest puts the ``tests/`` directory on
``sys.path`` (default prepend import mode), so this resolves without packaging.
"""
from __future__ import annotations

from types import SimpleNamespace

from flowgauge.schemas import Row


class FakeReportClient:
    """Stand-in for GA4Client that returns canned ``(rows, sampled)`` and records calls.

    Pass a ``handler(dimensions, metrics, start, end, **kw) -> (rows, sampled)``,
    or ``rows=`` for a one-shot fixed response.
    """

    def __init__(self, handler=None, rows=None, sampled=False):
        if handler is None:
            handler = lambda *a, **k: (rows or [], sampled)  # noqa: E731
        self._handler = handler
        self.calls: list[dict] = []

    def run_report(self, dimensions, metrics, start_date, end_date,
                   order_by_metric=None, limit=50, dim_filters=None, dim_contains=None):
        self.calls.append({
            "dimensions": dimensions, "metrics": metrics,
            "start": start_date, "end": end_date,
            "order_by_metric": order_by_metric, "limit": limit,
            "dim_filters": dim_filters or {}, "dim_contains": dim_contains or {},
        })
        return self._handler(dimensions, metrics, start_date, end_date,
                             order_by_metric=order_by_metric, limit=limit,
                             dim_filters=dim_filters, dim_contains=dim_contains)


def ga4_response(dim_headers, met_headers, rows, sampled=False):
    """Build a minimal duck-typed GA4 runReport response for GA4Client parsing."""
    H = lambda name: SimpleNamespace(name=name)          # noqa: E731
    V = lambda value: SimpleNamespace(value=value)        # noqa: E731
    resp_rows = [
        SimpleNamespace(
            dimension_values=[V(v) for v in r[0]],
            metric_values=[V(v) for v in r[1]],
        )
        for r in rows
    ]
    return SimpleNamespace(
        dimension_headers=[H(h) for h in dim_headers],
        metric_headers=[H(h) for h in met_headers],
        rows=resp_rows,
        metadata=SimpleNamespace(sampling_metadatas=[1] if sampled else []),
    )


def make_row(dims: dict, mets: dict) -> Row:
    return Row(dimensions=dims, metrics=mets)
