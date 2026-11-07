"""RFC 7807 problem responses."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"


class Problem(Exception):
    def __init__(self, status: int, title: str, detail: str, code: str) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail
        self.code = code


def _response(request: Request, status: int, title: str, detail: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type=PROBLEM_MEDIA_TYPE,
        content={
            "type": f"https://ledgerlens.invalid/problems/{code}",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
            "instance": request.url.path,
        },
    )


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def on_problem(request: Request, error: Problem) -> JSONResponse:
        return _response(request, error.status, error.title, error.detail, error.code)

    @app.exception_handler(HTTPException)
    async def on_http(request: Request, error: HTTPException) -> JSONResponse:
        return _response(request, error.status_code, "Request failed", str(error.detail), "http")

    @app.exception_handler(RequestValidationError)
    async def on_validation(request: Request, error: RequestValidationError) -> JSONResponse:
        fields = ", ".join(".".join(str(p) for p in e["loc"]) for e in error.errors())
        return _response(request, 422, "Invalid request", f"Invalid: {fields}", "invalid_request")
