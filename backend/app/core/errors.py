from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError
from starlette.exceptions import HTTPException


class Problem(Exception):
    def __init__(self, status, code, detail, **extra):
        self.status, self.code, self.detail, self.extra = status, code, detail, extra


def response(request, status, code, detail, **extra):
    retry_after = extra.pop("retry_after", 60)
    request_id = getattr(request.state, "request_id", "unknown")
    # Unexpected errors are handled outside user middleware by ServerErrorMiddleware.
    # They must keep the same privacy and correlation headers as handled failures.
    headers = {
        "X-Request-ID": request_id,
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }
    if status == 429:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        {
            "type": f"urn:pathable:problem:{code.lower()}",
            "title": code.replace("_", " ").title(),
            "status": status,
            "code": code,
            "detail": detail,
            "request_id": request_id,
            **extra,
        },
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
    )


def install_handlers(app):
    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception):
        return response(
            request,
            500,
            "INTERNAL_ERROR",
            "Unexpected server error; contact support with the request ID",
        )

    @app.exception_handler(Problem)
    async def problem(request: Request, error: Problem):
        return response(request, error.status, error.code, error.detail, **error.extra)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, error: RequestValidationError):
        # Pydantic's raw errors include input values; never echo passwords or tokens.
        errors = [
            {"field": ".".join(map(str, e["loc"])), "type": e["type"]} for e in error.errors()
        ]
        malformed = any(e["type"] == "json_invalid" for e in error.errors())
        return response(
            request,
            400 if malformed else 422,
            "INVALID_INPUT",
            "Request validation failed",
            field_errors=errors,
        )

    @app.exception_handler(IntegrityError)
    async def integrity(request: Request, error: IntegrityError):
        duplicate = getattr(error.orig, "sqlstate", "") == "23505"
        return response(
            request,
            409 if duplicate else 422,
            "CONFLICT" if duplicate else "INVALID_ASSOCIATION",
            "Resource conflicts with an existing record"
            if duplicate
            else "Database integrity validation failed",
        )

    @app.exception_handler(DBAPIError)
    async def database(request: Request, error: DBAPIError):
        return response(
            request, 503, "DATABASE_UNAVAILABLE", "Database operation unavailable; retry later"
        )

    @app.exception_handler(HTTPException)
    async def http(request: Request, error: HTTPException):
        return response(request, error.status_code, "HTTP_ERROR", str(error.detail))
