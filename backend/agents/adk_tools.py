"""
SubroGate Google Agent Development Kit (ADK) & Vertex AI Agent Tools Library.
Declarative agent tools, schemas, and runners for Google GenAI / Vertex AI Agent orchestration.
"""
import re
import json
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field

# ==============================================================================
# TOOL 1: STATUTORY CARMACK & UIIA LEGAL PRECEDENT TOOL
# ==============================================================================

class CarmackPrecedentInput(BaseModel):
    doctrine_type: str = Field(
        ...,
        description="The legal doctrine to query: 'STRICT_LIABILITY', 'PRIMA_FACIE_STANDARD', 'CARMACK_EXCEPTIONS', or 'UIIA_CUSTODY'"
    )

def query_carmack_statutory_precedent(doctrine_type: str) -> Dict[str, Any]:
    """
    Google ADK Tool: Queries federal statutory precedent and burden-of-proof rules
    under 49 U.S.C. § 14706 (Carmack Amendment) and the UIIA Agreement.
    """
    doctrines = {
        "STRICT_LIABILITY": {
            "statute": "49 U.S.C. § 14706",
            "principle": "Interstate motor carriers are strictly liable for actual loss or injury to cargo during transit under a bill of lading.",
            "leading_case": "Missouri Pacific R. Co. v. Elmore & Stahl, 377 U.S. 134 (1964)",
            "burden": "Once prima facie damage is established, the burden shifts entirely to the carrier to prove freedom from negligence and an affirmative statutory defense."
        },
        "PRIMA_FACIE_STANDARD": {
            "statute": "49 U.S.C. § 14706",
            "three_prongs": [
                "1. Delivery to carrier in good condition (established by clean EIR / BOL without exception).",
                "2. Arrival at destination in damaged condition (established by delivery receipt / sensor breach).",
                "3. Specified amount of damages (commercial invoice / certified destruction value)."
            ]
        },
        "CARMACK_EXCEPTIONS": {
            "statute": "49 U.S.C. § 14706",
            "five_exclusive_defenses": [
                "1. Act of God",
                "2. Public Enemy",
                "3. Act of Shipper / Inherent Vice",
                "4. Public Authority / Quarantine",
                "5. Inherent Vice of Cargo"
            ],
            "rule": "General denials or third-party excuses do not satisfy the five statutory exceptions."
        },
        "UIIA_CUSTODY": {
            "statute": "Uniform Intermodal Interchange Agreement (UIIA Section E.2)",
            "principle": "Motor carrier assumes continuous Care, Custody, and Control (CCC) upon gate-out interchange and remains strictly responsible until interchange back to facility."
        }
    }
    return doctrines.get(doctrine_type.upper(), doctrines["STRICT_LIABILITY"])


# ==============================================================================
# TOOL 2: ISO 6346 CONTAINER CHECK-DIGIT VERIFIER TOOL
# ==============================================================================

class ContainerVerifyInput(BaseModel):
    container_id: str = Field(..., description="11-character ISO container number (e.g. MSKU9082345)")

def verify_iso_6346_check_digit(container_id: str) -> Dict[str, Any]:
    """
    Google ADK Tool: Mathematically computes and validates the ISO 6346 Modulo-11
    check digit for standard intermodal freight containers.
    """
    clean_id = re.sub(r'[^A-Z0-9]', '', container_id.upper())
    if len(clean_id) != 11:
        return {
            "container_id": container_id,
            "valid": False,
            "error": f"Invalid length {len(clean_id)}, expected exactly 11 characters."
        }

    letter_values = {
        'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18, 'I': 19, 'J': 20,
        'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27, 'Q': 28, 'R': 29, 'S': 30, 'T': 31,
        'U': 32, 'V': 34, 'W': 35, 'X': 36, 'Y': 37, 'Z': 38
    }

    try:
        total = 0
        for i in range(10):
            char = clean_id[i]
            val = letter_values[char] if char in letter_values else int(char)
            total += val * (2 ** i)

        calculated = total % 11
        if calculated == 10:
            calculated = 0

        actual = int(clean_id[10])
        is_valid = (calculated == actual)

        return {
            "container_id": clean_id,
            "owner_code": clean_id[:3],
            "category": clean_id[3],
            "serial_number": clean_id[4:10],
            "actual_check_digit": actual,
            "calculated_check_digit": calculated,
            "valid": is_valid
        }
    except Exception as e:
        return {"container_id": container_id, "valid": False, "error": str(e)}


# ==============================================================================
# TOOL 3: TEMPORAL CUSTODY OVERLAP CALCULATOR
# ==============================================================================

class CustodyOverlapInput(BaseModel):
    handover_timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp of origin custody interchange")
    breach_timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp of earliest sensor excursion")

