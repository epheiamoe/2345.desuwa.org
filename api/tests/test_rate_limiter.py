"""Tests for rate limiter."""

import time

import pytest

from api.rate_limiter import RateLimiter


class MockCursor:
    """Mock cursor for simulating SQLite cursor operations."""

    def __init__(self, records, key):
        self.records = records
        self.key = key
        self._result = None

    def fetchone(self):
        return self._result


class MockConnection:
    """Mock connection for simulating SQLite connection within a transaction."""

    def __init__(self, records):
        self.records = records

    def execute(self, sql, params=()):
        sql_upper = sql.strip().upper()
        if "SELECT" in sql_upper:
            key = params[0]
            record = self.records.get(key)
            cursor = MockCursor(self.records, key)
            if record:
                # Simulate sqlite3.Row behavior
                class Row:
                    def __init__(self, data):
                        self._data = data

                    def __getitem__(self, key):
                        return self._data.get(key)

                    def keys(self):
                        return self._data.keys()

                cursor._result = Row(record)
            return cursor
        elif "INSERT" in sql_upper:
            key = params[0]
            self.records[key] = {
                "key": key,
                "minute_count": params[1],
                "day_count": params[2],
                "month_count": params[3],
                "minute_reset": params[4],
                "day_reset": params[5],
                "month_reset": params[6],
            }
            return MockCursor(self.records, key)
        elif "UPDATE" in sql_upper:
            key = params[-1]
            if key in self.records:
                self.records[key]["minute_count"] = params[0]
                self.records[key]["day_count"] = params[1]
                self.records[key]["month_count"] = params[2]
                self.records[key]["minute_reset"] = params[3]
                self.records[key]["day_reset"] = params[4]
                self.records[key]["month_reset"] = params[5]
            return MockCursor(self.records, key)
        return MockCursor(self.records, "")


class MockDatabase:
    """Mock database for testing rate limiter."""

    def __init__(self):
        self.records = {}

    def get_rate_limit(self, key):
        return self.records.get(key)

    def update_rate_limit(self, key, counters):
        self.records[key] = counters

    def transaction(self):
        """Provide a transaction context manager for atomic operations."""
        import contextlib

        return contextlib.contextmanager(self._transaction)()

    def _transaction(self):
        conn = MockConnection(self.records)
        yield conn


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_default_limits(self):
        """Should use default limits when none provided."""
        limiter = RateLimiter(database=MockDatabase())
        assert limiter.limits["per_minute"] == 10
        assert limiter.limits["per_day"] == 1000
        assert limiter.limits["per_month"] == 2000

    def test_custom_limits(self):
        """Should accept custom limits."""
        custom = {"per_minute": 5, "per_day": 100, "per_month": 500}
        limiter = RateLimiter(limits=custom, database=MockDatabase())
        assert limiter.limits["per_minute"] == 5

    def test_invalid_limit_key_raises(self):
        """Should raise ValueError for unknown limit key."""
        with pytest.raises(ValueError, match="Unknown rate limit key"):
            RateLimiter(limits={"per_hour": 10}, database=MockDatabase())

    def test_negative_limit_raises(self):
        """Should raise ValueError for negative limit."""
        with pytest.raises(ValueError, match="positive integer"):
            RateLimiter(limits={"per_minute": -1}, database=MockDatabase())


class TestRateLimiterIsAllowed:
    """Tests for is_allowed method."""

    def setup_method(self):
        """Set up fresh mock database for each test."""
        self.db = MockDatabase()
        self.limiter = RateLimiter(database=self.db)

    def test_first_request_allowed(self):
        """Should allow first request for new key."""
        allowed, info = self.limiter.is_allowed("test-key")
        assert allowed is True
        assert info["allowed"] is True
        assert info["remaining_minute"] == 9

    def test_second_request_allowed(self):
        """Should allow second request."""
        self.limiter.is_allowed("test-key")
        allowed, info = self.limiter.is_allowed("test-key")
        assert allowed is True
        assert info["remaining_minute"] == 8

    def test_minute_limit_exceeded(self):
        """Should block when minute limit exceeded."""
        custom_limits = {"per_minute": 2, "per_day": 100, "per_month": 200}
        limiter = RateLimiter(limits=custom_limits, database=self.db)

        limiter.is_allowed("test-key")
        limiter.is_allowed("test-key")
        allowed, info = limiter.is_allowed("test-key")

        assert allowed is False
        assert info["allowed"] is False
        assert info["remaining_minute"] == 0

    def test_different_keys_independent(self):
        """Should track different keys independently."""
        self.limiter.is_allowed("key-1")
        self.limiter.is_allowed("key-2")

        info1 = self.limiter.get_status("key-1")
        info2 = self.limiter.get_status("key-2")

        assert info1["remaining_minute"] == 9
        assert info2["remaining_minute"] == 9

    def test_rate_limit_info_structure(self):
        """Should return complete rate limit info."""
        allowed, info = self.limiter.is_allowed("test-key")
        assert "limit_minute" in info
        assert "limit_day" in info
        assert "limit_month" in info
        assert "remaining_minute" in info
        assert "remaining_day" in info
        assert "remaining_month" in info
        assert "reset_minute" in info
        assert "reset_day" in info
        assert "reset_month" in info
        assert "allowed" in info


class TestRateLimiterGetStatus:
    """Tests for get_status method."""

    def setup_method(self):
        self.db = MockDatabase()
        self.limiter = RateLimiter(database=self.db)

    def test_new_key_full_quota(self):
        """Should return full quota for new key."""
        info = self.limiter.get_status("new-key")
        assert info["remaining_minute"] == 10
        assert info["remaining_day"] == 1000
        assert info["remaining_month"] == 2000
        assert info["allowed"] is True

    def test_status_after_requests(self):
        """Should reflect used quota after requests."""
        self.limiter.is_allowed("test-key")
        self.limiter.is_allowed("test-key")

        info = self.limiter.get_status("test-key")
        assert info["remaining_minute"] == 8
        assert info["allowed"] is True


class TestRateLimiterResetCounters:
    """Tests for reset_counters method."""

    def setup_method(self):
        self.db = MockDatabase()
        self.limiter = RateLimiter(database=self.db)

    def test_reset_clears_counters(self):
        """Should reset all counters to zero."""
        self.limiter.is_allowed("test-key")
        self.limiter.reset_counters("test-key")

        info = self.limiter.get_status("test-key")
        assert info["remaining_minute"] == 10


class TestRateLimiterWindowReset:
    """Tests for time window reset behavior."""

    def test_window_start_calculation(self):
        """Should calculate window start correctly."""
        db = MockDatabase()
        limiter = RateLimiter(database=db)

        now = int(time.time())
        minute_start = limiter._get_window_start("minute")
        assert minute_start <= now
        assert minute_start % 60 == 0

        day_start = limiter._get_window_start("day")
        assert day_start % 86400 == 0

    def test_invalid_period_raises(self):
        """Should raise ValueError for invalid time period."""
        limiter = RateLimiter(database=MockDatabase())
        with pytest.raises(ValueError, match="Invalid time period"):
            limiter._get_window_start("year")
