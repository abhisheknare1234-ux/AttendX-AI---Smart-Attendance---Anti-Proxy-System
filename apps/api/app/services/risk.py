"""Explainable, deterministic attendance risk engine.

This is a rule engine, not a trained machine-learning model. Every outcome is
reproducible from the supplied factor states and reason codes. It must never be
described as ML or as a probability of cheating.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models import FactorStatus, GpsStatus, RiskDecision

# Reason severities
BLOCK = "block"
REVIEW = "review"
INFO = "info"


@dataclass(frozen=True, slots=True)
class RequiredFactors:
    pin: bool
    geofence: bool
    face: bool
    liveness: bool


@dataclass(frozen=True, slots=True)
class RiskInput:
    required: RequiredFactors
    qr_status: FactorStatus
    pin_status: FactorStatus
    gps_status: GpsStatus
    face_status: FactorStatus
    liveness_status: FactorStatus
    allow_review_outside_geofence: bool = True
    duplicate_attendance: bool = False
    pin_attempts_exceeded: bool = False


@dataclass(slots=True)
class RiskReason:
    code: str
    factor: str
    severity: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "factor": self.factor,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass(slots=True)
class RiskOutcome:
    decision: RiskDecision
    score: int
    reasons: list[RiskReason] = field(default_factory=list)
    factor_states: dict[str, FactorStatus] = field(default_factory=dict)

    def reasons_dict(self) -> list[dict[str, str]]:
        return [reason.as_dict() for reason in self.reasons]


_MESSAGES = {
    "DUPLICATE_ATTENDANCE": "Attendance has already been recorded for this session.",
    "QR_INVALID": "The session QR token is invalid or has expired.",
    "PIN_INVALID": "The temporary PIN was not verified.",
    "PIN_ATTEMPTS_EXCEEDED": "Too many incorrect PIN attempts.",
    "FACE_MISMATCH": "Face verification did not match the enrolled identity.",
    "FACE_UNAVAILABLE": "Face verification is unavailable because no provider is configured or reachable.",
    "FACE_NOT_ENROLLED": "No authorized face enrollment exists for this student.",
    "LIVENESS_FAILED": "Liveness detection did not pass.",
    "LIVENESS_UNAVAILABLE": "Liveness detection is unavailable because no provider is configured or reachable.",
    "GPS_OUTSIDE_GEOFENCE": "Location evidence places the device outside the classroom geofence.",
    "GPS_OUTSIDE_GEOFENCE_REVIEW": "Location evidence places the device outside the classroom geofence and requires teacher review.",
    "GPS_LOW_ACCURACY": "The location fix was too imprecise to confirm proximity.",
    "GPS_UNAVAILABLE": "Location evidence was not available.",
    "GPS_PERMISSION_DENIED": "Location permission was not granted.",
    "GPS_STALE": "The location timestamp was too old or inconsistent with server time.",
    "PIN_PENDING": "PIN verification has not been completed.",
    "VERIFICATION_PENDING": "A required verification factor has not been completed.",
    "ALL_FACTORS_PASSED": "All required factors passed.",
}


def _reason(code: str, factor: str, severity: str) -> RiskReason:
    return RiskReason(code=code, factor=factor, severity=severity, message=_MESSAGES.get(code, code))


def evaluate_risk(data: RiskInput) -> RiskOutcome:
    reasons: list[RiskReason] = []
    states: dict[str, FactorStatus] = {}

    # --- Hard blocks (evidence of a failed requirement, not simply missing data)
    if data.duplicate_attendance:
        reasons.append(_reason("DUPLICATE_ATTENDANCE", "duplicate", BLOCK))

    if data.qr_status == FactorStatus.FAILED:
        reasons.append(_reason("QR_INVALID", "qr", BLOCK))
    states["qr"] = data.qr_status

    if data.pin_attempts_exceeded:
        reasons.append(_reason("PIN_ATTEMPTS_EXCEEDED", "pin", BLOCK))
    if data.required.pin:
        if data.pin_status == FactorStatus.FAILED:
            reasons.append(_reason("PIN_INVALID", "pin", BLOCK))
        elif data.pin_status == FactorStatus.PENDING_REVIEW:
            reasons.append(_reason("PIN_PENDING", "pin", REVIEW))
        states["pin"] = data.pin_status if data.pin_status != FactorStatus.PENDING else FactorStatus.PENDING_REVIEW
    else:
        states["pin"] = FactorStatus.NOT_REQUIRED

    # --- GPS / geofence
    if not data.required.geofence:
        states["gps"] = FactorStatus.NOT_REQUIRED
    else:
        states["gps"] = FactorStatus.PASSED
        if data.gps_status == GpsStatus.INSIDE_GEOFENCE:
            pass
        elif data.gps_status == GpsStatus.OUTSIDE_GEOFENCE:
            if data.allow_review_outside_geofence:
                states["gps"] = FactorStatus.PENDING_REVIEW
                reasons.append(_reason("GPS_OUTSIDE_GEOFENCE_REVIEW", "gps", REVIEW))
            else:
                states["gps"] = FactorStatus.FAILED
                reasons.append(_reason("GPS_OUTSIDE_GEOFENCE", "gps", BLOCK))
        elif data.gps_status == GpsStatus.LOW_ACCURACY:
            states["gps"] = FactorStatus.PENDING_REVIEW
            reasons.append(_reason("GPS_LOW_ACCURACY", "gps", REVIEW))
        elif data.gps_status == GpsStatus.PERMISSION_DENIED:
            states["gps"] = FactorStatus.PENDING_REVIEW
            reasons.append(_reason("GPS_PERMISSION_DENIED", "gps", REVIEW))
        elif data.gps_status == GpsStatus.STALE:
            states["gps"] = FactorStatus.PENDING_REVIEW
            reasons.append(_reason("GPS_STALE", "gps", REVIEW))
        else:
            states["gps"] = FactorStatus.PENDING_REVIEW
            reasons.append(_reason("GPS_UNAVAILABLE", "gps", REVIEW))

    # --- Face
    if not data.required.face:
        states["face"] = FactorStatus.NOT_REQUIRED
    else:
        states["face"] = data.face_status
        if data.face_status == FactorStatus.FAILED:
            reasons.append(_reason("FACE_MISMATCH", "face", BLOCK))
        elif data.face_status == FactorStatus.UNAVAILABLE:
            reasons.append(_reason("FACE_UNAVAILABLE", "face", REVIEW))
        elif data.face_status in {FactorStatus.PENDING, FactorStatus.NOT_SUBMITTED}:
            reasons.append(_reason("VERIFICATION_PENDING", "face", REVIEW))
            states["face"] = FactorStatus.PENDING_REVIEW

    # --- Liveness
    if not data.required.liveness:
        states["liveness"] = FactorStatus.NOT_REQUIRED
    else:
        states["liveness"] = data.liveness_status
        if data.liveness_status == FactorStatus.FAILED:
            reasons.append(_reason("LIVENESS_FAILED", "liveness", BLOCK))
        elif data.liveness_status == FactorStatus.UNAVAILABLE:
            reasons.append(_reason("LIVENESS_UNAVAILABLE", "liveness", REVIEW))
        elif data.liveness_status in {FactorStatus.PENDING, FactorStatus.NOT_SUBMITTED}:
            reasons.append(_reason("VERIFICATION_PENDING", "liveness", REVIEW))
            states["liveness"] = FactorStatus.PENDING_REVIEW

    blocked = any(r.severity == BLOCK for r in reasons)
    review = any(r.severity == REVIEW for r in reasons)

    if blocked:
        decision = RiskDecision.REJECTED
    elif review:
        decision = RiskDecision.REVIEW_REQUIRED
    else:
        decision = RiskDecision.ACCEPTED
        reasons.append(_reason("ALL_FACTORS_PASSED", "summary", INFO))

    score = 0
    for reason in reasons:
        if reason.severity == BLOCK:
            score += 45
        elif reason.severity == REVIEW:
            score += 20
    score = min(100, score)

    return RiskOutcome(
        decision=decision,
        score=score,
        reasons=reasons,
        factor_states=states,
    )
