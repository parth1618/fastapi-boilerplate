"""Enhanced input validation and sanitization middleware."""

import re
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for enhanced input validation and security checks.

    Features:
    - SQL injection pattern detection
    - XSS pattern detection
    - Path traversal detection
    - Malicious header detection
    - Request size limits
    """

    # Suspicious patterns that might indicate attacks
    SQL_INJECTION_PATTERNS: ClassVar[list[str]] = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(;|--|#|\/\*|\*\/)",  # SQL delimiters and comments
        r"('\s*or\s*')",  # ' OR ' pattern
        r"(\"  \s*or\s*\")",  # " OR " pattern
        r"(\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)",  # OR 1=1
    ]

    # And make sure XSS patterns catch the script tags:
    XSS_PATTERNS: ClassVar[list[str]] = [
        r"<script[\s>]",  # Opening script tag with space or >
        r"</script>",  # Closing script tag
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    PATH_TRAVERSAL_PATTERNS: ClassVar[list[str]] = [
        r"\.\./",
        r"\.\.",
        r"%2e%2e",
        r"\.\.\\",
    ]

    # Maximum request size in bytes (10MB default)
    MAX_REQUEST_SIZE = 10 * 1024 * 1024

    def __init__(self, app: Any, max_request_size: int | None = None) -> None:
        """Initialize validation middleware.

        Args:
            app: FastAPI application instance
            max_request_size: Maximum allowed request size in bytes
        """
        super().__init__(app)
        self.max_request_size = max_request_size or self.MAX_REQUEST_SIZE

        # Compile regex patterns for performance
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process and validate incoming requests."""
        # Check request size
        if hasattr(request, "headers") and "content-length" in request.headers:
            content_length = int(request.headers["content-length"])
            if content_length > self.max_request_size:
                logger.warning(
                    "request_too_large",
                    size=content_length,
                    max_size=self.max_request_size,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request body too large"},
                )

        # Validate URL path
        path = str(request.url.path)
        if self._contains_suspicious_patterns(path, self.path_patterns):
            logger.warning(
                "path_traversal_attempt",
                path=path,
                client=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request path"},
            )

        # Validate query parameters
        query_string = str(request.url.query)
        if query_string:  # Only check if query string exists
            if self._contains_suspicious_patterns(query_string, self.sql_patterns):
                logger.warning(
                    "sql_injection_attempt",
                    query=query_string,
                    path=request.url.path,
                    client=request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid query parameters"},
                )

            if self._contains_suspicious_patterns(query_string, self.xss_patterns):
                logger.warning(
                    "xss_attempt",
                    query=query_string,
                    path=request.url.path,
                    client=request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid query parameters"},
                )

        # Validate headers
        if self._validate_headers(request):
            logger.warning(
                "suspicious_headers",
                path=request.url.path,
                client=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request headers"},
            )

        # Process request
        try:
            response: Response = await call_next(request)
            return response
        except Exception as e:
            logger.error("request_processing_error", error=str(e))
            raise

    def _contains_suspicious_patterns(
        self,
        text: str,
        patterns: list[re.Pattern[str]],
    ) -> bool:
        """Check if text contains any suspicious patterns.

        Args:
            text: Text to check
            patterns: Compiled regex patterns to match against

        Returns:
            True if suspicious pattern found, False otherwise
        """
        return any(pattern.search(text) for pattern in patterns)

    def _validate_headers(self, request: Request) -> bool:
        """Validate request headers for suspicious content.

        Args:
            request: FastAPI request object

        Returns:
            True if headers are suspicious, False otherwise
        """
        suspicious_headers = [
            "x-forwarded-host",
            "x-original-url",
            "x-rewrite-url",
        ]

        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                # Check for suspicious patterns in header values
                if self._contains_suspicious_patterns(value, self.xss_patterns):
                    return True
                if self._contains_suspicious_patterns(value, self.path_patterns):
                    return True

        return False


def sanitize_string(input_string: str, max_length: int = 1000) -> str:
    """Sanitize string input by removing dangerous characters.

    Args:
        input_string: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not input_string:
        return ""

    # Truncate to max length
    sanitized = input_string[:max_length]

    # Remove null bytes
    sanitized = sanitized.replace("\x00", "")

    # Remove control characters (except newline, tab, carriage return)
    sanitized = "".join(
        char
        for char in sanitized
        if char in ("\n", "\t", "\r") or (ord(char) >= 32 and ord(char) != 127)
    )

    return sanitized.strip()


def validate_email_format(email: str) -> bool:
    """Validate email format using regex.

    Args:
        email: Email address to validate

    Returns:
        True if valid email format, False otherwise
    """
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return bool(email_pattern.match(email))


def validate_username_format(username: str) -> bool:
    """Validate username format.

    Rules:
    - 3-50 characters
    - Alphanumeric, underscore, hyphen only
    - Must start with alphanumeric

    Args:
        username: Username to validate

    Returns:
        True if valid username format, False otherwise
    """
    if not username or len(username) < 3 or len(username) > 50:
        return False

    username_pattern = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    return bool(username_pattern.match(username))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength.

    Requirements:
    - Minimum 12 characters (enterprise standard)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - No common passwords

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    flag, message = True, ""
    if len(password) < 12:
        flag, message = False, "Password must be at least 12 characters long"

    if not re.search(r"[A-Z]", password):
        flag, message = False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        flag, message = False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        flag, message = False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        flag, message = False, "Password must contain at least one special character"

    # Check against common passwords
    common_passwords = {
        "password123",
        "admin123",
        "12345678",
        "qwerty123",
        "password1",
        "123456789",
        "admin1234",
    }
    if password.lower() in common_passwords:
        return False, "Password is too common, please choose a stronger password"

    return (flag, message)
