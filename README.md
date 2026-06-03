# FlowGauge

**Opinionated Google Analytics 4 for people who don't have an analyst. Decisions, not tables.**

FlowGauge is an MCP server + companion skill that turns GA4 into answers to three questions:

1. **Where is my traffic coming from?** (acquisition by channel / source / campaign)
2. **Where is the UX leaking?** (landing pages, engagement, exits, and real session paths)
3. **What should I fix next?** (a prioritized, plain-language read — not a spreadsheet)

> **v0.1.** The GA4 Data API tools are implemented and working end-to-end. The optional BigQuery backend (`flow_paths` / `funnel`) is still on the roadmap. See [`docs/SPEC.md`](docs/SPEC.md) for the full design.

## Who it's for

**FlowGauge is for you if** you own a website's analytics but you're not an
analyst — a solo founder, creator, indie hacker, or small-team marketer who has
GA4 set up, uses Claude (Code or Desktop) or another MCP client, and wants
*"what should I do about my traffic?"* without learning GA4's dimension/metric
schema.

**It's probably not for you if** you're a data analyst who wants raw,
arbitrary GA4 queries (use [Google's official MCP server](https://github.com/googleanalytics/google-analytics-mcp)
for that), or you don't have a GA4 property yet.

## What you get

Ask Claude *"run a traffic health check"* and FlowGauge returns a prioritized
memo, not a spreadsheet:

````text
Traffic Health — last 29 days (no compare window; baselines are site-wide)

Bottom line
Traffic is healthy and social-led — ~50% Organic Social, ~80% engagement. The
problem isn't getting people in; it's that conversion tracking looks broken and
the catalog page leaks half its visitors.

What's working
• Organic Social is the engine: ~2,000 sessions (~50% of traffic), 80% engagement.
• Homepage holds attention: 83% engagement, 17% bounce — best entry point on the site.
• Organic Search is efficient: 290 key events from just 674 sessions.

What's leaking
• store_clickout = 0 and patreon_clickout = 1 in 29 days — that's a broken/
  uninstrumented event, not real demand. Highest-value fix.
• /catalog: ~370 sessions at 46% engagement / 54% bounce, vs. 83% on the homepage.
• ~285 untagged sessions (8.5%) at ~95% bounce — social in-app browsers stripping
  the referrer.

Fix next
1. Audit the clickout events — confirm they fire and are registered as GA4 key events.
2. Rework /catalog — a 54% bounce on your main catalog is the biggest on-site leak.
3. UTM-tag social links to recover the ~285 untagged sessions.

Hand-off prompt  (copy into your coding agent)
```
My GA4 traffic-health check found three issues on my site — please
investigate and fix:

1. Conversion tracking looks broken: the `store_clickout` event fired 0 times
   and `patreon_clickout` 1 time over 29 days, despite the membership page
   getting real traffic. Verify both events fire on the live buttons and are
   registered as GA4 key events; fix the wiring if they aren't.
2. The /catalog page leaks visitors — 54% bounce / 46% engagement vs. 83% on
   the homepage. Audit it and tighten above-the-fold (clear thumbnails, CTAs).
3. ~8.5% of sessions arrive untagged (~95% bounce) — social in-app browsers
   stripping the referrer. Add UTM parameters to my social bio/link posts so
   that traffic becomes attributable.
```
````

*(Real output from a live site, lightly anonymized — paths genericized, numbers rounded.)*

## Why another GA4 integration?

There are already many GA4 MCP servers — including [Google's official one](https://github.com/googleanalytics/google-analytics-mcp). **FlowGauge is deliberately not another raw query wrapper.** Those expose "pick dimensions + metrics, get a table," which assumes you know GA4's schema. FlowGauge adds the layer on top that they don't:

- **Config-driven KPIs.** Declare what *success* means for your site once (e.g. "an outbound click to my store or Patreon is a conversion") and every report speaks in those terms.
- **A canonical methodology.** One `traffic-health` routine always runs the same battery and writes a **what's working / what's leaking / fix next** memo.
- **Real UX flow.** Optional BigQuery backend gives true session paths and funnels — which the GA4 Data API cannot do.
- **Shipped as a skill,** so the output is a decision, not raw data.
- **Safe defaults** for non-analysts: sane date windows, cardinality caps, sampling/quota guards.

It generalizes to any site through a single config file — no site-specific logic lives in the code.

## Install

FlowGauge ships two ways. Both run the same MCP server and skill — pick the one
that matches your client.

### Option A — Claude Code plugin (one command)

```text
/plugin marketplace add ianmacdowell13-byte/flowgauge
/plugin install flowgauge@flowgauge
```

This connects the FlowGauge MCP server **and** loads the `traffic-health` skill.
It runs the server via `uvx flowgauge`, so you need [`uv`](https://docs.astral.sh/uv/)
on your PATH. You still complete the one-time GA4 setup below
([Authentication](#authentication) + a `flowgauge.config.yaml`) — the plugin
makes *connecting the tool* one step, not *configuring analytics access*.

### Option B — any MCP client (Claude Desktop, Cursor, …)

```bash
uvx flowgauge          # run without installing (recommended)
# or
pip install flowgauge  # install into your environment
```

Then add it to your client's MCP config (see [Quickstart](#quickstart) step 5).

### From source (development)

```bash
git clone https://github.com/ianmacdowell13-byte/flowgauge && cd flowgauge
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

6. **Ask for a read.** In your client: *"run a traffic health check"* — the
   `traffic-health` skill chains the tools and writes the memo shown in
   [What you get](#what-you-get). (Plugin users get the skill automatically;
   otherwise, point the client at [`skills/traffic-health/SKILL.md`](skills/traffic-health/SKILL.md).)

## Authentication

**Authenticate as yourself** — the recommended path. If your Google account
already has access to the GA4 property (Viewer or above), this needs **no "add
user" step**:

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

> **Why not a service account?** (June 2026) Google stopped registering service
> accounts created after ~April 20, 2026 as Google Accounts, so GA4 rejects them
> with *"this email doesn't match a Google Account."* Authenticate as yourself
> until that's restored. A service-account key still works for the optional
> BigQuery backend, and for GA4 if your service account predates the cutoff.
> Ref: [Google Developer forums](https://discuss.google.dev/t/problem-with-new-service-accounts/362176).

## Service account setup

> Use this path only for the **BigQuery backend**, or if you have a service
> account created **before ~April 20, 2026** (see the note above — newer ones
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

## Billing & data access

FlowGauge is **just code** — there is no hosted FlowGauge service, and nothing
routes through the author's accounts:

- **You bring your own GA4 property and Google credentials.** Every API call runs
  under *your* auth against *your* property.
- **The GA4 Data API is free.** Google rate-limits it with per-property quotas but
  does not bill per request. Installing FlowGauge costs you nothing in API fees.
- **No keys are embedded.** The package ships only placeholder config; your real
  config and credentials stay on your machine and are git-ignored.
- **The only thing that can cost money** is the optional BigQuery backend
  (`flow_paths` / `funnel`), which runs on *your* GCP billing, is opt-in, and ships
  **disabled by default**.

## Tools

**Available now** (GA4 Data API — implemented and tested):

| Tool | Purpose |
|---|---|
| `traffic_overview` | Sessions / users / new users / engagement over time |
| `acquisition` | Breakdown by channel group / source-medium / campaign |
| `landing_pages` | Landing page × sessions × engagement × bounce × key events |
| `page_engagement` | Page × views × engagement time × event count |
| `conversions` | Your config-defined conversions, broken down by channel |

Each tool takes optional `start` / `end` dates (GA4 relative forms like
`28daysAgo`, or `YYYY-MM-DD`) and returns a typed `ReportResult` — a one-line
`summary`, the `rows`, a `date_range`, a `sampled` flag, and any `notes`. Full
reference: [`docs/TOOLS.md`](docs/TOOLS.md).

**Planned** (designed in [`docs/SPEC.md`](docs/SPEC.md), not yet implemented):

| Tool | Ships in | Purpose |
|---|---|---|
| `flow_paths` *(BigQuery)* | v0.3 | Most common ordered page/event sequences |
| `funnel` *(BigQuery)* | v0.3 | Step-by-step conversion + drop-off |

The **`traffic-health`** skill (in [`skills/`](skills/traffic-health/SKILL.md)) chains the available tools into a narrative report.

## Status & roadmap

- **v0.1** — scaffold + Data API tools ✓
- **v0.2** — `traffic-health` skill + Claude Code plugin packaging ✓ *(current)*
- **v0.3** — period-over-period compare (wire up `report_defaults.compare`) + BigQuery backend (`flow_paths`, `funnel`)
- **v0.4** — optional Google Search Console join on `landingPage`

See [`docs/SPEC.md`](docs/SPEC.md).

## License

[Apache-2.0](LICENSE).
