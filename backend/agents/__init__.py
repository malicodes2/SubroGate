"""
SubroGate Agent Layer (Google ADK & Vertex AI / GenAI SDK Compatible)
"""
from .base import BaseForensicAgent, AgentExecutionResult
from .document_agent import DocumentIntelligenceAgent
from .investigator_agent import InvestigatorAgent, STATUTORY_SOURCES
from .settlement_agent import SettlementAgent

__all__ = [
    "BaseForensicAgent",
    "AgentExecutionResult",
    "DocumentIntelligenceAgent",
    "InvestigatorAgent",
    "STATUTORY_SOURCES",
    "SettlementAgent"
]
