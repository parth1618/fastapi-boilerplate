"""Security utilities tests."""

from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.middleware.validation import sanitize_string, validate_password_strength


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_hash_password(self) -> None:
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$argon2")

    def test_verify_password_success(self) -> None:
        """Test successful password verification."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self) -> None:
        """Test failed password verification."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_hash_different_each_time(self) -> None:
        """Test that hashing produces different results each time."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2


class TestJWTTokens:
    """Test JWT token functions."""

    def test_create_access_token(self) -> None:
        """Test access token creation."""
        token = create_access_token(subject=123)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self) -> None:
        """Test refresh token creation."""
        token = create_refresh_token(subject=123)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token(self) -> None:
        """Test access token verification."""
        user_id = 123
        token = create_access_token(subject=user_id)
        payload = verify_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_verify_refresh_token(self) -> None:
        """Test refresh token verification."""
        user_id = 456
        token = create_refresh_token(subject=user_id)
        payload = verify_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_verify_expired_token(self) -> None:
        """Test expired token verification."""
        token = create_access_token(subject=123, expires_delta=timedelta(seconds=-1))

        with pytest.raises(ValueError, match="expired"):
            verify_token(token)

    def test_verify_invalid_token(self) -> None:
        """Test invalid token verification."""
        with pytest.raises(ValueError, match="Invalid"):
            verify_token("invalid.token.here")

    def test_token_with_string_subject(self) -> None:
        """Test token with string subject."""
        token = create_access_token(subject="user123")
        payload = verify_token(token)

        assert payload["sub"] == "user123"


class TestPasswordValidation:
    """Test password strength validation."""

    def test_valid_strong_password(self) -> None:
        """Test valid strong password."""
        is_valid, msg = validate_password_strength("StrongPass123!")

        assert is_valid is True
        assert msg == ""

    def test_password_too_short(self) -> None:
        """Test password too short."""
        is_valid, msg = validate_password_strength("Short1!")

        assert is_valid is False
        assert "at least" in msg.lower()

    def test_password_no_uppercase(self) -> None:
        """Test password without uppercase."""
        is_valid, msg = validate_password_strength("lowercase123!")

        assert is_valid is False
        assert "uppercase" in msg.lower()

    def test_password_no_lowercase(self) -> None:
        """Test password without lowercase."""
        is_valid, msg = validate_password_strength("UPPERCASE123!")

        assert is_valid is False
        assert "lowercase" in msg.lower()

    def test_password_no_digit(self) -> None:
        """Test password without digit."""
        is_valid, msg = validate_password_strength("NoDigitsHere!")

        assert is_valid is False
        assert "digit" in msg.lower()

    def test_password_no_special(self) -> None:
        """Test password without special character."""
        is_valid, msg = validate_password_strength("NoSpecial123")

        assert is_valid is False
        assert "special" in msg.lower()

    def test_password_common(self) -> None:
        """Test common password."""
        is_valid, msg = validate_password_strength("password123")

        assert is_valid is False
        assert "common" in msg.lower()


class TestInputSanitization:
    """Test input sanitization."""

    def test_sanitize_normal_text(self) -> None:
        """Test sanitizing normal text."""
        text = "Hello World"
        sanitized = sanitize_string(text)

        assert sanitized == "Hello World"

    def test_sanitize_null_bytes(self) -> None:
        """Test removing null bytes."""
        text = "Hello\x00World"
        sanitized = sanitize_string(text)

        assert "\x00" not in sanitized
        assert sanitized == "HelloWorld"

    def test_sanitize_control_chars(self) -> None:
        """Test removing control characters."""
        text = "Hello\x01\x02World"
        sanitized = sanitize_string(text)

        assert "\x01" not in sanitized
        assert sanitized == "HelloWorld"

    def test_sanitize_preserves_newlines(self) -> None:
        """Test that newlines are preserved."""
        text = "Hello\nWorld"
        sanitized = sanitize_string(text)

        assert sanitized == "Hello\nWorld"

    def test_sanitize_max_length(self) -> None:
        """Test max length truncation."""
        text = "A" * 2000
        sanitized = sanitize_string(text, max_length=100)

        assert len(sanitized) == 100

    def test_sanitize_empty_string(self) -> None:
        """Test sanitizing empty string."""
        sanitized = sanitize_string("")

        assert sanitized == ""

    def test_sanitize_whitespace(self) -> None:
        """Test trimming whitespace."""
        text = "  Hello World  "
        sanitized = sanitize_string(text)

        assert sanitized == "Hello World"
