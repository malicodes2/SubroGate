import re
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, Any
import dateutil.parser
import dateutil.tz

# Known timezone mapping with exact UTC offsets
TZ_ABBREVIATIONS = {
    "UTC": dateutil.tz.tzutc(),
    "GMT": dateutil.tz.tzutc(),
    "Z": dateutil.tz.tzutc(),
    # US Timezones (Standard vs Daylight)
    "EST": dateutil.tz.tzoffset("EST", -5 * 3600),
    "EDT": dateutil.tz.tzoffset("EDT", -4 * 3600),
    "CST": dateutil.tz.tzoffset("CST", -6 * 3600),
    "CDT": dateutil.tz.tzoffset("CDT", -5 * 3600),
    "MST": dateutil.tz.tzoffset("MST", -7 * 3600),
    "MDT": dateutil.tz.tzoffset("MDT", -6 * 3600),
    "PST": dateutil.tz.tzoffset("PST", -8 * 3600),
    "PDT": dateutil.tz.tzoffset("PDT", -7 * 3600),
    # Europe
    "WET": dateutil.tz.tzoffset("WET", 0),
    "WEST": dateutil.tz.tzoffset("WEST", 1 * 3600),
    "CET": dateutil.tz.tzoffset("CET", 1 * 3600),
    "CEST": dateutil.tz.tzoffset("CEST", 2 * 3600),
    "EET": dateutil.tz.tzoffset("EET", 2 * 3600),
    "EEST": dateutil.tz.tzoffset("EEST", 3 * 3600),
    "BST": dateutil.tz.tzoffset("BST", 1 * 3600),
    # Asia / Pacific
    "IST": dateutil.tz.tzoffset("IST", 5.5 * 3600),
    "JST": dateutil.tz.tzoffset("JST", 9 * 3600),
    "KST": dateutil.tz.tzoffset("KST", 9 * 3600),
    "SGT": dateutil.tz.tzoffset("SGT", 8 * 3600),
    "AEST": dateutil.tz.tzoffset("AEST", 10 * 3600),
    "AEDT": dateutil.tz.tzoffset("AEDT", 11 * 3600),
}

# Regex to detect if an explicit offset or timezone token is present
OFFSET_REGEX = re.compile(
    r'(Z|UTC|GMT|[+-]\d{2}:?\d{2}|[+-]\d{2}|[A-Z]{3,4}$|\b[A-Za-z]+/[A-Za-z_]+\b)',
    re.IGNORECASE
)

class TimestampNormalizer:
    """
    Deterministic timestamp normalizer.
    Converts timestamps to UTC, strictly preserves raw values,
    and flags records missing timezone information for human verification.
    """

    @classmethod
    def normalize(
        cls,
        raw_val: Any,
        default_timezone: Optional[str] = None
    ) -> Tuple[Optional[datetime], bool, Optional[str]]:
        """
        Parses raw timestamp and returns:
        (timestamp_utc, requires_human_verification, verification_reason)
        """
        if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
            return None, True, "Missing timestamp value"

        # If already a datetime
        if isinstance(raw_val, datetime):
            if raw_val.tzinfo is None:
                if default_timezone:
                    tz = cls._resolve_tz(default_timezone)
                    if tz:
                        dt = raw_val.replace(tzinfo=tz).astimezone(timezone.utc)
                        return dt, False, None
                return raw_val.replace(tzinfo=timezone.utc), True, "Datetime object missing explicit tzinfo (assumed UTC for computation, flagged for verification)"
            return raw_val.astimezone(timezone.utc), False, None

        val_str = str(raw_val).strip()

        # Check for UNIX epoch (numeric string)
        if re.match(r'^\d{10}(\.\d+)?$', val_str):
            try:
                dt = datetime.fromtimestamp(float(val_str), tz=timezone.utc)
                return dt, False, None
            except Exception:
                return None, True, f"Invalid UNIX timestamp: '{val_str}'"
        elif re.match(r'^\d{13}$', val_str): # Milliseconds epoch
            try:
                dt = datetime.fromtimestamp(float(val_str) / 1000.0, tz=timezone.utc)
                return dt, False, None
            except Exception:
                return None, True, f"Invalid UNIX millisecond timestamp: '{val_str}'"

        # Check for presence of timezone token in string
        has_tz_indicator = bool(OFFSET_REGEX.search(val_str))

        try:
            # Parse with dateutil
            parsed_dt = dateutil.parser.parse(val_str, tzinfos=TZ_ABBREVIATIONS)
        except Exception as e:
            return None, True, f"Malformed timestamp '{val_str}': {str(e)}"

        if parsed_dt.tzinfo is not None:
            # Explicit timezone was found and parsed
            utc_dt = parsed_dt.astimezone(timezone.utc)
            return utc_dt, False, None

        # No timezone found in parsed string
        if default_timezone:
            tz = cls._resolve_tz(default_timezone)
            if tz:
                utc_dt = parsed_dt.replace(tzinfo=tz).astimezone(timezone.utc)
                return utc_dt, False, None

        # STRICT PRINCIPLE: Never guess a timezone silently.
        # Fallback to interpreting as UTC for interval math but flag explicitly for human verification.
        utc_dt = parsed_dt.replace(tzinfo=timezone.utc)
        return utc_dt, True, f"Missing explicit timezone in timestamp '{val_str}'. Flagged for human verification."

    @classmethod
    def _resolve_tz(cls, tz_str: str) -> Optional[Any]:
        """Resolves timezone name, abbreviation, or IANA string."""
        if not tz_str:
            return None
        upper_tz = tz_str.strip().upper()
        if upper_tz in TZ_ABBREVIATIONS:
            return TZ_ABBREVIATIONS[upper_tz]
        try:
            return dateutil.tz.gettz(tz_str.strip())
        except Exception:
            return None
