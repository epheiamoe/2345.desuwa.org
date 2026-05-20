"""Tests for input validators."""

import pytest

from api.validators import InputValidator, ValidationError, validate_search_params


class TestValidateSearchQuery:
    """Tests for validate_search_query method."""

    def test_valid_query(self):
        """Should return stripped query for valid input."""
        result = InputValidator.validate_search_query("HRT")
        assert result == "HRT"

    def test_query_with_whitespace(self):
        """Should strip whitespace from query."""
        result = InputValidator.validate_search_query("  HRT  ")
        assert result == "HRT"

    def test_empty_query_raises(self):
        """Should raise ValidationError for empty string."""
        with pytest.raises(ValidationError, match="Query parameter is required"):
            InputValidator.validate_search_query("")

    def test_none_query_raises(self):
        """Should raise ValidationError for None."""
        with pytest.raises(ValidationError, match="Query parameter is required"):
            InputValidator.validate_search_query(None)

    def test_whitespace_only_query_raises(self):
        """Should raise ValidationError for whitespace-only string."""
        with pytest.raises(ValidationError, match="Query cannot be empty"):
            InputValidator.validate_search_query("   ")

    def test_query_too_long_raises(self):
        """Should raise ValidationError for query exceeding max length."""
        long_query = "a" * 201
        with pytest.raises(ValidationError, match="Query too long"):
            InputValidator.validate_search_query(long_query)

    def test_dangerous_characters_raises(self):
        """Should raise ValidationError for queries with dangerous characters."""
        with pytest.raises(ValidationError, match="Invalid characters"):
            InputValidator.validate_search_query("test\x00query")

    def test_exact_max_length_query(self):
        """Should accept query at exactly max length."""
        query = "a" * 200
        result = InputValidator.validate_search_query(query)
        assert result == query


class TestValidateLimit:
    """Tests for validate_limit method."""

    def test_valid_limit(self):
        """Should return integer for valid limit."""
        result = InputValidator.validate_limit(10)
        assert result == 10

    def test_string_limit(self):
        """Should convert string to integer."""
        result = InputValidator.validate_limit("20")
        assert result == 20

    def test_zero_limit_raises(self):
        """Should raise ValidationError for zero limit."""
        with pytest.raises(ValidationError, match="at least 1"):
            InputValidator.validate_limit(0)

    def test_negative_limit_raises(self):
        """Should raise ValidationError for negative limit."""
        with pytest.raises(ValidationError, match="at least 1"):
            InputValidator.validate_limit(-1)

    def test_excessive_limit_raises(self):
        """Should raise ValidationError for limit exceeding absolute max."""
        with pytest.raises(ValidationError, match="cannot exceed 1000"):
            InputValidator.validate_limit(1001)

    def test_invalid_type_raises(self):
        """Should raise ValidationError for non-integer string."""
        with pytest.raises(ValidationError, match="must be an integer"):
            InputValidator.validate_limit("abc")


class TestValidateOffset:
    """Tests for validate_offset method."""

    def test_valid_offset(self):
        """Should return integer for valid offset."""
        result = InputValidator.validate_offset(0)
        assert result == 0

    def test_positive_offset(self):
        """Should accept positive offset."""
        result = InputValidator.validate_offset(100)
        assert result == 100

    def test_string_offset(self):
        """Should convert string to integer."""
        result = InputValidator.validate_offset("50")
        assert result == 50

    def test_negative_offset_raises(self):
        """Should raise ValidationError for negative offset."""
        with pytest.raises(ValidationError, match="cannot be negative"):
            InputValidator.validate_offset(-1)

    def test_invalid_type_raises(self):
        """Should raise ValidationError for non-integer string."""
        with pytest.raises(ValidationError, match="must be an integer"):
            InputValidator.validate_offset("abc")


class TestValidateTag:
    """Tests for validate_tag method."""

    def test_valid_tag(self):
        """Should return tag for valid input."""
        result = InputValidator.validate_tag("HRT")
        assert result == "HRT"

    def test_invalid_tag_raises(self):
        """Should raise ValidationError for invalid tag."""
        with pytest.raises(ValidationError, match="Invalid tag"):
            InputValidator.validate_tag("invalid_tag")

    def test_empty_tag_raises(self):
        """Should raise ValidationError for empty tag."""
        with pytest.raises(ValidationError, match="Tag is required"):
            InputValidator.validate_tag("")


class TestValidateDomain:
    """Tests for validate_domain method."""

    def test_valid_domain(self):
        """Should return lowercase domain for valid input."""
        result = InputValidator.validate_domain("Example.COM")
        assert result == "example.com"

    def test_subdomain(self):
        """Should accept subdomain."""
        result = InputValidator.validate_domain("sub.example.com")
        assert result == "sub.example.com"

    def test_invalid_domain_raises(self):
        """Should raise ValidationError for invalid domain format."""
        with pytest.raises(ValidationError, match="Invalid domain format"):
            InputValidator.validate_domain("not a domain")

    def test_empty_domain_raises(self):
        """Should raise ValidationError for empty domain."""
        with pytest.raises(ValidationError, match="Domain is required"):
            InputValidator.validate_domain("")


class TestValidateApiKey:
    """Tests for validate_api_key method."""

    def test_valid_key(self):
        """Should return key for valid format."""
        key = "a" * 32
        result = InputValidator.validate_api_key(key)
        assert result == key

    def test_too_short_key_raises(self):
        """Should raise ValidationError for key under 20 chars."""
        with pytest.raises(ValidationError, match="Invalid API Key format"):
            InputValidator.validate_api_key("short")

    def test_empty_key_raises(self):
        """Should raise ValidationError for empty key."""
        with pytest.raises(ValidationError, match="API Key is required"):
            InputValidator.validate_api_key("")


class TestValidateLanguage:
    """Tests for validate_language method."""

    def test_valid_language(self):
        """Should return lowercase language code."""
        result = InputValidator.validate_language("EN")
        assert result == "en"

    def test_invalid_language_raises(self):
        """Should raise ValidationError for unsupported language."""
        with pytest.raises(ValidationError, match="Unsupported language"):
            InputValidator.validate_language("xx")


class TestValidateSearchParams:
    """Tests for validate_search_params convenience function."""

    def test_valid_params(self):
        """Should return validated params tuple."""
        q, limit, offset, tag, site = validate_search_params(
            q="HRT", limit="20", offset="0"
        )
        assert q == "HRT"
        assert limit == 20
        assert offset == 0
        assert tag is None
        assert site is None

    def test_with_optional_params(self):
        """Should handle optional tag and site parameters."""
        q, limit, offset, tag, site = validate_search_params(
            q="test", limit=10, offset=0, tag="HRT", site="example.com"
        )
        assert tag == "HRT"
        assert site == "example.com"

    def test_invalid_query_raises(self):
        """Should propagate ValidationError from invalid query."""
        with pytest.raises(ValidationError):
            validate_search_params(q="", limit=10)
