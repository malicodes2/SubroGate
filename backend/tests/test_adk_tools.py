import pytest
from backend.agents.adk_tools import (
    query_carmack_statutory_precedent,
    verify_iso_6346_check_digit,
    calculate_custody_breach_overlap,
    ADK_TOOL_DECLARATIONS
)

def test_query_carmack_statutory_precedent():
    res = query_carmack_statutory_precedent("STRICT_LIABILITY")
    assert "49 U.S.C. § 14706" in res["statute"]
    assert "Missouri Pacific" in res["leading_case"]

    exceptions = query_carmack_statutory_precedent("CARMACK_EXCEPTIONS")
    assert len(exceptions["five_exclusive_defenses"]) == 5

def test_verify_iso_6346_check_digit():
    # Valid container MSKU9082345: actual check digit is 5
    res = verify_iso_6346_check_digit("MSKU9082345")
    assert res["valid"] is True
    assert res["actual_check_digit"] == 5

    # Invalid container checksum
    bad_res = verify_iso_6346_check_digit("MSKU9082349")
    assert bad_res["valid"] is False

def test_calculate_custody_breach_overlap():
    handover = "2026-08-15T15:00:00Z"
    breach_after = "2026-08-15T17:15:00Z"
    res = calculate_custody_breach_overlap(handover, breach_after)
    assert res["breach_post_handover"] is True
    assert res["attributed_custodian"] == "RECEIVING_MOTOR_CARRIER"

    breach_before = "2026-08-15T13:00:00Z"
    res_before = calculate_custody_breach_overlap(handover, breach_before)
    assert res_before["breach_post_handover"] is False
    assert res_before["attributed_custodian"] == "ORIGIN_SHIPPER"

def test_adk_tool_declarations_schema():
    assert len(ADK_TOOL_DECLARATIONS) >= 3
    tool_names = [t["name"] for t in ADK_TOOL_DECLARATIONS]
    assert "query_carmack_statutory_precedent" in tool_names
    assert "verify_iso_6346_check_digit" in tool_names
    assert "calculate_custody_breach_overlap" in tool_names
