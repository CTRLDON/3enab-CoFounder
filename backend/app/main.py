"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import artifacts, audit, commerce, debate, founders, phases, plan, system, ventures
from app.config import get_settings
from app.database import init_db
from app.errors import MateError


@asynccontextmanager
async def lifespan(_: FastAPI):  # type: ignore[no-untyped-def]
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Mate — Your AI Co-Founder", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "X-Founder-Token"],
    )

    @app.exception_handler(MateError)
    async def _mate_error(_: Request, exc: MateError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message, "detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        problems = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": "invalid_input", "message": "Some fields need attention.", "detail": problems})

    for module in (system, founders, ventures, debate, plan, phases, commerce, artifacts, audit):
        app.include_router(module.router)
    return app


app = create_app()
