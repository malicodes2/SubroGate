# SubroGate Configuration Guide ⚙️

## Environment Variables & Model Strategy

All configuration parameters are centralized in `backend/config.py` using Pydantic Settings.

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SUBROGATE_GEMINI_MODEL` | `gemini-3.5-flash` | Centralized eligible Google Gemini model name (e.g. `gemini-3.5-flash`, `gemini-3.5-pro`). |
| `SUBROGATE_ENV` | `production` | Runtime environment (`development`, `staging`, `production`, `test`). |
| `SUBROGATE_HOST` | `0.0.0.0` | Bind host for FastAPI server. |
| `SUBROGATE_PORT` | `8080` | Bind port for FastAPI server (supports dynamic Cloud Run `PORT`). |
| `SUBROGATE_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `GEMINI_API_KEY` | *(None)* | Google AI Studio API Key (for local development). |
| `GOOGLE_CLOUD_PROJECT` | *(None)* | GCP Project ID (for Vertex AI & Firestore on Cloud Run). |
| `GOOGLE_CLOUD_LOCATION`| `us-central1` | GCP Region for Vertex AI. |
| `SUBROGATE_USE_VERTEX` | `true` | Set `true` to route via Google Cloud Vertex AI rather than AI Studio. |
| `SUBROGATE_API_TOKEN` | *(None)* | Optional Bearer token for Zero-Trust Agent Identity & endpoint protection. |
| `CORS_ORIGINS` | `https://malicodes2.github.io,http://localhost:5173,http://localhost:8080` | Allowed CORS origins (comma-separated). |

---

## Security & Principles

- **No Hardcoded Secrets**: Secrets, project IDs, and model keys must never be hardcoded in application code.
- **Fail-Safe Offline Mode**: If API credentials are not provided in development, agents operate in deterministic mode without failing server startup.
- **Strict Validation**: Invalid ports or model names raise explicit validation errors at initialization time.
