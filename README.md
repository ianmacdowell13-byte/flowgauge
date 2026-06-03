# FlowGauge

**Opinionated Google Analytics 4 for people who don't have an analyst. Decisions, not tables.**

FlowGauge is an MCP server + companion skill that turns GA4 into answers to three questions:

1. **Where is my traffic coming from?** (acquisition by channel / source / campaign)
2. **Where is the UX leaking?** (landing pages, engagement, exits, and real session paths)
3. **What should I fix next?** (a prioritized, plain-language read — not a spreadsheet)

> **v0.1.** The GA4 Data API tools are implemented and working end-to-end. The optional BigQuery backend (`flow_paths` / `funnel`) is still on the roadmap. See [`docs/SPEC.md`](docs/SPEC.md) for the full design.

## Why another GA4 integration?

There are already many GA4 MCP servers — including [Google's official one](https://github.com/googleanalytics/google-analytics-mcp). **FlowGauge is deliberately not another raw query wrapper.** Those expose "pick dimensions + metrics, get a table," which assumes you know GA4's schema. FlowGauge adds the layer on top that they don't:

- **Config-driven KPIs.** Declare what *success* means for your site once (e.g. "an outbound click to my store or Patreon is a conversion") and every report speaks in those terms.
- **A canonical methodology.** One `traffic-health` routine always runs the same battery and writes a **what's working / what's leaking / fix next** memo.
- **Real UX flow.** Optional BigQuery backend gives true session paths and funnels — which the GA4 Data API cannot do.
- **Shipped as a skill,** so the output is a decision, not raw data.
- **Safe defaults** for non-analysts: sane date windows, cardinality caps, sampling/quota guards.

It generalizes to any site through a single config file — no site-specific logic lives in the code.

## Install

```bash
uvx flowgauge          # run without installing (recommended)
# or
pip install flowgauge  # install into your environment
```

From source, for development:

```bash
git clone https://github.com/OWNER/flowgauge && cd flowgauge
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

## Quickstart

1. **Authenticate** as yourself (works today — see [Authentication](#authentication) for why, and the service-account option for CI):
   ```bash
   gcloud auth application-default login \
     --scopes=openid,https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
   gcloud auth application-default set-quota-project <your-gcp-project-id>
   ```
2. **Configure:**
   ```bash
   cp config/flowgauge.config.example.yaml flowgauge.config.yaml
   # edit property_id, brand_domains, conversions...
   export FLOWGAUGE_CONFIG=./flowgauge.config.yaml
   # Leave GOOGLE_APPLICATION_CREDENTIALS unset — FlowGauge uses the login above.
   ```
3. **Verify:**
   ```bash
   .venv/bin/python scripts/smoke-test.py
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
           "FLOWGAUGE_CONFIG": "/path/to/flowgauge.config.yaml"
         }
       }
     }
   }
   ```
   (Using a pre-cutoff service account instead? Add `"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json"` to that `env` block.)

## Authentication

> **Heads-up (June 2026):** Google stopped registering service accounts created
> after ~April 20, 2026 as Google Accounts, so GA4 (and Search Console) reject
> them with *"this email doesn't match a Google Account."* Until Google restores
> that, authenticate to GA4 as **yourself** (a user login). A service-account key
> still works for the optional BigQuery backend, and for GA4 if you have a
> service account created *before* the cutoff.
> Ref: [Google Developer forums](https://discuss.google.dev/t/problem-with-new-service-accounts/362176).

### Authenticate as yourself (recommended)

If your Google account already has access to the GA4 property (Viewer or above),
this needs **no "add user" step**:

```bash
gcloud auth application-default login \
  --scopes=openid,https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
gcloud auth application-default set-quota-project <your-gcp-project-id>
```

Leave `GOOGLE_APPLICATION_CREDENTIALS` **unset** — FlowGauge picks up this login
automatically (`google.auth.default()`). Verify the whole chain:

```bash
.venv/bin/python scripts/smoke-test.py
```

## Service account setup

> Use this path only for the **BigQuery backend**, or if you have a service
> account created **before ~April 20, 2026** (see the heads-up above — newer ones
> can't be added to GA4).

FlowGauge can also authenticate to GA4 with a **service-account key** (not a
personal Google login), so it runs the same way on your laptop, a teammate's
machine, or CI — no per-person OAuth dance.

**Automated (recommended).** From the repo root:

```bash
gcloud auth login                                   # one-time; opens browser. This is CLI auth — it does NOT touch your ADC file.
scripts/setup-service-account.sh <your-gcp-project-id>
```

The script is idempotent and:

1. enables `analyticsdata.googleapis.com` + `analyticsadmin.googleapis.com`,
2. creates the `flowgauge-reader` service account,
3. writes its JSON key to `~/.config/flowgauge/sa-key.json` (mode `600`, **outside the repo** so it can't be committed),
4. prints the service-account email and the export lines.

Don't have a project yet? `gcloud projects create <your-gcp-project-id>` first.

**The one manual step** (GA4 access is not GCP IAM, so it can't be scripted): in
**GA4 → Admin → Property Access Management**, add the printed service-account
email as a **Viewer**.

**Manual equivalent**, if you'd rather not run the script:

```bash
PROJECT=<your-gcp-project-id>
gcloud services enable analyticsdata.googleapis.com analyticsadmin.googleapis.com --project "$PROJECT"
gcloud iam service-accounts create flowgauge-reader --project "$PROJECT" --display-name "FlowGauge (read-only GA4)"
gcloud iam service-accounts keys create ~/.config/flowgauge/sa-key.json \
  --iam-account "flowgauge-reader@${PROJECT}.iam.gserviceaccount.com" --project "$PROJECT"
```

Then `export GOOGLE_APPLICATION_CREDENTIALS=~/.config/flowgauge/sa-key.json` and continue with the [Quickstart](#quickstart).

> The service account needs **no GCP IAM roles** — its only permission is the GA4 Viewer grant you add in the GA4 admin UI. Least privilege by default.

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
