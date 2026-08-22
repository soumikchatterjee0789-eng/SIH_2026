"""
Standard, documented error codes (PRD Section 27) and a single custom
exception type that carries them through to a consistent JSON body via
the exception handler registered in app.main.
"""
from fastapi import HTTPException


class ErrorCode:
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_TRANSACTION = "INVALID_TRANSACTION"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    UNAUTHORIZED = "UNAUTHORIZED"
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CALCULATION_ERROR = "CALCULATION_ERROR"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class APIError(HTTPException):
    """Raise this anywhere in routes/services; the global handler in
    app.main converts it into the standard error envelope."""

    def __init__(self, status_code: int, message: str, error_code: str):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_code = error_code
