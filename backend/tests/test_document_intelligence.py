import os
import io
import base64
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.documents import (
    ExtractionStatus,
    GateEventType,
    HandoverCondition,
    ValidationFlag,
    ExtractedEIRData,
    FieldEvidence
)
from backend.services.document_validator import ISO6346Validator, DocumentValidator
from backend.services.document_service import DocumentIntelligenceService
from backend.agents.document_agent import DocumentIntelligenceAgent
from backend.tests.fixtures.document_samples import (
    get_all_document_fixtures,
    CLEAN_EXTRACTED_DATA,
    ROTATED_EXTRACTED_DATA,
    POOR_QUALITY_EXTRACTED_DATA,
    AMBIGUOUS_EXTRACTED_DATA,
    UNREADABLE_EXTRACTED_DATA
)


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ==============================================================================
# 1. ISO 6346 CONTAINER ID CHECKSUM UNIT TESTS
# ==============================================================================

def test_iso_6346_valid_check_digits():
    # Valid real-world shipping containers with mathematical check digits
    valid_containers = [
        ("MSKU9082345", 5),
        ("CMAU7182935", 5),
        ("CSQU3054383", 3),
        ("HLXU1234561", 1)
    ]
    for cid, expected_digit in valid_containers:
        calculated = ISO6346Validator.calculate_check_digit(cid[:10])
        assert calculated == expected_digit, f"Failed on {cid}: expected {expected_digit}, got {calculated}"
        is_valid, chk_match, err = ISO6346Validator.validate(cid)
        assert is_valid is True
        assert chk_match is True
        assert err is None


def test_iso_6346_check_digit_mismatch():
    # Calculated check digit for MSKU123456 is 4, but string ends in 7
    is_valid, chk_match, err = ISO6346Validator.validate("MSKU1234567")
    assert is_valid is True
    assert chk_match is False
    assert "Check digit mismatch" in err


def test_iso_6346_malformed_formats():
    invalid_cases = [
        "",
        None,
        "12345",
        "MSKU1234",
        "MSKU1234567890",
        "12345678901",
        "MSK-908234-1"  # Needs cleaning
    ]
    for raw in invalid_cases:
        if raw == "MSK-908234-1":
            # Cleanable to MSK9082341 (10 chars, not 11)
            is_valid, chk_match, _ = ISO6346Validator.validate(raw)
            assert is_valid is False
        else:
            is_valid, chk_match, _ = ISO6346Validator.validate(raw)
            assert is_valid is False


# ==============================================================================
# 2. APPLICATION-LEVEL VALIDATION: 5 SCENARIO FIXTURES
# ==============================================================================

def test_clean_document_validation():
    """Clean EIR with valid ISO container, unambiguous EDT timestamp, and quotes passes."""
    report = DocumentValidator.validate_eir_extraction(
        extracted=CLEAN_EXTRACTED_DATA,
        expected_container_id="MSKU9082345",
        expected_carrier="Apex Drayage LLC"
    )

    assert report.status == ExtractionStatus.PASS
    assert report.requires_human_verification is False
    assert report.is_timestamp_parseable is True
    assert report.is_timezone_explicit is True
    assert report.normalized_timestamp_utc == datetime(2026, 6, 15, 18, 30, 0, tzinfo=timezone.utc)
    assert report.is_container_id_valid_iso is True
    assert report.container_id_checksum_matches is True
    assert report.matches_expected_container_id is True
    assert report.matches_expected_carrier is True
    assert report.timestamp_has_supporting_evidence is True
    assert len(report.errors) == 0


def test_rotated_document_validation():
    """Rotated EIR with 90° inspection stamp flags rotation and notes damage."""
    report = DocumentValidator.validate_eir_extraction(
        extracted=ROTATED_EXTRACTED_DATA
    )

    assert report.status == ExtractionStatus.REVIEW_REQUIRED
    assert report.requires_human_verification is True
    assert ValidationFlag.ROTATED_STAMP_EXCEPTION in report.validation_flags
    assert report.is_timestamp_parseable is True
    assert report.normalized_timestamp_utc == datetime(2026, 6, 18, 13, 15, 0, tzinfo=timezone.utc)


def test_poor_quality_document_validation():
    """Poor quality EIR with low model confidence and checksum mismatch flags review."""
    report = DocumentValidator.validate_eir_extraction(
        extracted=POOR_QUALITY_EXTRACTED_DATA
    )

    assert report.status == ExtractionStatus.REVIEW_REQUIRED
    assert report.requires_human_verification is True
    assert ValidationFlag.LOW_MODEL_CONFIDENCE in report.validation_flags
    assert ValidationFlag.CONTAINER_ID_CHECKSUM_WARNING in report.validation_flags
    assert ValidationFlag.UNREADABLE_SECTIONS in report.validation_flags


def test_ambiguous_document_validation():
    """Ambiguous EIR with missing timezone and handwritten notes flags review."""
    report = DocumentValidator.validate_eir_extraction(
        extracted=AMBIGUOUS_EXTRACTED_DATA
    )

    assert report.status == ExtractionStatus.REVIEW_REQUIRED
    assert report.requires_human_verification is True
    assert ValidationFlag.AMBIGUOUS_TIMEZONE in report.validation_flags
    assert ValidationFlag.HANDWRITING_AMBIGUITY in report.validation_flags
    assert report.is_timezone_explicit is False


