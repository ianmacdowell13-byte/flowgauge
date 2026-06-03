#!/usr/bin/env bash
#
# setup-service-account.sh — provision a read-only GA4 service account for FlowGauge.
#
# What it does (idempotent — safe to re-run):
#   1. Enables the GA4 Data + Admin APIs on your project.
#   2. Creates a service account named "flowgauge-reader".
#   3. Creates and downloads a JSON key to a path OUTSIDE this repo.
#   4. Prints the one manual step (granting the SA Viewer in GA4) and the
#      exact env vars to export.
#
# What it does NOT do:
#   - It never runs `gcloud auth login` for you, and never touches your
#     Application Default Credentials. CLI auth and ADC are separate stores.
#   - It cannot grant GA4 property access — that lives in GA4 Admin, not GCP IAM.
#     (The script prints the exact step.)
#
# Usage:
#   scripts/setup-service-account.sh <GCP_PROJECT_ID>
#
# Optional overrides via env vars:
#   SA_NAME    service account id          (default: flowgauge-reader)
#   KEY_PATH   where to write the JSON key (default: ~/.config/flowgauge/sa-key.json)
#
set -euo pipefail

SA_NAME="${SA_NAME:-flowgauge-reader}"
KEY_PATH="${KEY_PATH:-$HOME/.config/flowgauge/sa-key.json}"

die() { printf '\033[31merror:\033[0m %s\n' "$1" >&2; exit 1; }
info() { printf '\033[36m==>\033[0m %s\n' "$1"; }

# --- preconditions ----------------------------------------------------------
command -v gcloud >/dev/null 2>&1 || die "gcloud not found. Install the Google Cloud CLI: https://cloud.google.com/sdk/docs/install"

PROJECT_ID="${1:-}"
[ -n "$PROJECT_ID" ] || die "missing project id.  Usage: $0 <GCP_PROJECT_ID>"

# Confirm an account is logged in (this is CLI auth, NOT ADC).
if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep -q .; then
  die "no active gcloud account. Run 'gcloud auth login' first (opens your browser; does not touch ADC)."
fi

# Confirm the project exists and we can see it.
gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1 \
  || die "cannot access project '$PROJECT_ID' (wrong id, or no permission). Create one with: gcloud projects create $PROJECT_ID"

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# --- 1. enable APIs ---------------------------------------------------------
info "Enabling GA4 Data + Admin APIs on ${PROJECT_ID} (no-op if already enabled)…"
gcloud services enable \
  analyticsdata.googleapis.com \
  analyticsadmin.googleapis.com \
  --project "$PROJECT_ID"

# --- 2. create the service account (skip if it exists) ----------------------
if gcloud iam service-accounts describe "$SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1; then
  info "Service account already exists: ${SA_EMAIL}"
else
  info "Creating service account ${SA_NAME}…"
  gcloud iam service-accounts create "$SA_NAME" \
    --project "$PROJECT_ID" \
    --display-name "FlowGauge (read-only GA4)"
fi

# --- 3. create + download the key -------------------------------------------
mkdir -p "$(dirname "$KEY_PATH")"
if [ -f "$KEY_PATH" ]; then
  info "Key already present at ${KEY_PATH} — leaving it untouched."
  info "      (To rotate, delete that file and re-run, or set KEY_PATH=… for a new one.)"
else
  info "Creating key → ${KEY_PATH}"
  gcloud iam service-accounts keys create "$KEY_PATH" \
    --iam-account "$SA_EMAIL" \
    --project "$PROJECT_ID"
  chmod 600 "$KEY_PATH"
fi

# --- done: print the human steps --------------------------------------------
cat <<EOF

$(printf '\033[32m✓ Service account ready.\033[0m')

Service account email:
    ${SA_EMAIL}

ONE manual step (cannot be scripted — GA4 access is not GCP IAM):
    GA4 → Admin → Property Access Management → "+" → Add the email above
    as a Viewer:
        ${SA_EMAIL}

Then point FlowGauge at the key:
    export GOOGLE_APPLICATION_CREDENTIALS="${KEY_PATH}"
    export FLOWGAUGE_CONFIG="\$(pwd)/flowgauge.config.yaml"

And set your GA4 numeric property_id in flowgauge.config.yaml.
EOF
