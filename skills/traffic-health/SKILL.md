---
name: traffic-health
description: >
  Run a full GA4 traffic + UX-flow health check and write a decision memo.
  Use when the user asks "how's my traffic", "is my site optimized",
  "where am I losing visitors", "run a traffic health check", or wants a
  read on acquisition, landing-page engagement, or conversion drop-off.
  Requires the flowgauge MCP server to be connected.
---

# Traffic Health

Produce a short, prioritized read on a site's traffic and UX flow using the
`flowgauge` MCP tools. Output **decisions, not tables**.

## Routine

1. **Frame the window.** Default to the config `lookback_days` vs. the compare
   period. State the dates.
2. **Pull the battery** (in order):
   - `traffic_overview` — trend + vs. compare.
   - `acquisition` (breakdown=`channel`, then `source_medium` if a channel is vague) — what's driving visits.
   - `landing_pages` — entry points and their engagement/bounce.
   - `conversions` — config-defined success events, by channel.
   - If BigQuery is enabled: `flow_paths` and/or `funnel` for true drop-off.
3. **Synthesize** into three sections, each 2–5 bullets:
   - **What's working** — channels/pages up vs. compare; best converters.
   - **What's leaking** — high-traffic / low-engagement landing pages; channels
     with traffic but no conversions; biggest path drop-offs.
   - **Fix next** — 3–5 concrete, prioritized actions tied to specific numbers.

## Rules

- Lead with the answer; keep tables minimal and only when they earn their place.
- Always quantify ("engagement rate 38% vs. 52% site-wide"), never vibes.
- Flag sampling/threshold warnings surfaced in tool `notes`.
- Never expose user-level data; operate on aggregates only.
- If a tool errors on auth, tell the user to check the service-account Viewer
  grant and `GOOGLE_APPLICATION_CREDENTIALS`.
