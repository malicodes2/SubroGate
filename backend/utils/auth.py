import logging
from typing import Optional
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..config import get_settings

logger = logging.getLogger("subrogate.auth")
security = HTTPBearer(auto_error=False)

def verify_agent_identity(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> dict:
    """
    Agent Identity & Zero-Trust Access Control Dependency (Fortified Enterprise Fleet).
    Enforces authentication on state-mutating routes when SUBROGATE_API_TOKEN is configured.
    Also extracts caller identity from Google Cloud IAP / Bearer headers if present.
    """
    settings = get_settings()
    expected_token = getattr(settings, "SUBROGATE_API_TOKEN", None)
    
    # Extract identity metadata from Google Cloud headers or Bearer tokens
    iap_user = request.headers.get("X-Goog-Authenticated-User-Email") or request.headers.get("X-Goog-Authenticated-User-Id")
    trace_id = request.headers.get("X-SubroGate-Trace-ID", "internal")
    
    token = None
    if credentials:
        token = credentials.credentials
    elif "X-SubroGate-Token" in request.headers:
        token = request.headers["X-SubroGate-Token"]

    # If an explicit API token is configured in environment, enforce it strictly
    if expected_token:
        if not token or token != expected_token:
            logger.warning(f"Unauthorized access attempt to {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Valid Agent Identity bearer token required for state-mutating operations."
            )

    identity = {
        "authenticated": bool(token or iap_user),
        "actor": iap_user or ("ENTERPRISE_AGENT" if token else "ADJUSTER_ANONYMOUS"),
        "trace_id": trace_id
    }
    request.state.agent_identity = identity
    return identity
