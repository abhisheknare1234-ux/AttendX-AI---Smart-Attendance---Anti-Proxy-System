"""Authentication endpoints: password login, TOTP MFA, reset tokens, sessions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import AuthContext, client_ip, get_current_auth, require_csrf
from app.core.security import hash_password, password_problem, verify_password
from app.schemas.accounts import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MfaChallengeResponse,
    MfaCodeRequest,
    MfaDisableRequest,
    MfaSetupResponse,
    MfaStatusResponse,
    MfaVerifyRequest,
    PasswordResetRequest,
)
from app.services import audit as audit_service
from app.services import auth as auth_service
from app.services import mfa as mfa_service
from app.services import password_reset as password_reset_service
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


@router.post("/login", response_model=LoginResponse)
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
    if session is None or raw_token is None:
        challenge_token, challenge = mfa_service.create_challenge(
            db, user=user, ip_address=client_ip(request), settings=settings
        )
        return MfaChallengeResponse(
            challenge_token=challenge_token,
            expires_at=challenge.expires_at,
        )
    _set_cookies(response, raw_token, session.csrf_token, settings)
    return MeResponse(user=user_out(db, user), csrf_token=session.csrf_token)


@router.post("/mfa/verify", response_model=MeResponse)
def verify_mfa(
    payload: MfaVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user, session, raw_token = mfa_service.verify_challenge(
        db,
        challenge_token=payload.challenge_token,
        code=payload.code,
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


@router.get("/mfa", response_model=MfaStatusResponse)
def mfa_status(auth: AuthContext = Depends(get_current_auth)):
    return MfaStatusResponse(**mfa_service.status(auth.user))


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(
    auth: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    secret, uri = mfa_service.begin_setup(db, user=auth.user, settings=settings)
    return MfaSetupResponse(secret=secret, otpauth_uri=uri)


@router.post("/mfa/enable", response_model=MfaStatusResponse)
def mfa_enable(
    payload: MfaCodeRequest,
    auth: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    mfa_service.enable(db, user=auth.user, code=payload.code, settings=settings)
    return MfaStatusResponse(**mfa_service.status(auth.user))


@router.post("/mfa/disable", response_model=MfaStatusResponse)
def mfa_disable(
    payload: MfaDisableRequest,
    auth: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    mfa_service.disable(
        db,
        user=auth.user,
        password=payload.password,
        code=payload.code,
        current_session_id=auth.session.id,
        settings=settings,
    )
    return MfaStatusResponse(**mfa_service.status(auth.user))


@router.post("/reset-password")
def reset_password(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    password_reset_service.reset_password(
        db,
        raw_token=payload.token,
        new_password=payload.new_password,
        settings=settings,
        ip_address=client_ip(request),
    )
    return {"ok": True}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    auth: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not verify_password(payload.current_password, auth.user.password_hash):
        raise errors.bad_request("The current password is incorrect.", "CURRENT_PASSWORD_INVALID")
    if auth.user.mfa_enabled:
        if not payload.mfa_code:
            raise errors.bad_request(
                "An authenticator code is required when MFA is enabled.",
                "MFA_CODE_REQUIRED",
            )
        mfa_service.require_code(db, user=auth.user, code=payload.mfa_code, settings=settings)
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
