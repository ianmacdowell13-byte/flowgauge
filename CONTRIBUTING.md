# Contributing to FlowGauge

Thanks for helping build opinionated GA4 analytics. A few notes:

## Ground rules
- **Read-only by default.** v1 never writes to GA4. Don't add Admin *write* calls.
- **No PII.** Operate on aggregates. Never return user-level identifiers (e.g. `user_pseudo_id`) to the model. BigQuery queries must aggregate.
- **No secrets in the repo.** Keys/config stay local; only `*.example.yaml` is committed.

## Dev setup
```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev,bigquery]"
.venv/bin/ruff check . && .venv/bin/pytest -q
```

**No live GA4 calls anywhere in the suite.** Tests inject a fake report client or a
duck-typed GA4 response — shared helpers live in [`tests/helpers.py`](tests/helpers.py)
(imported as `from helpers import ...`). Layout:

| File | Covers |
|---|---|
| `test_config.py` | config loading, env resolution, property-name normalization |
| `test_schemas.py` | output models + `model_dump` shape |
| `test_ga4_client_report.py` | `run_report` parsing, sampling, request wiring |
| `test_reports.py` | report builders: dims/metrics, windows, caps, summaries |
| `test_smoke.py` | channel-override merge math + per-conversion breakdown |
| `test_server.py` | MCP tool registration + delegation |
| `test_bigquery.py` | disabled-by-default guard + v0.3 stubs |

## Good first issues
- New **report recipes** in `reports.py` (e.g. device split, new-vs-returning).
- New **conversion matchers** in `config.py` (more `match:` predicates).
- Docs: MCP client config snippets for additional clients.

## PRs
- Keep tool outputs typed (`schemas.py`) and include a one-line `summary`.
- Pin new GA4 fields against the Metadata API and add a fixture.
- Conventional-ish commits appreciated; semantic versioning for releases.
