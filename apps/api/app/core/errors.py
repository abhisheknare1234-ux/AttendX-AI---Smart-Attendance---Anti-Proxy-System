"""Consistent API error shape: {"error": {"code", "message", "details"}}."""
from __future__ import annotations

from fastapi import HTTPException, status


class ApiError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        **details: object,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message, "details": details or {}},
        )


def unauthorized(message: str = "Authentication required.") -> ApiError:
    return ApiError(status.HTTP_401_UNAUTHORIZED, "NOT_AUTHENTICATED", message)


def forbidden(message: str = "You are not allowed to perform this action.") -> ApiError:
    return ApiError(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def not_found(message: str = "Resource not found.") -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", message)


def conflict(message: str, code: str = "CONFLICT", **details: object) -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, code, message, **details)


def bad_request(message: str, code: str = "BAD_REQUEST", **details: object) -> ApiError:
    return ApiError(status.HTTP_400_BAD_REQUEST, code, message, **details)


def too_many_requests(message: str, retry_after: int = 0) -> ApiError:
    return ApiError(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "RATE_LIMITED",
        message,
        retry_after_seconds=retry_after,
    )
