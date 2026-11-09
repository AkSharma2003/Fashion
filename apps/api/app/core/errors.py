"""Standard error format (SRS 8.1 / 8.2).

New modules raise BusinessError; the handler in main.py turns it into
{"success": false, "data": null, "error": {"code", "message"}, "detail": message}.
`detail` is kept so older screens that read FastAPI's `detail` still show the message.
"""
from typing import Any


class BusinessError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422, extra: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}


def not_found(what: str = "Item") -> BusinessError:
    return BusinessError("NOT_FOUND", f"{what} not found.", 404)


def forbidden(message: str = "Your role is not allowed to do this.") -> BusinessError:
    return BusinessError("FORBIDDEN", message, 403)


def validation(message: str) -> BusinessError:
    return BusinessError("VALIDATION_ERROR", message, 400)


def conflict(code: str, message: str) -> BusinessError:
    return BusinessError(code, message, 409)


def error_body(code: str, message: str, extra: dict | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if extra:
        error.update(extra)
    return {"success": False, "data": None, "error": error, "detail": message}


def ok(data: Any = None) -> dict[str, Any]:
    return {"success": True, "data": data, "error": None}
