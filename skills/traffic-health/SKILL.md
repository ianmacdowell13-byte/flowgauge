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

1. **Frame the window.** Default to the config `lookback_days`. State the dates.
   Period-over-period compare is **not implemented yet** (it's reserved in
   config) — so judge "good/bad" against **within-window and site-wide
   baselines**, not a prior period. Do **not** report a "no compare period set"
   line or recommend setting one; that's a known gap, not a config the user can
   fix today.
2. **Pull the battery** (in order):
   - `traffic_overview` — sessions/users/engagement across the window.
   - `acquisition` (breakdown=`channel`, then `source_medium` if a channel is vague) — what's driving visits.
   - `landing_pages` — entry points and their engagement/bounce.
   - `conversions` — config-defined success events, by channel.
   - If BigQuery is enabled: `flow_paths` and/or `funnel` for true drop-off.
3. **Synthesize** into three sections, each 2–5 bullets:
   - **What's working** — best channels/pages by engagement and key events; best converters.
   - **What's leaking** — high-traffic / low-engagement landing pages; channels
     with traffic but no conversions; biggest path drop-offs.
   - **Fix next** — 3–5 concrete, prioritized actions tied to specific numbers.

## Rules

- Lead with the answer; keep tables minimal and only when they earn their place.
- Always quantify ("engagement rate 38% vs. 52% site-wide"), never vibes.
- Flag sampling/threshold warnings surfaced in tool `notes`.
- `conversions` counts each config-defined event separately. Event-param matches
  (e.g. `link_domain`) require that param to be registered as an event-scoped
  custom dimension in GA4; if it isn't, the failure surfaces in the report
  `notes` — relay that instead of reporting a silent zero.
- Never expose user-level data; operate on aggregates only.
- If a tool errors on auth, the GA4 credentials aren't reaching the API: confirm
  the user ran `gcloud auth application-default login` (with the
  `analytics.readonly` scope) and that their Google account or service account
  has access to the property. `GOOGLE_APPLICATION_CREDENTIALS` should be set only
  when using a (pre-2026) service-account key, not for user ADC.
