"""
Time Synchronization Module — TANTRA Trace Lock (Phase 8)

Ensures all timestamps across the trace spine are:
 - Normalized to UTC (no local time)
 - ISO 8601 formatted
 - Monotonically orderable

Rules:
 - No local time inconsistencies
 - No drift across layers
 - All layers use this single source of truth for time
"""

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def get_normalized_timestamp() -> str:
    """
    Generate a UTC-normalized ISO 8601 timestamp.
    
    This is the ONLY sanctioned way to generate timestamps
    within the TANTRA trace spine. All layers MUST use this.
    
    Returns:
        ISO 8601 UTC timestamp string (e.g., '2026-04-20T09:02:51.123456+00:00')
    """
    return datetime.now(timezone.utc).isoformat()


def compare_timestamps(ts_a: str, ts_b: str) -> int:
    """
    Compare two ISO 8601 timestamps for monotonic ordering.
    
    Args:
        ts_a: First timestamp (ISO 8601)
        ts_b: Second timestamp (ISO 8601)
    
    Returns:
        -1 if ts_a < ts_b (a is earlier)
         0 if ts_a == ts_b
         1 if ts_a > ts_b (a is later)
    """
    dt_a = datetime.fromisoformat(ts_a)
    dt_b = datetime.fromisoformat(ts_b)
    
    if dt_a < dt_b:
        return -1
    elif dt_a > dt_b:
        return 1
    return 0


def validate_timestamp_ordering(timestamps: list) -> bool:
    """
    Validate that a list of timestamps is in strictly non-decreasing order.
    Used to verify trace ordering integrity.
    
    Args:
        timestamps: List of ISO 8601 timestamp strings
    
    Returns:
        True if timestamps are monotonically non-decreasing
    """
    if len(timestamps) < 2:
        return True
    
    for i in range(1, len(timestamps)):
        if compare_timestamps(timestamps[i - 1], timestamps[i]) > 0:
            logger.error(
                f"Timestamp ordering violation: {timestamps[i-1]} > {timestamps[i]}"
            )
            return False
    return True


def parse_to_utc(timestamp_str: str) -> datetime:
    """
    Parse an ISO 8601 timestamp string and ensure it is in UTC.
    
    Args:
        timestamp_str: ISO 8601 timestamp string
    
    Returns:
        datetime object in UTC timezone
    """
    dt = datetime.fromisoformat(timestamp_str)
    if dt.tzinfo is None:
        # Treat naive datetimes as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
