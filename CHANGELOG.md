# Changelog

All notable changes to FlowGauge are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-06-03

### Added
- MCP server exposing opinionated GA4 Data API tools: `traffic_overview`,
  `acquisition`, `landing_pages`, `page_engagement`, and `conversions`.
- Config-driven KPIs via `flowgauge.config.yaml`: per-site conversions, custom
  channel overrides, and report defaults — no site-specific logic in the code.
- Per-conversion breakdown by channel, with exact (`params`) and substring
  (`params_contains`) event-parameter matching, queried via event-scoped custom
  dimensions; failures isolate per conversion instead of sinking the report.
- `traffic-health` skill that chains the tools into a "what's working / what's
  leaking / fix next" decision memo.
- `scripts/setup-service-account.sh` (service-account provisioning) and
  `scripts/smoke-test.py` (end-to-end auth + config check).
- PyPI release via GitHub Actions Trusted Publishing.

### Notes
- GA4 reads authenticate via Application Default Credentials — a user login or a
  service-account key created before ~April 2026. See README → Authentication.
