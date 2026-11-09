"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import AuthContext, client_ip, get_current_auth, require_csrf
from app.core.security import hash_password, password_problem, verify_password
from app.models import UserStatus
from app.schemas.accounts import ChangePasswordRequest, LoginRequest, MeResponse
from app.services import audit as audit_service
from app.services import auth as auth_service
from app.services.users import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookies(response: Response, raw_token: str, csrf_token: str, settings: Settings) -> None:
    max_age = settings.session_ttl_minutes * 60
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.effective_cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.effective_cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _clear_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


@router.post("/login", response_model=MeResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user, session, raw_token = auth_service.authenticate(
        db,
        email=payload.email,
        password=payload.password,
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        settings=settings,
    )
    _set_cookies(response, raw_token, session.csrf_token, settings)
    return MeResponse(user=user_out(db, user), csrf_token=session.csrf_token)


@router.post("/logout")
def logout(
    response: Response,
    auth: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    auth_service.revoke(db, auth.session)
    _clear_cookies(response, settings)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(auth: AuthContext = Depends(get_current_auth), db: Session = Depends(get_db)):
    return MeResponse(user=user_out(db, auth.user), csrf_token=auth.session.csrf_token)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    auth: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, auth.user.password_hash):
        raise errors.bad_request("The current password is incorrect.", "CURRENT_PASSWORD_INVALID")
    problem = password_problem(payload.new_password)
    if problem:
        raise errors.bad_request(problem, "WEAK_PASSWORD")
    if payload.current_password == payload.new_password:
        raise errors.bad_request("The new password must be different.", "PASSWORD_UNCHANGED")
    auth.user.password_hash = hash_password(payload.new_password)
    auth.user.must_change_password = False
    audit_service.security(
        db,
        event_type="PASSWORD_CHANGED",
        user_id=auth.user.id,
        details={},
    )
    db.commit()
    return {"ok": True}
