import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from ..models.documents import (
    ExtractedEIRData,
    DocumentValidationReport,
    ExtractionStatus,
    ValidationFlag,
    HandoverCondition
)
from .timestamp_normalizer import TimestampNormalizer

# ISO 6346 character-to-number mapping table
# Multiples of 11 (11, 22, 33) are intentionally omitted per standard
ISO_6346_LETTER_MAP = {
    'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18, 'I': 19, 'J': 20,
    'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27, 'Q': 28, 'R': 29, 'S': 30, 'T': 31,
    'U': 32, 'V': 34, 'W': 35, 'X': 36, 'Y': 37, 'Z': 38
}

ISO_CONTAINER_REGEX = re.compile(r'^[A-Z]{4}\d{7}$')


class ISO6346Validator:
    """
    Deterministic ISO 6346 intermodal freight container identifier validator.
    Computes standard modulo 11 check digit verification.
    """

    @classmethod
    def clean_container_id(cls, raw_id: Optional[str]) -> Optional[str]:
        if not raw_id:
            return None
        # Strip whitespace, hyphens, and common punctuation
        clean = re.sub(r'[^A-Za-z0-9]', '', raw_id).upper()
        return clean if clean else None

    @classmethod
    def calculate_check_digit(cls, prefix_and_serial: str) -> Optional[int]:
        """
        Calculates the ISO 6346 check digit for the first 10 characters (4 letters + 6 digits).
        """
        if len(prefix_and_serial) < 10:
            return None

        clean_10 = prefix_and_serial[:10].upper()
        total_sum = 0

        for i, char in enumerate(clean_10):
            if char.isalpha():
                val = ISO_6346_LETTER_MAP.get(char)
                if val is None:
                    return None
            elif char.isdigit():
                val = int(char)
            else:
                return None

            weight = 2 ** i
            total_sum += val * weight

        remainder = total_sum % 11
        check_digit = remainder % 10  # Remainder 10 becomes 0 per ISO standard
        return check_digit

    @classmethod
    def validate(cls, container_id: Optional[str]) -> Tuple[bool, bool, Optional[str]]:
        """
        Validates container ID. Returns:
        (is_valid_iso_format, checksum_matches, error_reason)
        """
        cleaned = cls.clean_container_id(container_id)
        if not cleaned:
            return False, False, "Missing container ID"

        if len(cleaned) != 11 or not ISO_CONTAINER_REGEX.match(cleaned):
            return False, False, f"Container ID '{cleaned}' does not match standard 4-letter + 7-digit ISO format"

        expected_digit = cls.calculate_check_digit(cleaned[:10])
        actual_digit = int(cleaned[10])

        if expected_digit is None:
            return True, False, "Unable to compute ISO 6346 check digit"

        if expected_digit != actual_digit:
            return True, False, f"Check digit mismatch: calculated {expected_digit}, document contains {actual_digit}"

        return True, True, None


