"""AttendX AI FastAPI application."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import admin, attendance_student, auth, health, academic, reports, student, teacher
from app.core.config import get_settings
from app.core.db import SessionLocal, create_all
from app.core.errors import ApiError
from app.models import User, UserRole
from app.services.auth import bootstrap_admin

settings = get_settings()
logger = logging.getLogger("attendx")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env in {"development", "test"}:
        create_all()
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        with SessionLocal() as db:
            existing_admin = db.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1))
            if existing_admin is None:
                bootstrap_admin(
                    db,
                    email=settings.bootstrap_admin_email,
                    password=settings.bootstrap_admin_password,
                    full_name=settings.bootstrap_admin_name,
                )
                logger.warning(
                    "Bootstrap administrator created for %s. Change the bootstrap password "
                    "and remove BOOTSTRAP_ADMIN_PASSWORD from the environment.",
                    settings.bootstrap_admin_email,
                )
    yield


app = FastAPI(
    title="AttendX AI API",
    version="0.1.0",
    description=(
        "Intelligent attendance with rotating QR, temporary PIN, location evidence, "
        "provider-based face/liveness verification and an explainable risk engine."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin is not None and origin.rstrip("/") not in {
            item.rstrip("/") for item in settings.cors_origins
        }:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "ORIGIN_NOT_ALLOWED",
                        "message": "The request origin is not allowed.",
                        "details": {},
                    }
                },
            )
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(self), geolocation=(self), microphone=()"
    )
    response.headers.setdefault("X-Request-Id", uuid.uuid4().hex)
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    headers = {}
    if exc.status_code == 429:
        details = exc.detail.get("details", {}) if isinstance(exc.detail, dict) else {}
        retry = details.get("retry_after_seconds")
        if retry:
            headers["Retry-After"] = str(retry)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail}, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "One or more request fields are invalid.",
                "details": {"errors": exc.errors()},
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        payload = detail
    else:
        payload = {"code": "HTTP_ERROR", "message": str(detail), "details": {}}
    return JSONResponse(status_code=exc.status_code, content={"error": payload})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected server error occurred.",
                "details": {},
            }
        },
    )


app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(academic.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(teacher.router, prefix=settings.api_v1_prefix)
app.include_router(student.router, prefix=settings.api_v1_prefix)
app.include_router(attendance_student.router, prefix=settings.api_v1_prefix)
app.include_router(reports.router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "AttendX AI API",
        "version": "0.1.0",
        "docs": "/api/docs",
        "health": f"{settings.api_v1_prefix}/health/ready",
    }
