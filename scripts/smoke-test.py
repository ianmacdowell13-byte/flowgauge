#!/usr/bin/env python3
"""FlowGauge smoke test — confirms config + auth + the GA4 Data API all work.

GA4 reads authenticate as YOU via Application Default Credentials (a personal
Google login), because Google stopped letting service accounts created after
~April 2026 be added to GA4. Run these two commands once before this script:

    gcloud auth application-default login \\
      --scopes=openid,https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
    gcloud auth application-default set-quota-project flowgauge-ga4-7842

Then, from the repo root, using the project's virtualenv:

    .venv/bin/python scripts/smoke-test.py
"""
from __future__ import annotations

import os


def main() -> int:
    # GA4 reads should use your user login, not the (GA4-blocked) service account.
    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gac:
        print(f"! GOOGLE_APPLICATION_CREDENTIALS is set:\n    {gac}")
        print("  GA4 reads use your user login (ADC), so a service account here will")
        print("  fail. Unset it for this test:  unset GOOGLE_APPLICATION_CREDENTIALS\n")

    from flowgauge import reports
    from flowgauge.config import load_config
    from flowgauge.ga4_client import GA4Client

    cfg = load_config()
    print(f"Property: {cfg.ga_property}   (timezone {cfg.timezone})")

    client = GA4Client(cfg.ga_property)
    try:
        result = reports.traffic_overview(client, cfg, start="7daysAgo", end="today")
    except Exception as e:  # noqa: BLE001 — we want any failure surfaced with hints
        print(f"\nFAILED to query GA4:\n    {type(e).__name__}: {e}\n")
        print("Likely fixes:")
        print("  • Run the two gcloud ADC commands in this file's header.")
        print("  • Make sure GOOGLE_APPLICATION_CREDENTIALS is NOT pointing at the new")
        print("    service account — Google blocks post-April-2026 SAs from GA4.")
        print("  • Confirm your Google account has access to this GA4 property.")
        print("  • If you see 'user must specify a project', re-run set-quota-project.")
        return 1

    print(f"\nOK — {result.summary}")
    print(f"Date range: {result.date_range}   sampled={result.sampled}")
    for r in result.rows[:5]:
        print(f"    {r.dimensions}  {r.metrics}")
    print("\n✓ Auth + config + GA4 Data API all working.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
