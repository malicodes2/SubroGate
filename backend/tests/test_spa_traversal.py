import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import create_app

def test_spa_fallback_rejects_traversal(tmp_path):
    """
    SEC-01 Regression Test:
    Asserts that path traversal attempts (e.g. /../../backend/config.py or /etc/passwd)
    never return arbitrary source files or sensitive files on disk, but strictly return
    the SPA index.html or 404 when index.html does not exist.
    """
    client = TestClient(create_app())

    traversal_paths = [
        "/..%2f..%2fbackend%2fconfig.py",
        "/../../backend/config.py",
        "/..%2f..%2f..%2f..%2fetc%2fpasswd",
        "/../../../../etc/passwd",
        "/..%2f..%2fDockerfile",
        "/../../Dockerfile",
        "/assets/..%2f..%2fbackend%2fmain.py"
    ]

    for path in traversal_paths:
        res = client.get(path)
        # Should never return python source code or sensitive config content
        assert "SUBROGATE_GEMINI_MODEL" not in res.text, f"Path traversal leaked config.py on path: {path}"
        assert "import uvicorn" not in res.text, f"Path traversal leaked main.py on path: {path}"
        assert "subrogate:subrogate" not in res.text, f"Path traversal leaked Dockerfile on path: {path}"
        assert "root:x:0:0" not in res.text, f"Path traversal leaked /etc/passwd on path: {path}"
