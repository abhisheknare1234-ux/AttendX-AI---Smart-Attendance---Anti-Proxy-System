"""Student attendance verification flow endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import AuthContext, client_ip, require_csrf, require_student_profile
from app.schemas.attendance import (
    AttemptDetailResponse,
    AttemptOut,
    CheckInRequest,
    CheckInResponse,
    FactorStepResponse,
    FinalizeResponse,
    LocationRequest,
    LocationStepResponse,
    PinRequest,
    QrValidateRequest,
    QrValidateResponse,
    StepResponse,
)
from app.services import attendance as attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"], dependencies=[Depends(require_csrf)])


@router.post("/qr/validate", response_model=QrValidateResponse)
def validate_qr(
    payload: QrValidateRequest,
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    _row, session = attendance_service.validate_qr(db, payload.token, settings)
    attendance_service.ensure_enrolled(db, session, auth.student_id)
    return attendance_service.qr_validate_response(db, session, auth.student_id, settings)


@router.post("/check-ins", response_model=CheckInResponse, status_code=201)
def check_in(
    payload: CheckInRequest,
    request: Request,
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    attempt, session_view, steps, next_step = attendance_service.start_attempt(
        db,
        token=payload.qr_token,
        student_id=auth.student_id,
        settings=settings,
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return CheckInResponse(
        attempt=attendance_service.attempt_out(attempt),
        session=session_view,
        required_steps=steps,
        next_step=next_step,
    )


@router.get("/attempts/{attempt_id}", response_model=AttemptDetailResponse)
def get_attempt(
    attempt_id: uuid.UUID,
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    attempt, session = attendance_service._attempt_for_student(db, attempt_id, auth.student_id)
    return AttemptDetailResponse(
        attempt=attendance_service.attempt_out(attempt),
        session=attendance_service.qr_validate_response(db, session, auth.student_id, settings),
        next_step=attendance_service.next_step(attempt, session),
    )


@router.post("/attempts/{attempt_id}/pin", response_model=StepResponse)
def submit_pin(
    attempt_id: uuid.UUID,
    payload: PinRequest,
    request: Request,
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    attempt, next_step = attendance_service.submit_pin(
        db,
        attempt_id=attempt_id,
        student_id=auth.student_id,
        pin=payload.pin,
        settings=settings,
        ip_address=client_ip(request),
    )
    return StepResponse(
        attempt=attendance_service.attempt_out(attempt),
        next_step=next_step,
        message="PIN verified." if attempt.pin_status.value == "PASSED" else "PIN step complete.",
    )


@router.post("/attempts/{attempt_id}/location", response_model=LocationStepResponse)
def submit_location(
    attempt_id: uuid.UUID,
    payload: LocationRequest,
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    attempt, evidence = attendance_service.submit_location(
        db,
        attempt_id=attempt_id,
        student_id=auth.student_id,
        payload=payload,
        settings=settings,
    )
    return LocationStepResponse(
        attempt=attendance_service.attempt_out(attempt),
        next_step=attendance_service.next_step(
            attempt, attendance_service.get_session(db, attempt.session_id)
        ),
        message="Location evidence recorded.",
        gps_status=evidence.status,
        distance_m=evidence.distance_m,
        accuracy_m=evidence.accuracy_m,
        reason_code=evidence.reason_code,
    )


@router.post("/attempts/{attempt_id}/face", response_model=FactorStepResponse)
async def submit_face(
    attempt_id: uuid.UUID,
    image: UploadFile | None = File(default=None),
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    image_bytes = await image.read() if image is not None else None
    content_type = image.content_type if image is not None else ""
    attempt, result = attendance_service.submit_face(
        db,
        attempt_id=attempt_id,
        student_id=auth.student_id,
        image=image_bytes,
        content_type=content_type or "",
        settings=settings,
    )
    next_step = attendance_service.next_step(
        attempt, attendance_service.get_session(db, attempt.session_id)
    )
    return FactorStepResponse(
        attempt=attendance_service.attempt_out(attempt),
        next_step=next_step,
        message="Face verification step recorded.",
        factor="face",
        status=result.status,
        reason_code=result.reason_code,
        provider=result.provider,
        score=result.score,
    )


@router.post("/attempts/{attempt_id}/liveness", response_model=FactorStepResponse)
async def submit_liveness(
    attempt_id: uuid.UUID,
    image: UploadFile | None = File(default=None),
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    image_bytes = await image.read() if image is not None else None
    content_type = image.content_type if image is not None else ""
    attempt, result = attendance_service.submit_liveness(
        db,
        attempt_id=attempt_id,
        student_id=auth.student_id,
        image=image_bytes,
        content_type=content_type or "",
        settings=settings,
    )
    next_step = attendance_service.next_step(
        attempt, attendance_service.get_session(db, attempt.session_id)
    )
    return FactorStepResponse(
        attempt=attendance_service.attempt_out(attempt),
        next_step=next_step,
        message="Liveness step recorded.",
        factor="liveness",
        status=result.status,
        reason_code=result.reason_code,
        provider=result.provider,
        score=result.score,
    )


@router.post("/attempts/{attempt_id}/finalize", response_model=FinalizeResponse)
def finalize(
    attempt_id: uuid.UUID,
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return attendance_service.finalize_attempt(
        db, attempt_id=attempt_id, student_id=auth.student_id, settings=settings
    )
