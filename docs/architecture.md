# SubroGate Architecture Overview 🏗️

## System Design & Foundation Architecture

SubroGate is an agentic forensic assessment system for cargo transit disputes. It adheres to clean architecture principles:
1. **Deterministic Core**: Pure deterministic algorithms for telemetry normalization, threshold breach detection, geofence parsing, and temporal custody alignment.
2. **AI Multimodal & Agentic Reasoning**: Applied where unstructured multimodal extraction (EIR handwriting, seal photos) and contextual reasoning across evidence provide verified value.
3. **Google Agent Development Kit (ADK) Compatibility**: Agent layers adhere to stateless prompt execution, structured Pydantic tool schemas, and verifiable audit trails.
4. **Centralized Model Strategy**: Configurable via `SUBROGATE_GEMINI_MODEL` (e.g. `gemini-2.5-flash`). Model names are never dynamically altered at runtime.

---

## Layered Project Structure

```
SubroGate/
├── backend/
│   ├── config.py             # Centralized settings & SUBROGATE_GEMINI_MODEL validation
│   ├── main.py               # FastAPI application, structured logging, CORS, error handling
│   ├── routes/
│   │   ├── __init__.py
│   │   └── health.py         # /health endpoint with environment & model metadata
│   ├── agents/
│   │   ├── __init__.py
│   │   └── base.py           # Google ADK & Vertex AI / GenAI SDK base agent
│   ├── services/
│   │   ├── __init__.py
│   │   └── logging.py        # Structured JSON & console logging
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydantic foundation schemas
│   ├── utils/
│   │   ├── __init__.py
│   │   └── errors.py         # Custom application exceptions & FastAPI handlers
│   └── tests/
│       ├── test_config.py    # Configuration loading & validation tests
│       └── test_health.py    # Health endpoint & integration tests
├── frontend/
│   ├── src/
│   │   ├── api/client.ts     # Typed API client layer
│   │   ├── components/
│   │   │   ├── Layout.tsx    # Application layout shell
│   │   │   └── Navbar.tsx    # Navigation placeholder with system status & model badge
│   │   ├── types/index.ts    # TypeScript models
│   │   ├── App.tsx           # Foundation application with loading/error states
│   │   ├── index.css         # Modern design tokens
│   │   └── main.tsx          # React entrypoint
│   └── package.json
├── scripts/
│   └── run_backend.py        # Application launch script
├── docs/
│   ├── architecture.md       # Architecture specification
│   └── configuration.md      # Configuration & environment variables guide
└── tests/
    └── test_foundation.py    # Root test suite
```
