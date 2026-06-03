# Configuring FlowGauge

All site-specific behavior lives in one YAML file — the code stays generic. Copy
the example and edit:

```bash
cp config/flowgauge.config.example.yaml flowgauge.config.yaml
export FLOWGAUGE_CONFIG=./flowgauge.config.yaml   # or pass the path to load_config()
```

FlowGauge resolves the config from, in order: an explicit path → `$FLOWGAUGE_CONFIG`
→ `./flowgauge.config.yaml`. The real config is git-ignored; only the `.example` is
committed.

## Full schema

Validated by [`config.py`](../src/flowgauge/config.py) (pydantic). Unknown keys are
rejected, so a typo fails fast.

```yaml
property_id: "123456789"        # required — bare numeric ID or "properties/123456789"
timezone: America/New_York      # informational; GA4 reports in the property's own tz
brand_domains: [example.com]    # used to classify internal vs. outbound

conversions: []                 # see "Conversions" below
channels: {}                    # see "Custom channels" below

report_defaults:
  lookback_days: 28             # default window when start/end aren't passed
  compare: previous_period      # previous_period | previous_year | none  (reserved)
  cardinality_cap: 50           # max rows per breakdown — protects LLM context
  currency: USD

bigquery:
  enabled: false                # opt-in; off by default
  project: "my-gcp-project"
  dataset: "analytics_123456789"
```

### `property_id` (required)

Your GA4 numeric property ID (Admin → Property Settings). Either `"123456789"` or
`"properties/123456789"` — FlowGauge normalizes to the full resource name.

## Conversions

Declare what *success* means for your site. Each entry becomes its own
`conversions` query and is counted separately, by channel.

```yaml
conversions:
  # Substring match on an event parameter (robust to subdomains / www.):
  - name: store_clickout
    match: { event_name: click, params_contains: { link_domain: myshop } }

  - name: patreon_clickout
    match: { event_name: click, params_contains: { link_domain: patreon.com } }

  # Exact event-parameter match:
  - name: signup
    match: { event_name: form_submit, params: { form_id: newsletter } }

  # Reuse the key events you already marked in GA4 (no custom dimension needed):
  - name: key_event
    match: { key_event: true }
```

**Match semantics** (`ConversionMatch`):

| Field | Meaning |
|---|---|
| `event_name` | Exact GA4 event name (e.g. `click`). |
| `params` | Exact event-parameter equalities. AND-ed together. |
| `params_contains` | Substring matches on event parameters. AND-ed together. |
| `key_event` | `true` → count all GA4-marked key events; ignores the fields above. |

> **Custom dimensions are required for param matches.** `params` / `params_contains`
> query the parameter as an **event-scoped custom dimension** (`customEvent:<param>`).
> Register each one in **GA4 → Admin → Custom definitions** first. If you don't, that
> single conversion surfaces an error in the report `notes` instead of silently
> reporting zero — and the rest of the report still runs.

A match with neither `key_event` nor `event_name` is skipped with a note.

## Custom channels

Override GA4's default channel grouping when it misclassifies sources. Each rule
relabels rows whose source/medium contains any token, then merges the collapsed
rows into one correctly-aggregated channel.

```yaml
channels:
  Social-Short-Form:
    source_contains: [tiktok, "t.co", instagram, youtube]
```

With the above, `tiktok / referral` and `instagram / social` both become a single
`Social-Short-Form` row in `acquisition` — sessions/key-events summed, and ratio
metrics (engagement rate, bounce rate) recombined as a session-weighted average.

## Report defaults

| Key | Default | Effect |
|---|---|---|
| `lookback_days` | `28` | Window used when a tool gets no `start`/`end`. |
| `compare` | `previous_period` | Reserved for vs-period deltas (not yet wired). |
| `cardinality_cap` | `50` | Max rows per breakdown — keeps responses LLM-sized. |
| `currency` | `USD` | Informational. |

## BigQuery (optional, v0.3)

True session paths and funnels need the free GA4 → BigQuery export — the Data API
can't produce them. Disabled by default; when you enable it, queries run on **your**
GCP billing.

```yaml
bigquery:
  enabled: true
  project: "my-gcp-project"
  dataset: "analytics_123456789"   # the GA4 export dataset
```

`flow_paths` and `funnel` land in v0.3; until then they raise `NotImplementedError`
even when configured. Enabling without both `project` and `dataset` raises a clear
`BigQueryDisabled` error.
