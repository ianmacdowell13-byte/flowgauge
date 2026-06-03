# FlowGauge — Design Spec

*Spec v0.1 — June 2026. Working name `flowgauge`.*

> **One line:** Turn Google Analytics 4 into **decisions, not tables** — a config-driven MCP server plus a Claude/Cowork skill that answers "where's my traffic coming from, where is the UX leaking, and what do I fix next?" for creators and small sites.

---

## 1. Why this exists (and an honest reality check)

A first-party Google Analytics connector is a real gap in most agent ecosystems — you either pay an aggregator or scrape the GA4 UI. **But a GA4 MCP itself is not new.** Know the field before building:

- **Google's official** server: `github.com/googleanalytics/google-analytics-mcp` (Admin API + Data API, raw tools).
- ~10 community servers (`surendranb`, `gomarble-ai`, `mcp-ga4-ultimate` with 54 tools, OAuth variants, etc.).

What they nearly all share: they expose **raw GA4 reporting** — "pick dimensions + metrics, get a table." Powerful for analysts, useless for a solo operator who doesn't know that `sessionDefaultChannelGroup` is the thing to group by.

**The unclaimed niche → the analysis layer on top:**

1. **Config-driven KPIs** — declare "an outbound click to my store/Patreon is my conversion," and every report speaks in those terms.
2. **A canonical methodology** — one `traffic-health` routine that always pulls the same battery and renders a narrative: what's working, what's leaking, what to fix next.
3. **Real UX-flow** — landing→path→exit and funnels, which the GA4 Data API *cannot* do; only the BigQuery export can.
4. **Delivered as a skill**, not just tools — output is a decision memo, not a spreadsheet.
5. **Safe defaults for non-analysts** — sane date ranges, cardinality caps, quota/sampling guards.

Position the repo as *"opinionated GA4 analytics for people who don't have an analyst,"* not *"another GA4 MCP."*

---

## 2. Target users

- **Primary (reference profile):** solo creators / small DTC brands who drive traffic to off-site destinations (a store, Patreon, Etsy, Gumroad, link-in-bio). They care about *acquisition channel → landing page → click-out*, not pageview minutiae. A generic profile — *short-form social → site → store/Patreon* — anchors the docs; it lives only in config, never in code.
- **Secondary:** indie SaaS, bloggers, small agencies wanting a repeatable health check across properties.
- **Explicit non-user:** enterprise analytics teams who want raw, unopinionated query access — point them at Google's official server.

---

## 3. Goals / Non-goals

**Goals**
- Answer the three creator questions (traffic sources, UX flow, conversions) in one command.
- Generalize entirely through a **config file** — zero site-specific logic in code.
- Read-only, least-privilege, no PII handling.
- Run locally with a service-account key; no SaaS middleman, no recurring cost.
- Ship both a thin MCP (composable) and a skill (the opinionated wrapper).

**Non-goals (v1)**
- Writing/altering GA4 config (read-only).
- Replacing a BI tool or dashboards.
- Multi-touch attribution modeling.
- Ad-platform data (Google Ads, Meta) — that's the aggregators' turf.

---

## 4. Architecture

```
                ┌─────────────────────────────────────────────┐
   Claude /     │                flowgauge (MCP)               │
   Cowork  ───▶ │                                              │
   (skill)      │  reports.py   ← opinionated report builders  │
                │      │                                        │
                │      ├── ga4_client.py  → GA4 Data API v1     │  ← traffic, acquisition,
                │      │                     (runReport, etc.)  │     landing, engagement, events
                │      ├── bigquery.py     → GA4→BQ export       │  ← true path/funnel (phase 3)
                │      └── config.py       → flowgauge.config.yaml   │  ← property, conversions, channels
                └─────────────────────────────────────────────┘
                          ▲                         ▲
              service account (analytics.readonly)   BQ dataset (read)
```