def test_unreadable_document_validation():
    """Unreadable / corrupted document fails with critical field errors."""
    report = DocumentValidator.validate_eir_extraction(
        extracted=UNREADABLE_EXTRACTED_DATA
    )

    assert report.status == ExtractionStatus.FAILED
    assert report.requires_human_verification is True
    assert ValidationFlag.MISSING_CRITICAL_FIELD in report.validation_flags
    assert len(report.errors) > 0


def test_expected_container_id_mismatch_fails():
    """When extracted container does not match expected case container, status is FAILED."""
    report = DocumentValidator.validate_eir_extraction(
        extracted=CLEAN_EXTRACTED_DATA,
        expected_container_id="TCLU9999999"  # Mismatch!
    )

    assert report.status == ExtractionStatus.FAILED
    assert report.matches_expected_container_id is False
    assert ValidationFlag.CONTAINER_ID_MISMATCH in report.validation_flags


# ==============================================================================
# 3. EVIDENCE PRESERVATION & SERVICE LAYER TESTS
# ==============================================================================

def test_document_service_sha256_and_traceability():
    """Service calculates cryptographic hash and preserves field evidence mapping."""
    fixtures = get_all_document_fixtures()
    pdf_bytes, mock_data = fixtures["clean"]

    service = DocumentIntelligenceService()
    result = service.process_document(
        file_bytes=pdf_bytes,
        filename="apm_clean_eir.pdf",
        mime_type="application/pdf",
        mock_extraction=mock_data
    )

    assert result.extraction_status == ExtractionStatus.PASS
    assert result.document_metadata.filename == "apm_clean_eir.pdf"
    assert result.document_metadata.file_size_bytes == len(pdf_bytes)
    assert len(result.document_metadata.sha256_hash) == 64  # Hex SHA-256

    # Verify field evidence quotes
    extracted = result.extracted_data
    assert extracted is not None
    assert "container_id" in extracted.field_evidence_map
    cid_ev = extracted.field_evidence_map["container_id"]
    assert cid_ev.verbatim_quote is not None
    assert "MSKU9082345" in cid_ev.verbatim_quote
    assert cid_ev.is_verified is True


def test_document_service_unsupported_mime_type():
    """Service rejects invalid MIME types with FAILED status."""
    service = DocumentIntelligenceService()
    result = service.process_document(
        file_bytes=b"some text",
        filename="malicious.exe",
        mime_type="application/x-msdownload"
    )

    assert result.extraction_status == ExtractionStatus.FAILED
    assert "Unsupported MIME type" in result.validation_report.errors[0]


# ==============================================================================
# 4. FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_extract_multipart_endpoint(client):
    """Tests POST /api/documents/extract with synthetic PDF file upload."""
    fixtures = get_all_document_fixtures()
    pdf_bytes, _ = fixtures["clean"]

    files = {
        "file": ("clean_gate_receipt.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    }
    data = {
        "expected_container_id": "MSKU9082345",
        "default_timezone": "EDT"
    }

    response = client.post("/api/documents/extract", files=files, data=data)
    assert response.status_code == 200
    res_json = response.json()
    assert "document_metadata" in res_json
    assert "extraction_status" in res_json
    assert "validation_report" in res_json
    assert res_json["document_metadata"]["filename"] == "clean_gate_receipt.pdf"


def test_api_extract_base64_endpoint(client):
    """Tests POST /api/documents/extract-base64 with base64 payload."""
    fixtures = get_all_document_fixtures()
    pdf_bytes, _ = fixtures["clean"]
    b64_str = base64.b64encode(pdf_bytes).decode("utf-8")

    payload = {
        "filename": "clean_eir.pdf",
        "base64_content": b64_str,
        "mime_type": "application/pdf",
        "expected_container_id": "MSKU9082345"
    }

    response = client.post("/api/documents/extract-base64", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["document_metadata"]["filename"] == "clean_eir.pdf"


def test_api_direct_validation_endpoint(client):
    """Tests POST /api/documents/validate for direct payload re-validation."""
    payload = {
        "extracted_data": CLEAN_EXTRACTED_DATA.model_dump(),
        "expected_container_id": "MSKU9082345",
        "expected_carrier": "Apex Drayage LLC"
    }

    response = client.post("/api/documents/validate", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "PASS"
    assert res_json["requires_human_verification"] is False
    assert res_json["is_container_id_valid_iso"] is True


def test_api_empty_file_upload_rejected(client):
    """Tests that empty 0-byte file uploads are rejected with HTTP 400."""
    files = {
        "file": ("empty.pdf", io.BytesIO(b""), "application/pdf")
    }
    response = client.post("/api/documents/extract", files=files)
    assert response.status_code == 400


# ==============================================================================
# 5. LIVE MODEL INTEGRATION PATH (Conditional on API credentials)
# ==============================================================================

@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_CLOUD_PROJECT"),
    reason="Live Gemini/Vertex AI credentials not configured in environment."
)
def test_live_gemini_multimodal_extraction():
    """Live integration test against the configured Gemini model on Vertex AI / Google GenAI SDK."""
    agent = DocumentIntelligenceAgent()
    assert agent.is_online is True

    fixtures = get_all_document_fixtures()
    pdf_bytes, _ = fixtures["clean"]

    extracted = agent.extract_eir(
        document_bytes=pdf_bytes,
        mime_type="application/pdf"
    )

    assert extracted is not None
    assert extracted.container_id is not None
    assert len(extracted.field_evidence_map) > 0
