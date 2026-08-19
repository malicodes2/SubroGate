# ==============================================================================
# SubroGate 1-Command Google Cloud Run Deployment Script (PowerShell)
# ==============================================================================

param (
    [string]$ServiceName = "subrogate",
    [string]$Region = "us-central1",
    [string]$ProjectId = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
    $ProjectId = (gcloud config get-value project 2>$null)
}

if (-not $ProjectId) {
    Write-Error "No active GCP project configured. Run 'gcloud config set project <PROJECT_ID>' first."
    exit 1
}

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host " SubroGate Google Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Active Project:  $ProjectId"
Write-Host "Service Name:    $ServiceName"
Write-Host "Target Region:   $Region"
Write-Host ""

# Step 1: Enable required GCP APIs
Write-Host "Step 1: Enabling required GCP APIs..." -ForegroundColor Yellow
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  aiplatform.googleapis.com `
  cloudtrace.googleapis.com `
  firestore.googleapis.com `
  --project=$ProjectId

# Step 2: Build and Deploy
Write-Host "Step 2: Building and deploying container to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
  --source="." `
  --region=$Region `
  --project=$ProjectId `
  --platform="managed" `
  --allow-unauthenticated `
  --memory="1Gi" `
  --cpu="1" `
  --min-instances="0" `
  --max-instances="5" `
  --port="8080" `
  --set-env-vars="SUBROGATE_ENV=production,SUBROGATE_GEMINI_MODEL=gemini-3.5-flash,SUBROGATE_USE_VERTEX=true,GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$Region,CORS_ORIGINS=https://muhammadasghar0.github.io,http://localhost:5173,*"

$ServiceUrl = (gcloud run services describe $ServiceName --platform="managed" --region=$Region --project=$ProjectId --format="value(status.url)")

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host " SubroGate Deployed Successfully!" -ForegroundColor Green
Write-Host " Service URL: $ServiceUrl" -ForegroundColor Green
Write-Host " Health Check: $ServiceUrl/health" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green

# Step 3: Smoke test
Write-Host "Step 3: Executing Smoke Test against live deployment..." -ForegroundColor Yellow
python scripts/smoke_test.py --url $ServiceUrl
