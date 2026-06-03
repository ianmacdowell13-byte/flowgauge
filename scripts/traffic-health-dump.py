#!/usr/bin/env python3
"""Run the full FlowGauge traffic-health battery and dump results to JSON.

This pulls the same reports the `traffic-health` skill chains, for the current
lookback window AND the previous (compare) window, and writes everything to
traffic-health-data.json in the repo root. Hand that file back to Claude to get
the "what's working / what's leaking / fix next" memo.

Run (from anywhere, using the project's venv):
    cd ~/code/flowgauge && .venv/bin/python scripts/traffic-health-dump.py
"""
from __future__ import annotations

import json
from pathlib import Path


def _ser(result) -> dict:
    return {
        "summary": result.summary,
        "date_range": result.date_range,
        "sampled": result.sampled,
        "notes": list(result.notes),
        "rows": [{"dimensions": r.dimensions, "metrics": r.metrics} for r in result.rows],
    }


def main() -> int:
    from flowgauge import reports
    from flowgauge.config import load_config
    from flowgauge.ga4_client import GA4Client

    cfg = load_config()
    client = GA4Client(cfg.ga_property)
    look = cfg.report_defaults.lookback_days

    # Current window vs. the immediately preceding window of equal length.
    cur = (f"{look}daysAgo", "today")
    prev = (f"{2 * look}daysAgo", f"{look + 1}daysAgo")

    out: dict = {
        "property": cfg.ga_property,
        "timezone": cfg.timezone,
        "lookback_days": look,
        "windows": {"current": cur, "compare": prev},
        "conversions_configured": [c.name for c in cfg.conversions],
        "reports": {},
    }
    r = out["reports"]

    r["traffic_overview_current"] = _ser(reports.traffic_overview(client, cfg, *cur))
    r["traffic_overview_compare"] = _ser(reports.traffic_overview(client, cfg, *prev))
    r["acquisition_channel"] = _ser(reports.acquisition(client, cfg, "channel", *cur))
    r["acquisition_source_medium"] = _ser(reports.acquisition(client, cfg, "source_medium", *cur))
    r["acquisition_campaign"] = _ser(reports.acquisition(client, cfg, "campaign", *cur))
    r["landing_pages"] = _ser(reports.landing_pages(client, cfg, *cur))
    r["page_engagement"] = _ser(reports.page_engagement(client, cfg, *cur))
    r["conversions"] = _ser(reports.conversions(client, cfg, *cur))

    dest = Path(__file__).resolve().parent.parent / "traffic-health-data.json"
    dest.write_text(json.dumps(out, indent=2))

    print(f"✓ Wrote {dest}")
    print(f"  property {cfg.ga_property}, window {cur[0]}..{cur[1]} vs {prev[0]}..{prev[1]}")
    print(f"  {len(r)} reports captured. Hand this file to Claude for the memo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
