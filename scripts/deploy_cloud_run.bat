@echo off
REM ==============================================================================
REM SubroGate Google Cloud Run Deployment Script (Windows CMD/PowerShell)
REM ==============================================================================

echo ======================================================================
echo  SubroGate — Google Cloud Run Production Deployment
echo ======================================================================

set REGION=us-central1
set SERVICE_NAME=subrogate-backend
set GEMINI_MODEL=gemini-3.5-flash

if "%GOOGLE_CLOUD_PROJECT%"=="" (
    for /f "tokens=*" %%i in ('gcloud config get-value project 2^>nul') do set GOOGLE_CLOUD_PROJECT=%%i
)

if "%GOOGLE_CLOUD_PROJECT%"=="" (
    echo ERROR: GOOGLE_CLOUD_PROJECT is not set and no default gcloud project found.
    echo Please run: gcloud config set project YOUR_PROJECT_ID
    exit /b 1
)

echo GCP Project:      %GOOGLE_CLOUD_PROJECT%
echo Region:           %REGION%
echo Service Name:     %SERVICE_NAME%
echo Gemini Model:     %GEMINI_MODEL%
echo ======================================================================

echo Enabling necessary GCP services (Cloud Run, Vertex AI, Firestore)...
call gcloud services enable run.googleapis.com aiplatform.googleapis.com firestore.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=%GOOGLE_CLOUD_PROJECT%

echo Building and deploying container to Google Cloud Run...
call gcloud run deploy %SERVICE_NAME% --source . --project %GOOGLE_CLOUD_PROJECT% --region %REGION% --platform managed --allow-unauthenticated --memory 1Gi --cpu 1 --min-instances 0 --max-instances 10 --set-env-vars SUBROGATE_ENV=production,SUBROGATE_GEMINI_MODEL=%GEMINI_MODEL%,SUBROGATE_USE_VERTEX=true,GOOGLE_CLOUD_PROJECT=%GOOGLE_CLOUD_PROJECT%,GOOGLE_CLOUD_LOCATION=%REGION%,CORS_ORIGINS=https://muhammadasghar0.github.io,http://localhost:5173,*

for /f "tokens=*" %%u in ('gcloud run services describe %SERVICE_NAME% --platform managed --region %REGION% --project %GOOGLE_CLOUD_PROJECT% --format "value(status.url)"') do set SERVICE_URL=%%u

echo ======================================================================
echo DEPLOYMENT SUCCESSFUL!
echo Cloud Run API URL: %SERVICE_URL%
echo Health Endpoint:   %SERVICE_URL%/health
echo ======================================================================
