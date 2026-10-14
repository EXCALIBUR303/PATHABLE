import re
import uuid

from fastapi import FastAPI
from starlette.datastructures import MutableHeaders
from starlette.requests import Request

from app.api.ml import router as ml_router
from app.api.reporting import router as reporting_router
from app.api.routes import router
from app.core.errors import install_handlers, response


class RequestBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        scope.setdefault("state", {})["request_id"] = str(uuid.uuid4())
        request = Request(scope)

        async def headers(message):
            if message["type"] == "http.response.start":
                outgoing = MutableHeaders(scope=message)
                outgoing["X-Request-ID"] = scope["state"]["request_id"]
                outgoing["X-Content-Type-Options"] = "nosniff"
                outgoing.setdefault("Cache-Control", "no-store")
            await send(message)

        upload = scope["method"] == "POST" and re.fullmatch(
            r"/api/v1/reports/[0-9a-fA-F-]{36}/evidence", scope["path"]
        )
        if upload:
            from app.services.evidence import MAX_REQUEST_BYTES

            if (
                request.headers.get("content-type", "").split(";", 1)[0].lower()
                != "multipart/form-data"
            ):
                return await response(
                    request, 415, "UNSUPPORTED_MEDIA_TYPE", "Use multipart/form-data for evidence"
                )(scope, receive, headers)
            length = request.headers.get("content-length")
            if length is not None:
                if not length.isascii() or not length.isdigit():
                    return await response(request, 400, "INVALID_LENGTH", "Invalid Content-Length")(
                        scope, receive, headers
                    )
                if int(length) > MAX_REQUEST_BYTES:
                    return await response(
                        request, 413, "BODY_TOO_LARGE", "Evidence request exceeds its byte limit"
                    )(scope, receive, headers)
            consumed = 0

            async def bounded_receive():
                nonlocal consumed
                message = await receive()
                consumed += len(message.get("body", b""))
                if consumed > MAX_REQUEST_BYTES:
                    from app.core.errors import Problem

                    raise Problem(413, "BODY_TOO_LARGE", "Evidence request exceeds its byte limit")
                return message

            # Authentication/ownership happens in the endpoint before parsing. The
            # multipart parser spools files while this boundary bounds actual bytes.
            return await self.app(scope, bounded_receive, headers)
        messages = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 65536:
                return await response(
                    request, 413, "BODY_TOO_LARGE", "Request body exceeds 64 KiB"
                )(scope, receive, headers)
            messages.append(message)
            if not message.get("more_body", False):
                break

        if (
            size
            and scope["method"] in ("POST", "PUT", "PATCH", "DELETE")
            and request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            != "application/json"
        ):
            return await response(
                request, 415, "UNSUPPORTED_MEDIA_TYPE", "Use application/json for this endpoint"
            )(scope, receive, headers)

        async def replay():
            return messages.pop(0) if messages else await receive()

        await self.app(scope, replay, headers)


def create_app():
    app = FastAPI(
        title="PathAble API",
        version="0.5.0",
        description="Campus routing, reviewed reporting and live graph updates. Seed data is synthetic_demo.",
    )
    app.add_middleware(RequestBoundary)
    install_handlers(app)
    app.include_router(router)
    app.include_router(reporting_router, responses=router.responses)
    app.include_router(ml_router, responses=router.responses)
    return app


app = create_app()