class DocumentValidator:
    """
    Deterministic application-level validator for extracted EIR documents.
    Applies multi-rule validation to produce PASS, REVIEW_REQUIRED, or FAILED.
    """

    @classmethod
    def validate_eir_extraction(
        cls,
        extracted: Optional[ExtractedEIRData],
        expected_container_id: Optional[str] = None,
        expected_carrier: Optional[str] = None,
        default_timezone: Optional[str] = None
    ) -> DocumentValidationReport:
        """
        Evaluates extracted document data against business rules and data integrity checks.
        """
        if extracted is None:
            return DocumentValidationReport(
                status=ExtractionStatus.FAILED,
                requires_human_verification=True,
                validation_flags=[ValidationFlag.MISSING_CRITICAL_FIELD],
                errors=["Extraction returned null data payload."],
                warnings=[],
                is_timestamp_parseable=False,
                is_timezone_explicit=False,
                is_container_id_valid_iso=False,
                container_id_checksum_matches=False,
                timestamp_has_supporting_evidence=False
            )

        flags: List[ValidationFlag] = []
        errors: List[str] = []
        warnings: List[str] = []

        # ======================================================================
        # 1. TIMESTAMP & TIMEZONE VALIDATION
        # ======================================================================
        is_timestamp_parseable = False
        normalized_timestamp_utc: Optional[datetime] = None
        is_timezone_explicit = False
        timestamp_has_supporting_evidence = False

        if not extracted.raw_timestamp_str or not extracted.raw_timestamp_str.strip():
            errors.append("No gate handover timestamp could be extracted from the document.")
            flags.append(ValidationFlag.MISSING_CRITICAL_FIELD)
        else:
            raw_ts = extracted.raw_timestamp_str.strip()
            # Parse with deterministic TimestampNormalizer
            dt, req_verify, reason = TimestampNormalizer.normalize(
                raw_ts,
                default_timezone=default_timezone
            )

            if dt is not None:
                is_timestamp_parseable = True
                normalized_timestamp_utc = dt
                if req_verify:
                    # Missing explicit timezone in the document
                    is_timezone_explicit = False
                    flags.append(ValidationFlag.AMBIGUOUS_TIMEZONE)
                    warnings.append(
                        f"Timestamp '{raw_ts}' lacks explicit timezone identifier. "
                        f"Assumed UTC/default, but requires human verification."
                    )
                else:
                    is_timezone_explicit = True
            else:
                errors.append(f"Failed to parse extracted timestamp '{raw_ts}': {reason}")
                flags.append(ValidationFlag.TIMESTAMP_PARSE_FAILURE)

            # Check if timestamp has supporting verbatim evidence quote
            ts_evidence = extracted.field_evidence_map.get("raw_timestamp_str") or extracted.field_evidence_map.get("timestamp")
            if ts_evidence and ts_evidence.verbatim_quote:
                # Verbatim quote exists
                clean_quote = ts_evidence.verbatim_quote.lower()
                clean_ts = raw_ts.lower()
                # Check for token overlap
                ts_tokens = [t for t in re.split(r'[\s:T\-\/]+', clean_ts) if len(t) >= 2]
                if any(tok in clean_quote for tok in ts_tokens):
                    timestamp_has_supporting_evidence = True
                    ts_evidence.is_verified = True
                else:
                    flags.append(ValidationFlag.UNSUPPORTED_TIMESTAMP_EVIDENCE)
                    warnings.append("Extracted timestamp does not appear in supporting verbatim text quote.")
            else:
                flags.append(ValidationFlag.MISSING_EVIDENCE_QUOTE)
                warnings.append("Missing verbatim text quote for extracted timestamp.")

        # ======================================================================
        # 2. CONTAINER ID & ISO 6346 VALIDATION
        # ======================================================================
        is_container_id_valid_iso = False
        container_id_checksum_matches = False
        matches_expected_container_id: Optional[bool] = None

        if not extracted.container_id or not extracted.container_id.strip():
            errors.append("No container ID was identified in the document.")
            flags.append(ValidationFlag.MISSING_CRITICAL_FIELD)
        else:
            raw_cid = extracted.container_id.strip()
            is_valid_format, chk_match, chk_reason = ISO6346Validator.validate(raw_cid)
            is_container_id_valid_iso = is_valid_format
            container_id_checksum_matches = chk_match

            if not is_valid_format:
                flags.append(ValidationFlag.INVALID_CONTAINER_FORMAT)
                warnings.append(f"Container ID '{raw_cid}' is not standard ISO 6346 format: {chk_reason}")
            elif not chk_match:
                flags.append(ValidationFlag.CONTAINER_ID_CHECKSUM_WARNING)
                warnings.append(f"Container ID check digit warning: {chk_reason}")

            # Verify evidence quote for container ID
            cid_evidence = extracted.field_evidence_map.get("container_id")
            if cid_evidence and cid_evidence.verbatim_quote:
                cleaned_cid = ISO6346Validator.clean_container_id(raw_cid) or raw_cid
                if cleaned_cid.lower() in cid_evidence.verbatim_quote.lower() or raw_cid.lower() in cid_evidence.verbatim_quote.lower():
                    cid_evidence.is_verified = True

            # Match against expected case container ID if provided
            if expected_container_id:
                clean_expected = ISO6346Validator.clean_container_id(expected_container_id) or expected_container_id.strip().upper()
                clean_extracted = ISO6346Validator.clean_container_id(raw_cid) or raw_cid.strip().upper()
                if clean_extracted == clean_expected:
                    matches_expected_container_id = True
                else:
                    matches_expected_container_id = False
                    flags.append(ValidationFlag.CONTAINER_ID_MISMATCH)
                    errors.append(
                        f"Extracted container ID '{clean_extracted}' does not match expected case container ID '{clean_expected}'."
                    )

        # ======================================================================
        # 3. CARRIER & ENTITY VALIDATION
        # ======================================================================
        matches_expected_carrier: Optional[bool] = None
        if not extracted.carrier_name and not extracted.releasing_entity and not extracted.receiving_entity:
            warnings.append("No carrier, releasing party, or receiving party was identified.")
            flags.append(ValidationFlag.CARRIER_UNKNOWN)
        elif expected_carrier:
            extracted_carrier_text = f"{extracted.carrier_name or ''} {extracted.releasing_entity or ''} {extracted.receiving_entity or ''}".lower()
            clean_expected_carrier = expected_carrier.strip().lower()
            carrier_tokens = [t for t in clean_expected_carrier.split() if len(t) > 2]

            if any(tok in extracted_carrier_text for tok in carrier_tokens):
                matches_expected_carrier = True
            else:
                matches_expected_carrier = False
                flags.append(ValidationFlag.CARRIER_MISMATCH)
                warnings.append(
                    f"Identified carrier '{extracted.carrier_name}' does not match expected party '{expected_carrier}'."
                )

        # ======================================================================
        # 4. HANDWRITING, ROTATION, AND UNREADABLE SECTIONS AUDIT
        # ======================================================================
        if extracted.unreadable_sections:
            flags.append(ValidationFlag.UNREADABLE_SECTIONS)
            warnings.append(f"Document contains {len(extracted.unreadable_sections)} illegible/unreadable sections.")

        if extracted.handwritten_notes:
            flags.append(ValidationFlag.HANDWRITING_AMBIGUITY)
            warnings.append(f"Detected {len(extracted.handwritten_notes)} handwritten annotations requiring adjuster verification.")

        # Check for rotated stamps or damage stamps
        if extracted.stamps_detected:
            for stamp in extracted.stamps_detected:
                stamp_text = str(stamp.get("text", "")).lower()
                rotation = stamp.get("rotation_deg", 0)
                if rotation in (90, 180, 270):
                    flags.append(ValidationFlag.ROTATED_STAMP_EXCEPTION)
                if any(kw in stamp_text for kw in ["damaged", "exception", "broken", "rejected", "wet"]):
                    if extracted.condition_summary == HandoverCondition.CLEAN:
                        flags.append(ValidationFlag.CONFLICTING_CONDITION_EVIDENCE)
                        warnings.append(f"Document has stamp '{stamp.get('text')}' but condition is recorded as CLEAN.")

        # Check model self-confidence threshold
        for field_name, ev in extracted.field_evidence_map.items():
            if ev.confidence < 0.65:
                flags.append(ValidationFlag.LOW_MODEL_CONFIDENCE)
                warnings.append(f"Low extraction confidence ({ev.confidence:.2f}) on field '{field_name}'.")

        # ======================================================================
        # 5. SYNTHESIZE FINAL VALIDATION STATUS (PASS, REVIEW_REQUIRED, FAILED)
        # ======================================================================
        # FAILED criteria:
        # - Complete failure to extract timestamp OR container ID
        # - Fatal error that makes document unusable for legal audit
        # - Expected container ID mismatch
        if not is_timestamp_parseable or not extracted.container_id or matches_expected_container_id is False:
            final_status = ExtractionStatus.FAILED
            requires_human_verification = True
        # REVIEW_REQUIRED criteria:
        # - Ambiguous timezone (missing timezone offset)
        # - Container ID check digit warning or non-ISO format
        # - Unreadable sections, handwritten notes, conflicting stamps
        # - Missing evidence quote for timestamp
        # - Any non-blocking warnings
        elif (
            not is_timezone_explicit
            or not is_container_id_valid_iso
            or not container_id_checksum_matches
            or not timestamp_has_supporting_evidence
            or len(warnings) > 0
            or len(flags) > 0
        ):
            final_status = ExtractionStatus.REVIEW_REQUIRED
            requires_human_verification = True
        else:
            # PASS criteria:
            # - Timestamp parseable with explicit timezone & supporting evidence
            # - ISO-6346 Container ID passes checksum
            # - No critical warnings or ambiguities
            final_status = ExtractionStatus.PASS
            requires_human_verification = False

        # Deduplicate flags
        unique_flags = list(dict.fromkeys(flags))

        return DocumentValidationReport(
            status=final_status,
            requires_human_verification=requires_human_verification,
            validation_flags=unique_flags,
            errors=errors,
            warnings=warnings,
            is_timestamp_parseable=is_timestamp_parseable,
            normalized_timestamp_utc=normalized_timestamp_utc,
            is_timezone_explicit=is_timezone_explicit,
            is_container_id_valid_iso=is_container_id_valid_iso,
            container_id_checksum_matches=container_id_checksum_matches,
            matches_expected_container_id=matches_expected_container_id,
            matches_expected_carrier=matches_expected_carrier,
            timestamp_has_supporting_evidence=timestamp_has_supporting_evidence
        )
