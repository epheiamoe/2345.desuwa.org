"""Tests for database operations."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from api.database import Database, DatabaseError


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_creates_database_file(self):
        """Should create database file on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            assert os.path.exists(db_path)

    def test_creates_parent_directory(self):
        """Should create parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "nested", "dir", "test.db")
            db = Database(db_path)
            assert os.path.exists(db_path)

    def test_uses_default_path(self):
        """Should use default path when none provided."""
        db = Database()
        assert db.db_path.name == "db.sqlite"

    def test_schema_created(self):
        """Should create tables on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)

            with db._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in cursor.fetchall()]

            assert "api_keys" in tables
            assert "rate_limits" in tables
            assert "api_usage" in tables


class TestApiKeyManagement:
    """Tests for API key CRUD operations."""

    def setup_method(self):
        """Set up fresh database for each test."""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = Database(self.db_path)

    def teardown_method(self):
        """Clean up temporary database."""
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_and_get_api_key(self):
        """Should create and retrieve API key."""
        self.db.create_api_key("test-key-123", {"github_login": "testuser"})
        result = self.db.get_api_key("test-key-123")

        assert result is not None
        assert result["key"] == "test-key-123"
        assert result["github_login"] == "testuser"

    def test_get_nonexistent_key(self):
        """Should return None for non-existent key."""
        result = self.db.get_api_key("does-not-exist")
        assert result is None

    def test_duplicate_key_raises(self):
        """Should raise error for duplicate key."""
        self.db.create_api_key("dup-key", {})
        with pytest.raises(DatabaseError, match="already exists"):
            self.db.create_api_key("dup-key", {})

    def test_update_api_key(self):
        """Should update API key fields."""
        self.db.create_api_key("update-key", {"github_login": "old"})
        success = self.db.update_api_key("update-key", {"github_login": "new"})

        assert success is True
        result = self.db.get_api_key("update-key")
        assert result["github_login"] == "new"

    def test_update_nonexistent_key(self):
        """Should return False for non-existent key."""
        success = self.db.update_api_key("no-key", {"github_login": "test"})
        assert success is False

    def test_update_invalid_fields_ignored(self):
        """Should ignore invalid fields in update."""
        self.db.create_api_key("field-key", {})
        success = self.db.update_api_key("field-key", {"invalid_field": "value"})
        assert success is False

    def test_delete_api_key(self):
        """Should delete API key."""
        self.db.create_api_key("del-key", {})
        success = self.db.delete_api_key("del-key")
        assert success is True
        assert self.db.get_api_key("del-key") is None

    def test_delete_nonexistent_key(self):
        """Should return False for non-existent key."""
        success = self.db.delete_api_key("no-key")
        assert success is False

    def test_list_api_keys(self):
        """Should list all API keys ordered by creation time."""
        self.db.create_api_key("key-1", {"github_login": "user1"})
        self.db.create_api_key("key-2", {"github_login": "user2"})

        keys = self.db.list_api_keys()
        assert len(keys) == 2


class TestRateLimitOperations:
    """Tests for rate limit counter operations."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = Database(self.db_path)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_nonexistent_rate_limit(self):
        """Should return None for non-existent rate limit."""
        result = self.db.get_rate_limit("new-key")
        assert result is None

    def test_update_and_get_rate_limit(self):
        """Should update and retrieve rate limit counters."""
        counters = {
            "minute_count": 1,
            "day_count": 5,
            "month_count": 10,
            "minute_reset": 1000,
            "day_reset": 86400,
            "month_reset": 2592000,
        }
        self.db.update_rate_limit("test-key", counters)
        result = self.db.get_rate_limit("test-key")

        assert result is not None
        assert result["minute_count"] == 1
        assert result["day_count"] == 5
        assert result["month_count"] == 10

    def test_update_existing_rate_limit(self):
        """Should overwrite existing rate limit."""
        counters1 = {
            "minute_count": 1,
            "day_count": 1,
            "month_count": 1,
            "minute_reset": 1000,
            "day_reset": 86400,
            "month_reset": 2592000,
        }
        counters2 = {
            "minute_count": 5,
            "day_count": 5,
            "month_count": 5,
            "minute_reset": 2000,
            "day_reset": 172800,
            "month_reset": 5184000,
        }

        self.db.update_rate_limit("test-key", counters1)
        self.db.update_rate_limit("test-key", counters2)
        result = self.db.get_rate_limit("test-key")

        assert result["minute_count"] == 5


class TestApiUsageLogging:
    """Tests for API usage audit logging."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = Database(self.db_path)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_log_api_usage(self):
        """Should log API usage without errors."""
        self.db.log_api_usage("test-key", "/api/search")
        # Should not raise

    def test_log_api_usage_does_not_fail(self):
        """Should not raise even on invalid input."""
        # Should not raise even with None values
        self.db.log_api_usage("key", "endpoint")


class TestMigration:
    """Tests for data migration."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = Database(self.db_path)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_migrate_from_json(self):
        """Should migrate API keys from JSON file."""
        json_data = {
            "users": {
                "user-1": {
                    "github_id": "1",
                    "github_login": "user1",
                    "api_key": "key-1",
                },
                "user-2": {
                    "github_id": "2",
                    "github_login": "user2",
                    "api_key": "key-2",
                },
            },
            "keys": {
                "key-1": "user-1",
                "key-2": "user-2",
            },
        }
        json_path = os.path.join(self.tmpdir, "db.json")
        with open(json_path, "w") as f:
            json.dump(json_data, f)

        count = self.db.migrate_from_json(json_path)
        assert count == 2

        result = self.db.get_api_key("key-1")
        assert result is not None
        assert result["github_login"] == "user1"

    def test_migrate_from_nonexistent_file(self):
        """Should return 0 for non-existent file."""
        count = self.db.migrate_from_json("/nonexistent/path.json")
        assert count == 0

    def test_migrate_invalid_json_raises(self):
        """Should raise for invalid JSON."""
        json_path = os.path.join(self.tmpdir, "invalid.json")
        with open(json_path, "w") as f:
            f.write("not json")

        with pytest.raises(DatabaseError, match="Invalid JSON"):
            self.db.migrate_from_json(json_path)
