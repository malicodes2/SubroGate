# SubroGate Deployment Manual: Google Cloud Run

This document provides complete instructions for packaging, configuring, and deploying SubroGate to **Google Cloud Run** as a unified, production-ready enterprise container.

---

## 1. Deployment Architecture

SubroGate is packaged as a **single, unified container** to eliminate multi-service complexity:
- **Frontend**: React 18 + TypeScript + Vite compiled into a static production bundle (`/app/frontend/dist`).
- **Backend**: FastAPI with Python 3.12, serving both the REST API endpoints (`/api/*`, `/health`) and mounting the React Single-Page Application (SPA) at `/`.
- **AI & Cloud Engine**: Google GenAI SDK / Vertex AI Gemini 2.5 Flash, OpenTelemetry Cloud Trace exporter, Google Model Armor, and Firestore case repository.

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Run                         │
│                                                             │
│   ┌───────────────────────────┐  ┌───────────────────────┐  │
│   │ React SPA Dashboard (/)   │  │ FastAPI REST (/api/*) │  │
│   └─────────────┬─────────────┘  └───────────┬───────────┘  │
│                 │                            │              │
│                 └──────────────┬─────────────┘              │
│                                │                            │
│                  ┌─────────────┴────────────┐               │
│                  │  OpenTelemetry / Logger  │               │
│                  └─────────────┬────────────┘               │
└────────────────────────────────┼────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                    ▼
     Google Vertex AI    Google Cloud Trace   Google Cloud Firestore
     (Gemini 2.5 Flash)  (Distributed Spans)  (Persistent Cases)
```

---

## 2. Prerequisites

1. **Google Cloud SDK (`gcloud` CLI)**:
   ```bash
   gcloud version
   gcloud auth login
   gcloud config set project <YOUR_GCP_PROJECT_ID>
   ```
2. **Enable Required GCP APIs**:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     aiplatform.googleapis.com \
     cloudtrace.googleapis.com \
     firestore.googleapis.com
   ```
3. **IAM Service Account Roles**:
   Ensure the Cloud Run service account has the following IAM roles:
   - `roles/aiplatform.user` (Vertex AI Model Invocations)
   - `roles/cloudtrace.agent` (OpenTelemetry Trace Export)
   - `roles/datastore.user` (Firestore Database Access)

---

## 3. Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Container listening port (automatically set by Cloud Run) |
| `SUBROGATE_ENV` | `production` | Environment tier (`production`, `development`) |
| `SUBROGATE_GEMINI_MODEL` | `gemini-2.5-flash` | Configured Gemini Model strategy |
| `SUBROGATE_USE_VERTEX` | `true` | Enables Google Vertex AI authentication via Service Account |
| `GOOGLE_CLOUD_PROJECT` | *(GCP Project)* | Target Google Cloud Project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Vertex AI & Cloud Run region |
| `GEMINI_API_KEY` | *(Optional)* | Used when operating with Google AI Studio instead of Vertex |

---

## 4. 1-Command Deployment

### Option A: Using the Deployment Script
```bash
# On Linux / macOS / Google Cloud Shell:
chmod +x scripts/deploy_cloud_run.sh
./scripts/deploy_cloud_run.sh

# On Windows PowerShell:
.\scripts\deploy_cloud_run.ps1
```

### Option B: Using `gcloud run deploy` directly
```bash
gcloud run deploy subrogate \
  --source="." \
  --region="us-central1" \
  --platform="managed" \
  --allow-unauthenticated \
  --memory="1Gi" \
  --cpu="1" \
  --min-instances="0" \
  --max-instances="5" \
  --port="8080" \
  --set-env-vars="SUBROGATE_ENV=production,SUBROGATE_GEMINI_MODEL=gemini-2.5-flash,SUBROGATE_USE_VERTEX=true,GOOGLE_CLOUD_LOCATION=us-central1"
```

### Option C: Using Google Cloud Build CI/CD
```bash
gcloud builds submit --config=cloudbuild.yaml
```

---

## 5. Post-Deployment Smoke Testing

Verify the deployed service using the automated smoke test script:
```bash
# Test against your deployed Cloud Run URL:
python scripts/smoke_test.py --url https://subrogate-<YOUR_HASH>-uc.a.run.app
```

The smoke test validates:
1. `GET /health` &rarr; Returns HTTP 200, system health, and active model.
2. `GET /api/observability/status` &rarr; Confirms OpenTelemetry engine status.
3. `POST /api/cases/demo/load-clean` &rarr; Ingests and saves dispute case.
4. `GET /api/cases/CASE-2026-DEMO-MSKU` &rarr; Validates timeline and assessment.
5. `POST /api/investigation/simulate-telemetry-event` &rarr; Validates async background pipeline.
6. `GET /` &rarr; Confirms React SPA delivery.

---

## 6. Observability & Monitoring

- **Google Cloud Trace**: View distributed traces in the GCP Console under **Trace &rarr; Trace Explorer**.
- **Google Cloud Logging**: Structured JSON log entries stream directly to **Logs Explorer** (`resource.type="cloud_run_revision"`).
- **Execution Trace UI**: The interactive dashboard at `/` displays safe operational execution events in real time.