- **Two data backends.** The Data API covers ~80% (traffic, acquisition, landing pages, engagement, events/conversions). The **BigQuery export** covers the 20% the Data API can't: ordered session paths and funnels. BigQuery is optional — the server degrades gracefully without it.
- **Transport:** stdio (local) + streamable HTTP (remote/Cowork), standard MCP.
- **Language:** Python (matches Google's client libs; easiest contributor on-ramp). Pydantic for typed outputs.

---

## 5. Authentication & setup

- **Recommended: service account.** Create a GCP service account, download a JSON key, and in **GA4 Admin → Property Access Management** grant that service-account email **Viewer**. Scope: `https://www.googleapis.com/auth/analytics.readonly`. No interactive OAuth, no token refresh.
- **Optional: OAuth 2.0** for multi-tenant / agency use; keep it behind a flag.
- **BigQuery (optional):** the service account needs `roles/bigquery.dataViewer` + `bigquery.jobUser` on the export dataset.
- Secrets via env vars / key-file path; never committed. `flowgauge.config.yaml` holds only non-secret settings.

---

## 6. Configuration — the generalization layer

This file is the entire reason the repo is reusable. Site specifics live here, not in code. See `config/flowgauge.config.example.yaml`. Highlights: `property_id`, `brand_domains`, a `conversions[]` list of named match predicates (event + params, or `key_event: true`), optional `channels` overrides, and `report_defaults` (lookback, compare period, cardinality cap).

---

## 7. Tool surface (MCP)

Small, composable, safe-by-default. Each returns typed JSON + a one-line `summary`.

| Tool | Purpose | Backend |
|---|---|---|
| `describe_property` | Property name, timezone, currency, key events | Admin/Metadata API |
| `list_fields` | Schema discovery (valid dimensions/metrics, incl. custom) | Metadata API |
| `traffic_overview` | Sessions/users/engagement over time + vs. compare | Data API |
| `acquisition` | Channel group / source-medium / campaign breakdown | Data API |
| `landing_pages` | Landing page × sessions × engagement × bounce × conversions | Data API |
| `page_engagement` | Page path × views × avg engagement time × exits | Data API |
| `conversions` | Config `conversions[]` → event/key-event counts by channel | Data API |
| `run_report` | Power-user escape hatch (arbitrary, with safety caps) | Data API |
| `flow_paths` | Most common ordered page/event sequences | BigQuery |
| `funnel` | Step-by-step conversion + drop-off | BigQuery |

**Safety defaults:** 28-day window, `cardinality_cap` rows, sampling warnings in `summary`, quota-aware batching.

---

## 8. The opinionated layer (the actual product)

A **`traffic-health` skill** is the headline deliverable. It runs a fixed battery — `traffic_overview` → `acquisition` → `landing_pages` → `conversions` (→ `flow_paths`/`funnel` if BigQuery is on) — then writes a memo: **what's working / what's leaking / fix next**, with 3–5 prioritized actions. The MCP tools stay generic; the opinion lives in the skill + config.

---

## 9. UX-flow: the honest technical note

GA4's **Data API does not expose path exploration or funnels** (those live only in the Explore UI). Two tiers:

- **Approximate (Data API, always available):** landing pages + exits + event counts → infer where attention starts and dies.
- **Real (BigQuery export, opt-in):** the free GA4→BigQuery export streams raw events (`events_YYYYMMDD`, `event_params`, `user_pseudo_id`, `ga_session_id`, `event_timestamp`). `flow_paths` = sequence events per session ordered by timestamp; `funnel` = conditional aggregation across declared steps. This is the only way to get true session-path / drop-off analysis — and a real differentiator vs. existing GA4 MCPs.

---

## 10. Privacy, security, compliance

- Read-only scope; no Admin writes in v1.
- No PII: aggregates only; never request user-level identifiers via the Data API; BigQuery queries aggregate and never return `user_pseudo_id` rows to the model.
- Cardinality + row caps prevent dumping raw data into an LLM context.
- Service-account key handling documented; `.gitignore` + secret-scanning in CI.
- Short GDPR/region note in docs (GA4 data residency is the user's responsibility).

---

## 11. Roadmap (phased)

- **v0.1 — Core.** Service-account auth, config loader, Data API tools. stdio transport. *(this scaffold)*
- **v0.2 — The skill.** `traffic-health` narrative; HTTP transport; Cowork plugin packaging.
- **v0.3 — Real flow.** BigQuery backend: `flow_paths`, `funnel`.
- **v0.4 — Search context.** Optional Google Search Console join on `landingPage`.
- **Later:** OAuth multi-tenant; realtime; scheduled anomaly alerts.

---

## 12. Open-source plan

- **License: Apache-2.0** (explicit patent grant → companies comfortable adopting/contributing).
- **Repo layout:**
  ```
  flowgauge/
    README.md  LICENSE  NOTICE  CONTRIBUTING.md  pyproject.toml
    src/flowgauge/{server,ga4_client,bigquery,reports,config,schemas}.py
    config/flowgauge.config.example.yaml
    skills/traffic-health/SKILL.md
    docs/SPEC.md  tests/  .github/workflows/ci.yml
  ```
- **Adoption surface:** 5-minute quickstart (create SA → grant Viewer → `uvx flowgauge`), copy-paste MCP client config blocks, a recorded `traffic-health` demo. Frictionless setup is the growth lever.
- **Quality bar:** typed outputs, unit tests with recorded API fixtures (no live calls in CI), semver, CONTRIBUTING + "good first issue" recipes.
- **README leads with differentiation** so it's not mistaken for yet-another raw wrapper.

---

## 13. Risks & open questions

- **Crowded space** — must lead with the analysis/skill angle. *(Mitigation: positioning + BigQuery flow tools + the skill.)*
- **GA4 API field churn** — pin to the Metadata API for discovery; snapshot fixtures in tests.
- **BigQuery cost/complexity** — strictly optional; cache and date-partition queries.
- **Open:** Python vs TypeScript for widest contributor base? Skill in-repo vs separate marketplace entry? Service-account-only in v0.1 vs OAuth immediately for agencies?

---

## Appendix A — example GA4 Data API request (`acquisition`)

```json
POST https://analyticsdata.googleapis.com/v1beta/properties/PROPERTY_ID:runReport
{
  "dateRanges": [{ "startDate": "28daysAgo", "endDate": "today" }],
  "dimensions": [{ "name": "sessionDefaultChannelGroup" }],
  "metrics": [
    { "name": "sessions" }, { "name": "totalUsers" },
    { "name": "engagementRate" }, { "name": "keyEvents" }
  ],
  "orderBys": [{ "metric": { "metricName": "sessions" }, "desc": true }],
  "limit": 50
}
```

## Appendix B — canonical field map

- **Time/traffic:** `date`, `sessions`, `totalUsers`, `newUsers`, `engagedSessions`, `engagementRate`, `averageSessionDuration`, `userEngagementDuration`.
- **Acquisition:** `sessionDefaultChannelGroup`, `sessionSource`, `sessionMedium`, `sessionSourceMedium`, `sessionCampaignName`, `firstUserDefaultChannelGroup`.
- **Pages/UX:** `landingPage` *(also the GSC join key)*, `pagePath`, `pageTitle`, `screenPageViews`, `bounceRate`.
- **Conversions:** `eventName`, `eventCount`, `keyEvents`, `totalRevenue`.

*Field names should be validated against the GA4 Metadata API at build time; they have changed historically.*
