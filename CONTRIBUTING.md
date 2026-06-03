# Contributing to FlowGauge

Thanks for helping build opinionated GA4 analytics. A few notes:

## Ground rules
- **Read-only by default.** v1 never writes to GA4. Don't add Admin *write* calls.
- **No PII.** Operate on aggregates. Never return user-level identifiers (e.g. `user_pseudo_id`) to the model. BigQuery queries must aggregate.
- **No secrets in the repo.** Keys/config stay local; only `*.example.yaml` is committed.

## Dev setup
```bash
pip install -e ".[dev,bigquery]"
ruff check . && pytest
```
Tests use recorded fixtures — **no live GA4 calls in CI.**

## Good first issues
- New **report recipes** in `reports.py` (e.g. device split, new-vs-returning).
- New **conversion matchers** in `config.py` (more `match:` predicates).
- Docs: MCP client config snippets for additional clients.

## PRs
- Keep tool outputs typed (`schemas.py`) and include a one-line `summary`.
- Pin new GA4 fields against the Metadata API and add a fixture.
- Conventional-ish commits appreciated; semantic versioning for releases.
