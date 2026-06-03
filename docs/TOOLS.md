# FlowGauge Tools

The MCP server exposes five GA4 Data API tools. Each is opinionated: it picks a
sensible dimension/metric set so you don't have to know GA4's schema. All tools
share the same shape.

## Common contract

**Parameters** (all optional):

| Param | Type | Default | Notes |
|---|---|---|---|
| `start` | string | `{lookback_days}daysAgo` | GA4 relative form (`28daysAgo`) or `YYYY-MM-DD`. |
| `end` | string | `today` | Same forms as `start`. |

`acquisition` additionally takes `breakdown` (see below).

**Return** — every tool returns a `ReportResult` (defined in
[`schemas.py`](../src/flowgauge/schemas.py)):

```jsonc
{
  "summary": "string — the one-line answer; lead with this",
  "date_range": "28daysAgo..today",
  "compare_range": null,            // reserved for vs-period comparisons
  "rows": [
    { "dimensions": { "channel": "Organic Social" },
      "metrics":    { "sessions": 1234.0, "engagementRate": 0.41 } }
  ],
  "sampled": false,                 // true if GA4 sampled the result
  "notes": []                       // per-query warnings (e.g. unregistered custom dim)
}
```

Row counts are capped at `report_defaults.cardinality_cap` (default 50) to protect
LLM context. If `sampled` is `true` or `notes` is non-empty, surface that — don't
report sampled or partial numbers as exact.

---

## `traffic_overview`

Sessions, total users, new users, engagement rate, and average session duration —
one row per day.

- **Dimensions:** `date`
- **Metrics:** `sessions`, `totalUsers`, `newUsers`, `engagementRate`, `averageSessionDuration`
- **Summary:** total sessions over the window and the day count.

```text
traffic_overview(start="28daysAgo", end="today")
```

## `acquisition`

Where traffic comes from, ranked by sessions.

- **Param:** `breakdown` = `channel` (default) · `source_medium` · `campaign`
  - `channel` → `sessionDefaultChannelGroup`
  - `source_medium` → `sessionSourceMedium`
  - `campaign` → `sessionCampaignName`
  - An unknown value falls back to `channel`.
- **Metrics:** `sessions`, `totalUsers`, `engagementRate`, `keyEvents`
- **Custom channels:** if you define `channels:` in config, matching rows are
  relabeled and merged into one correctly-aggregated row (additive metrics summed,
  ratios re-weighted by sessions). See [CONFIGURATION.md](CONFIGURATION.md#custom-channels).

```text
acquisition(breakdown="source_medium")
```

## `landing_pages`

Entry pages and whether they hold attention.

- **Dimensions:** `landingPage`
- **Metrics:** `sessions`, `engagementRate`, `bounceRate`, `keyEvents`
- **Read it as:** high-session / low-engagement rows are your leaks.

## `page_engagement`

All pages by attention, not just entries.

- **Dimensions:** `pagePath`
- **Metrics:** `screenPageViews`, `userEngagementDuration`, `eventCount`
- Ordered by views.

## `conversions`

Counts each **config-defined** conversion separately, broken down by channel — so
"store click-out" vs. "Patreon click-out" vs. a marked key event are finally
distinguishable.

- **Output rows:** `{ conversion, channel } -> { count }`
- **Matching:** each `conversions[]` entry in config becomes its own GA4 query:
  - `key_event: true` → counts `keyEvents` (all marked key events).
  - `event_name` (+ `params` / `params_contains`) → counts `eventCount` filtered by
    the event name and event-parameter matches.
- **Custom-dimension requirement:** event-parameter matches (e.g. `link_domain`)
  are queried as **event-scoped custom dimensions**. Register each param in
  **GA4 → Admin → Custom definitions** first. If one isn't registered, that single
  conversion fails into `notes` instead of sinking the whole report.

```text
conversions(start="28daysAgo")
```

See [CONFIGURATION.md](CONFIGURATION.md#conversions) for how to declare conversions.

---

## Planned (not yet implemented)

| Tool | Ships in | Backend |
|---|---|---|
| `flow_paths` | v0.3 | BigQuery (GA4 export) |
| `funnel` | v0.3 | BigQuery (GA4 export) |

The GA4 Data API cannot return ordered session paths or true funnels; those require
the free GA4 → BigQuery export. They are stubbed in
[`bigquery.py`](../src/flowgauge/bigquery.py) and disabled by default.
