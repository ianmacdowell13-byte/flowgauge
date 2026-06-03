"""Output schema models: defaults, validation, and the public dump shape."""
from __future__ import annotations

from flowgauge.schemas import ReportResult, Row


def test_row_defaults_to_empty_maps():
    r = Row()
    assert r.dimensions == {}
    assert r.metrics == {}


def test_report_result_required_and_optional_fields():
    res = ReportResult(summary="s", date_range="a..b")
    assert res.compare_range is None
    assert res.rows == []
    assert res.sampled is False
    assert res.notes == []


def test_model_dump_is_json_safe_and_stable():
    res = ReportResult(
        summary="2 sessions",
        date_range="28daysAgo..today",
        rows=[Row(dimensions={"channel": "Direct"}, metrics={"sessions": 2.0})],
        sampled=True,
        notes=["heads up"],
    )
    dumped = res.model_dump()
    assert dumped == {
        "summary": "2 sessions",
        "date_range": "28daysAgo..today",
        "compare_range": None,
        "rows": [{"dimensions": {"channel": "Direct"}, "metrics": {"sessions": 2.0}}],
        "sampled": True,
        "notes": ["heads up"],
    }


def test_metrics_coerce_to_float():
    # pydantic coerces ints to float for the metrics map.
    r = Row(dimensions={"d": "x"}, metrics={"sessions": 5})
    assert isinstance(r.metrics["sessions"], float)
    assert r.metrics["sessions"] == 5.0