def calculate_custody_breach_overlap(
    handover_timestamp_utc: str,
    breach_timestamp_utc: str
) -> Dict[str, Any]:
    """
    Google ADK Tool: Deterministically calculates whether the physical sensor breach
    occurred prior to origin handover (shipper liability) or post-interchange (carrier liability).
    """
    from datetime import datetime

    try:
        handover_dt = datetime.fromisoformat(handover_timestamp_utc.replace("Z", "+00:00"))
        breach_dt = datetime.fromisoformat(breach_timestamp_utc.replace("Z", "+00:00"))

        diff_seconds = (breach_dt - handover_dt).total_seconds()
        diff_hours = diff_seconds / 3600.0

        if breach_dt > handover_dt:
            responsible_party = "RECEIVING_MOTOR_CARRIER"
            confidence = 0.94
            explanation = f"Breach initiated {diff_hours:.2f} hours AFTER signed origin interchange. Custody resided with receiving motor carrier."
        else:
            responsible_party = "ORIGIN_SHIPPER"
            confidence = 0.90
            explanation = f"Breach initiated {abs(diff_hours):.2f} hours BEFORE origin interchange. Cargo was pre-damaged prior to carrier receipt."

        return {
            "handover_utc": handover_dt.isoformat(),
            "breach_utc": breach_dt.isoformat(),
            "breach_post_handover": breach_dt > handover_dt,
            "temporal_delta_hours": diff_hours,
            "attributed_custodian": responsible_party,
            "confidence": confidence,
            "explanation": explanation
        }
    except Exception as e:
        return {"error": f"Failed to compute temporal overlap: {str(e)}"}


# ==============================================================================
# ADK DECLARATIVE TOOL SCHEMA EXPORT & REGISTRY
# ==============================================================================

ADK_TOOL_DECLARATIONS = [
    {
        "name": "query_carmack_statutory_precedent",
        "description": "Queries federal statutory precedent and burden-of-proof rules under 49 U.S.C. § 14706 (Carmack Amendment).",
        "parameters": {
            "type": "object",
            "properties": {
                "doctrine_type": {
                    "type": "string",
                    "enum": ["STRICT_LIABILITY", "PRIMA_FACIE_STANDARD", "CARMACK_EXCEPTIONS", "UIIA_CUSTODY"],
                    "description": "The legal doctrine to query"
                }
            },
            "required": ["doctrine_type"]
        }
    },
    {
        "name": "verify_iso_6346_check_digit",
        "description": "Mathematically computes and validates the ISO 6346 Modulo-11 check digit for intermodal containers.",
        "parameters": {
            "type": "object",
            "properties": {
                "container_id": {
                    "type": "string",
                    "description": "11-character container identifier"
                }
            },
            "required": ["container_id"]
        }
    },
    {
        "name": "calculate_custody_breach_overlap",
        "description": "Calculates whether sensor breach occurred prior to or post origin custody interchange.",
        "parameters": {
            "type": "object",
            "properties": {
                "handover_timestamp_utc": {"type": "string", "description": "UTC ISO 8601 handover timestamp"},
                "breach_timestamp_utc": {"type": "string", "description": "UTC ISO 8601 earliest breach timestamp"}
            },
            "required": ["handover_timestamp_utc", "breach_timestamp_utc"]
        }
    }
]


class ADKToolRegistry:
    """
    Formal Google Agent Development Kit (ADK) Tool Registry.
    Binds declarative function schemas to runtime Python callables for Gemini models.
    """
    _TOOL_MAP: Dict[str, Callable] = {
        "query_carmack_statutory_precedent": query_carmack_statutory_precedent,
        "verify_iso_6346_check_digit": verify_iso_6346_check_digit,
        "calculate_custody_breach_overlap": calculate_custody_breach_overlap,
    }

    @classmethod
    def get_registered_callables(cls) -> List[Callable]:
        """Returns all callable tools for direct binding to google.genai or Vertex AI."""
        return list(cls._TOOL_MAP.values())

    @classmethod
    def get_declarations(cls) -> List[Dict[str, Any]]:
        """Returns JSON schema declarations for Google GenAI tool manifests."""
        return ADK_TOOL_DECLARATIONS

    @classmethod
    def execute_tool(cls, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a registered tool by name with provided arguments."""
        if tool_name not in cls._TOOL_MAP:
            return {"error": f"Tool '{tool_name}' is not registered in ADK Tool Registry."}
        try:
            func = cls._TOOL_MAP[tool_name]
            return func(**arguments)
        except Exception as e:
            return {"error": f"Tool execution error on '{tool_name}': {str(e)}"}
