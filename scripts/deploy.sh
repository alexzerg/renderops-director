#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-renderops-director-2026}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-renderops-director}"
REPOSITORY="${REPOSITORY:-renderops}"
VERSION="${VERSION:-$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE}:${VERSION}"
APP_MODE="${RENDEROPS_MODE:-demo}"
MCP_TRANSPORT="${GRAFANA_MCP_TRANSPORT:-demo}"
SEED_TELEMETRY="${RENDEROPS_SEED_TELEMETRY:-false}"
ENV_VARS="RENDEROPS_MODE=${APP_MODE},GRAFANA_MCP_TRANSPORT=${MCP_TRANSPORT}"
ENV_VARS+=",GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}"
ENV_VARS+=",GOOGLE_GENAI_USE_VERTEXAI=true,GEMINI_MODEL=gemini-2.5-flash"
SECRET_ARGS=()

if [[ "$APP_MODE" == "live" ]]; then
  : "${GRAFANA_URL:?GRAFANA_URL is required in live mode}"
  ENV_VARS+=",GRAFANA_URL=${GRAFANA_URL}"
  SECRET_ARGS+=(
    --set-secrets
    "GRAFANA_SERVICE_ACCOUNT_TOKEN=grafana-service-account-token:latest"
  )
fi

if [[ "$SEED_TELEMETRY" == "true" ]]; then
  : "${GRAFANA_OTLP_ENDPOINT:?GRAFANA_OTLP_ENDPOINT is required}"
  : "${GRAFANA_OTLP_INSTANCE_ID:?GRAFANA_OTLP_INSTANCE_ID is required}"
  ENV_VARS+=",RENDEROPS_SEED_TELEMETRY=true"
  ENV_VARS+=",GRAFANA_OTLP_ENDPOINT=${GRAFANA_OTLP_ENDPOINT}"
  ENV_VARS+=",GRAFANA_OTLP_INSTANCE_ID=${GRAFANA_OTLP_INSTANCE_ID}"
  SECRET_ARGS+=(--set-secrets "GRAFANA_OTLP_TOKEN=grafana-otlp-token:latest")
fi

if ! gcloud artifacts repositories describe "$REPOSITORY" \
  --project="$PROJECT_ID" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --repository-format=docker \
    --description="RenderOps Director images" \
    --quiet
fi

gcloud builds submit --project="$PROJECT_ID" --tag="$IMAGE" --quiet .
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "$ENV_VARS" \
  "${SECRET_ARGS[@]}" \
  --quiet

gcloud run services describe "$SERVICE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format='value(status.url)'
