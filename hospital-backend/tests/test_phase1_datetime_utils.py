"""
Phase 1 Tests: Datetime Utilities
Tests for app/common/datetime/ modules

These tests validate:
1. ISO8601 timestamp parsing with timezone handling
2. Timezone-aware datetime formatting
3. Relative time formatting
4. Medical format timestamps
5. Core datetime utilities (now_utc, seconds_since, is_recent)

Related Files:
- hospital-backend/app/common/datetime/parser.py
- hospital-backend/app/common/datetime/formatter.py
- hospital-backend/app/common/datetime/utils.py
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.common.datetime.parser import parse_iso8601, parse_timestamp
from app.common.datetime.formatter import to_iso8601, format_relative, format_medical
from app.common.datetime.utils import now_utc, seconds_since, is_recent


@pytest.mark.unit
class TestDatetimeParser:
    """Test datetime parsing functions"""

    def test_parse_iso8601_with_z_suffix(self):
        """
        Test: Parse ISO8601 timestamp with Z suffix
        Expected: Returns timezone-aware UTC datetime
        """
        timestamp = "2025-01-10T14:30:00Z"
        result = parse_iso8601(timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 10
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_iso8601_with_offset(self):
        """
        Test: Parse ISO8601 timestamp with timezone offset
        Expected: Returns timezone-aware datetime with correct offset
        """
        timestamp = "2025-01-10T14:30:00+05:30"  # IST
        result = parse_iso8601(timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.year == 2025

    def test_parse_iso8601_without_timezone_assumes_utc(self):
        """
        Test: Parse ISO8601 timestamp without timezone
        Expected: Assumes UTC timezone
        """
        timestamp = "2025-01-10T14:30:00"
        result = parse_iso8601(timestamp)

        assert result.tzinfo == timezone.utc

    def test_parse_iso8601_with_milliseconds(self):
        """
        Test: Parse ISO8601 with milliseconds
        Expected: Correctly parses microseconds
        """
        timestamp = "2025-01-10T14:30:00.123456Z"
        result = parse_iso8601(timestamp)

        assert result.microsecond == 123456

    def test_parse_timestamp_with_numeric_timestamp(self):
        """
        Test: Parse Unix timestamp (numeric)
        Expected: Returns datetime from timestamp
        """
        timestamp = 1704895800  # 2024-01-10 14:30:00 UTC
        result = parse_timestamp(timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_parse_timestamp_with_string_timestamp(self):
        """
        Test: Parse string ISO8601 timestamp
        Expected: Returns parsed datetime
        """
        timestamp = "2025-01-10T14:30:00Z"
        result = parse_timestamp(timestamp)

        assert isinstance(result, datetime)
        assert result.year == 2025


@pytest.mark.unit
class TestDatetimeFormatter:
    """Test datetime formatting functions"""

    def test_to_iso8601_returns_z_suffix(self):
        """
        Test: Format datetime to ISO8601 with Z suffix
        Expected: Returns string ending with 'Z'
        """
        dt = datetime(2025, 1, 10, 14, 30, 0, tzinfo=timezone.utc)
        result = to_iso8601(dt)

        assert isinstance(result, str)
        assert result.endswith('Z')
        assert '2025-01-10' in result
        assert '14:30:00' in result

    def test_format_relative_just_now(self):
        """
        Test: Format recent datetime as "Just now"
        Expected: Returns "Just now" for < 60 seconds
        """
        recent_dt = datetime.now(timezone.utc) - timedelta(seconds=30)
        result = format_relative(recent_dt)

        assert result == "Just now"

    def test_format_relative_minutes_ago(self):
        """
        Test: Format datetime as "Xm ago"
        Expected: Returns "Nm ago"
        """
        dt = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = format_relative(dt)

        assert "m ago" in result
        assert "5m ago" == result

    def test_format_relative_hours_ago(self):
        """
        Test: Format datetime as "Xh ago"
        Expected: Returns "Nh ago"
        """
        dt = datetime.now(timezone.utc) - timedelta(hours=2)
        result = format_relative(dt)

        assert "h ago" in result
        assert "2h ago" == result

    def test_format_relative_days_ago(self):
        """
        Test: Format datetime as "Xd ago"
        Expected: Returns "Nd ago"
        """
        dt = datetime.now(timezone.utc) - timedelta(days=3)
        result = format_relative(dt)

        assert "d ago" in result
        assert "3d ago" == result

    def test_format_medical_includes_date_and_time(self):
        """
        Test: Format medical timestamp
        Expected: Returns "YYYY-MM-DD HH:MM:SS UTC" format
        """
        dt = datetime(2025, 1, 10, 14, 30, 0, tzinfo=timezone.utc)
        result = format_medical(dt)

        assert "2025-01-10" in result
        assert "14:30:00" in result
        assert "UTC" in result
        assert result == "2025-01-10 14:30:00 UTC"


@pytest.mark.unit
class TestDatetimeUtils:
    """Test core datetime utility functions"""

    def test_now_utc_returns_utc_datetime(self):
        """
        Test: Get current UTC datetime
        Expected: Returns timezone-aware UTC datetime
        """
        result = now_utc()

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

        # Should be within 1 second of actual now
        actual_now = datetime.now(timezone.utc)
        delta = abs((result - actual_now).total_seconds())
        assert delta < 1

    def test_seconds_since_recent_datetime(self):
        """
        Test: Calculate seconds since datetime
        Expected: Returns positive float seconds
        """
        dt = datetime.now(timezone.utc) - timedelta(seconds=30)
        result = seconds_since(dt)

        assert isinstance(result, float)
        assert 29 <= result <= 31  # ~30 seconds (±1 second tolerance)

    def test_seconds_since_old_datetime(self):
        """
        Test: Calculate seconds since old datetime
        Expected: Returns large positive integer
        """
        dt = datetime.now(timezone.utc) - timedelta(hours=1)
        result = seconds_since(dt)

        assert result >= 3600  # At least 1 hour in seconds

    def test_is_recent_for_recent_datetime(self):
        """
        Test: Check if datetime is recent (5 minutes threshold)
        Expected: Returns True for < 5 minutes old
        """
        dt = datetime.now(timezone.utc) - timedelta(minutes=3)
        result = is_recent(dt, max_age_seconds=300)  # 5 minutes

        assert result is True

    def test_is_recent_for_old_datetime(self):
        """
        Test: Check if datetime is recent
        Expected: Returns False for > 5 minutes old
        """
        dt = datetime.now(timezone.utc) - timedelta(minutes=10)
        result = is_recent(dt, max_age_seconds=300)  # 5 minutes

        assert result is False

    def test_is_recent_with_custom_threshold(self):
        """
        Test: Check if datetime is recent with custom threshold
        Expected: Uses custom threshold (e.g., 60 seconds)
        """
        dt = datetime.now(timezone.utc) - timedelta(seconds=45)
        result = is_recent(dt, max_age_seconds=60)

        assert result is True

        dt_old = datetime.now(timezone.utc) - timedelta(seconds=90)
        result_old = is_recent(dt_old, max_age_seconds=60)

        assert result_old is False


@pytest.mark.integration
class TestDatetimeEndToEnd:
    """Integration tests for datetime module"""

    def test_parse_format_roundtrip(self):
        """
        Test: Parse and format datetime roundtrip
        Expected: Original timestamp preserved
        """
        original = "2025-01-10T14:30:00.123456Z"

        # Parse
        dt = parse_iso8601(original)

        # Format back
        formatted = to_iso8601(dt)

        # Parse again
        dt2 = parse_iso8601(formatted)

        # Should be equal
        assert dt == dt2

    def test_complete_workflow(self):
        """
        Test: Complete datetime workflow
        Expected: All utilities work together correctly
        """
        # Get current UTC time
        now = now_utc()

        # Format to ISO8601
        iso_string = to_iso8601(now)

        # Parse back
        parsed = parse_iso8601(iso_string)

        # Check if recent (within 5 minutes)
        assert is_recent(parsed, max_age_seconds=300) is True

        # Calculate seconds since
        seconds = seconds_since(parsed)
        assert seconds < 2  # Should be very recent

        # Format relative
        relative = format_relative(parsed)
        assert relative == "Just now"

        # Format medical
        medical = format_medical(parsed)
        assert len(medical) > 0
