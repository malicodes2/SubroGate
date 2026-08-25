from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from ..config import get_settings

router = APIRouter(prefix="/agents", tags=["Agent Registry & Fleet Catalog"])

class AgentManifest(BaseModel):
    agent_id: str
    name: str
    version: str
    category: str
    role: str
    model_binding: str
    framework: str
    human_gated: bool
    requires_scopes: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    description: str
    capabilities: List[str]

class AgentRegistryCatalog(BaseModel):
    catalog_version: str
    fleet_name: str
    total_agents: int
    environment: str
    agents: List[AgentManifest]

@router.get("", response_model=AgentRegistryCatalog)
@router.get("/", response_model=AgentRegistryCatalog)
def list_agent_registry() -> AgentRegistryCatalog:
    """
    Agent Registry & Fleet Catalog Endpoint (Fortified Enterprise Fleet Pillar).
    Returns versioned agent declarations, model bindings, authorization scopes,
    and schema contracts for institutional discovery and cross-department reuse.
    """
    settings = get_settings()
    configured_model = settings.SUBROGATE_GEMINI_MODEL

    agents = [
        AgentManifest(
            agent_id="investigator-agent",
            name="Forensic Investigator Agent",
            version="2.0.0",
            category="DISPUTE_ARBITRATION",
            role="Multimodal Custody Extraction, Timeline Fusion & Responsibility Determination",
            model_binding=configured_model,
            framework="Google GenAI SDK",
            human_gated=True,
            requires_scopes=["investigation:read", "investigation:assess", "cases:write"],
            input_schema={
                "type": "object",
                "properties": {
                    "eir_document": {"type": "file", "format": "pdf/image"},
                    "telemetry_csv": {"type": "file", "format": "csv"},
                    "shipment_metadata": {"type": "object"}
                },
                "required": ["eir_document", "telemetry_csv"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "potentially_responsible_party": {"type": "string"},
                    "responsibility_confidence": {"type": "number"},
                    "normalized_timeline": {"type": "array"},
                    "supporting_evidence": {"type": "array"},
                    "applicable_legal_framework": {"type": "array"}
                }
            },
            description="Reconstructs intermodal transit timelines by fusing optical EIR custody records with calibrated IoT time-series telemetry. Applies Carmack Amendment statutory logic to determine primary liability.",
            capabilities=[
                "Deterministic UTC timestamp normalization",
                "ISO 6346 container check-digit verification",
                "Temperature & shock excursion correlation",
                "Statutory legal citation grounding"
            ]
        ),
        AgentManifest(
            agent_id="settlement-agent",
            name="Autonomous Settlement & Recovery Agent",
            version="2.0.0",
            category="CLAIMS_RECOVERY",
            role="Legal Demand Generation, Carrier Defense Analysis & Negotiation Rebuttal",
            model_binding=configured_model,
            framework="Google GenAI SDK",
            human_gated=True,
            requires_scopes=["settlement:read", "settlement:draft", "settlement:dispatch"],
            input_schema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "inbound_carrier_objection": {"type": "object"},
                    "human_approval_token": {"type": "string"}
                },
                "required": ["case_id", "human_approval_token"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string"},
                    "draft_subject": {"type": "string"},
                    "draft_body_markdown": {"type": "string"},
                    "relevant_evidence_citations": {"type": "array"},
                    "proposed_settlement_amount_usd": {"type": "number"},
                    "security_report": {"type": "object"}
                }
            },
            description="Formulates evidence-backed subrogation demands and rebuttals to carrier defense letters. Interacts with DLP screening gate before dispatching formal communications.",
            capabilities=[
                "Anticipated defense counter-analysis",
                "Multi-turn compromise settlement execution",
                "Evidence exhibit anchoring",
                "Pre-dispatch security validation"
            ]
        ),
        AgentManifest(
            agent_id="document-intelligence-agent",
            name="Multimodal Document Intelligence Agent",
            version="2.0.0",
            category="DATA_INGESTION",
            role="Optical EIR / BOL Ingestion, Checksum Validation & Data Quality Gate",
            model_binding=configured_model,
            framework="Google GenAI SDK",
            human_gated=False,
            requires_scopes=["documents:ingest", "documents:ocr"],
            input_schema={
                "type": "object",
                "properties": {
                    "document_bytes": {"type": "string", "format": "binary"},
                    "mime_type": {"type": "string"}
                },
                "required": ["document_bytes", "mime_type"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string"},
                    "iso_check_digit_valid": {"type": "boolean"},
                    "handover_timestamp_utc": {"type": "string"},
                    "equipment_status": {"type": "string"}
                }
            },
            description="Processes scanned Equipment Interchange Receipts (EIR), Bills of Lading (BOL), and delivery gate receipts to extract verified custody timestamps and container identifiers.",
            capabilities=[
                "Optical OCR extraction",
                "ISO 6346 checksum verification",
                "Timestamp ambiguity flagging",
                "SHA-256 payload fingerprinting"
            ]
        ),
        AgentManifest(
            agent_id="security-screening-agent",
            name="Google Model Armor & DLP Guardrail Agent",
            version="2.0.0",
            category="COMPLIANCE_AND_SECURITY",
            role="Pre-Dispatch PII, Secret, Margin & Prompt Injection Screening",
            model_binding="Rule-Engine & Google Model Armor API",
            framework="Deterministic Guardrail Engine",
            human_gated=False,
            requires_scopes=["security:screen"],
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "case_id": {"type": "string"}
                },
                "required": ["text"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "verdict": {"type": "string", "enum": ["PASS", "REVIEW", "BLOCK"]},
                    "findings_count": {"type": "integer"},
                    "suggested_sanitization": {"type": "string"}
                }
            },
            description="Inline guardrail screening preventing data leakage (SSN, payment cards, internal profit margins, API keys) and blocking adversarial prompt injections in agent outputs.",
            capabilities=[
                "Zero-Trust DLP inspection",
                "Adversarial prompt injection blocking",
                "Automated sensitive token sanitization",
                "OpenTelemetry trace sanitization"
            ]
        )
    ]

    return AgentRegistryCatalog(
        catalog_version="2.0.0",
        fleet_name="SubroGate Institutional Agent Fleet",
        total_agents=len(agents),
        environment=settings.SUBROGATE_ENV,
        agents=agents
    )
