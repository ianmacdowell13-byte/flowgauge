# FlowGauge

**Opinionated Google Analytics 4 for people who don't have an analyst. Decisions, not tables.**

FlowGauge is an MCP server + companion skill that turns GA4 into answers to three questions:

1. **Where is my traffic coming from?** (acquisition by channel / source / campaign)
2. **Where is the UX leaking?** (landing pages, engagement, exits, and real session paths)
3. **What should I fix next?** (a prioritized, plain-language read — not a spreadsheet)

> ⚠️ **Pre-release scaffold (v0.1).** The structure, config, and tool surface are defined; live API wiring is marked with `TODO` in the source. See [`docs/SPEC.md`](docs/SPEC.md) for the full design.

## Why another GA4 integration?

There are already many GA4 MCP servers — including [Google's official one](https://github.com/googleanalytics/google-analytics-mcp). **FlowGauge is deliberately not another raw query wrapper.** Those expose "pick dimensions + metrics, get a table," which assumes you know GA4's schema. FlowGauge adds the layer on top that they don't:

- **Config-driven KPIs.** Declare what *success* means for your site once (e.g. "an outbound click to my store or Patreon is a conversion") and every report speaks in those terms.
- **A canonical methodology.** One `traffic-health` routine always runs the same battery and writes a **what's working / what's leaking / fix next** memo.
- **Real UX flow.** Optional BigQuery backend gives true session paths and funnels — which the GA4 Data API cannot do.
- **Shipped as a skill,** so the output is a decision, not raw data.
- **Safe defaults** for non-analysts: sane date windows, cardinality caps, sampling/quota guards.

It generalizes to any site through a single config file — no site-specific logic lives in the code.

## Quickstart

1. **Create a service account** in Google Cloud and download its JSON key.
2. **Grant it read access:** in GA4 → Admin → *Property Access Management*, add the service-account email as **Viewer**.
3. **Configure:**
   ```bash
   cp config/flowgauge.config.example.yaml flowgauge.config.yaml
   # edit property_id, brand_domains, conversions...
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
   export FLOWGAUGE_CONFIG=./flowgauge.config.yaml
   ```
4. **Run:**
   ```bash
   uvx flowgauge            # or: pip install -e . && flowgauge
   ```
5. **Point your MCP client at it.** Example (Claude Desktop / Cowork `mcpServers` block):
   ```json
   {
     "mcpServers": {
       "flowgauge": {
         "command": "uvx",
         "args": ["flowgauge"],
         "env": {
           "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json",
           "FLOWGAUGE_CONFIG": "/path/to/flowgauge.config.yaml"
         }
       }
     }
   }
   ```

## Tools

| Tool | Purpose |
|---|---|
| `describe_property` | Property name, timezone, currency, configured key events |
| `list_fields` | Schema discovery (valid dimensions/metrics, incl. custom) |
| `traffic_overview` | Sessions/users/engagement over time vs. a compare period |
| `acquisition` | Breakdown by channel group / source-medium / campaign |
| `landing_pages` | Landing page × sessions × engagement × bounce × conversions |
| `page_engagement` | Page × views × avg engagement time × exits |
| `conversions` | Your config-defined conversions, by channel and landing page |
| `run_report` | Power-user escape hatch (arbitrary report, with safety caps) |
| `flow_paths` *(BigQuery)* | Most common ordered page/event sequences |
| `funnel` *(BigQuery)* | Step-by-step conversion + drop-off |

The **`traffic-health`** skill (in [`skills/`](skills/traffic-health/SKILL.md)) chains these into a narrative report.

## Status & roadmap

- **v0.1** — scaffold + Data API tools (this release)
- **v0.2** — `traffic-health` skill + HTTP transport + Cowork plugin packaging
- **v0.3** — BigQuery backend (`flow_paths`, `funnel`)
- **v0.4** — optional Google Search Console join on `landingPage`

See [`docs/SPEC.md`](docs/SPEC.md).

## License

[Apache-2.0](LICENSE).
