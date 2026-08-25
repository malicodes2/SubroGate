"""
SubroGate Agent Layer (Google ADK & GenAI SDK / Vertex AI Compatible)
"""
from .base import BaseForensicAgent, AgentExecutionResult
from .document_agent import DocumentIntelligenceAgent
from .investigator_agent import InvestigatorAgent, STATUTORY_SOURCES
from .settlement_agent import SettlementAgent
from .adk_tools import (
    query_carmack_statutory_precedent,
    verify_iso_6346_check_digit,
    calculate_custody_breach_overlap,
    ADK_TOOL_DECLARATIONS
)

__all__ = [
    "BaseForensicAgent",
    "AgentExecutionResult",
    "DocumentIntelligenceAgent",
    "InvestigatorAgent",
    "STATUTORY_SOURCES",
    "SettlementAgent",
    "query_carmack_statutory_precedent",
    "verify_iso_6346_check_digit",
    "calculate_custody_breach_overlap",
    "ADK_TOOL_DECLARATIONS"
]
