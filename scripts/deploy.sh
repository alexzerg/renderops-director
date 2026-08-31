#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-renderops-director-2026}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-renderops-director}"
REPOSITORY="${REPOSITORY:-renderops}"
VERSION="${VERSION:-$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE}:${VERSION}"

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
  --set-env-vars "RENDEROPS_MODE=demo,GRAFANA_MCP_TRANSPORT=demo,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=true,GEMINI_MODEL=gemini-2.5-flash" \
  --quiet

gcloud run services describe "$SERVICE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format='value(status.url)'
