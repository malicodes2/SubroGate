#!/bin/bash
set -e

# ==============================================================================
# SubroGate Google Cloud Run Deployment Script
# Deploys the FastAPI backend with Vertex AI Gemini & Firestore to Cloud Run.
# ==============================================================================

echo "======================================================================"
echo " SubroGate — Google Cloud Run Production Deployment"
echo "======================================================================"

# 1. Project Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}
REGION=${GOOGLE_CLOUD_LOCATION:-"us-central1"}
SERVICE_NAME="subrogate-backend"
GEMINI_MODEL=${SUBROGATE_GEMINI_MODEL:-"gemini-3.5-flash"}

if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: GOOGLE_CLOUD_PROJECT is not set and no default gcloud project found."
  echo "Please run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "GCP Project:      $PROJECT_ID"
echo "Region:           $REGION"
echo "Service Name:     $SERVICE_NAME"
echo "Gemini Model:     $GEMINI_MODEL"
echo "======================================================================"

# 2. Enable Required Google Cloud APIs
echo "Enabling necessary GCP services (Cloud Run, Vertex AI, Firestore, Artifact Registry)..."
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$PROJECT_ID"

# 3. Build and Deploy Container directly to Cloud Run
echo "Building and deploying to Google Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "SUBROGATE_ENV=production,SUBROGATE_GEMINI_MODEL=$GEMINI_MODEL,SUBROGATE_USE_VERTEX=true,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION"

# 4. Fetch Deployed Cloud Run Service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --project "$PROJECT_ID" --format 'value(status.url)')

echo "======================================================================"
echo "DEPLOYMENT SUCCESSFUL!"
echo "Cloud Run API URL: $SERVICE_URL"
echo "Health Endpoint:   $SERVICE_URL/health"
echo "======================================================================"
echo ""
echo "Next step: In your GitHub Repository Settings -> Secrets and variables -> Actions:"
echo "Set VITE_API_BASE_URL to $SERVICE_URL"
echo "Or build the frontend locally pointing to this URL:"
echo "cd frontend && VITE_API_BASE_URL=$SERVICE_URL npm run build"
