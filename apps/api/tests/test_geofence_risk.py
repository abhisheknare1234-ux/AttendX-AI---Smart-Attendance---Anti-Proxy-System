"""Pure geofence and risk-engine tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import FactorStatus, GpsStatus, RiskDecision
from app.services.geofence import GeofenceConfig, evaluate_location, haversine_m
from app.services.risk import RequiredFactors, RiskInput, evaluate_risk

CONFIG = GeofenceConfig(
    center_latitude=18.5204, center_longitude=73.8567, radius_m=80, max_accuracy_m=100
)
NOW = datetime.now(timezone.utc)


def test_haversine_distance_is_metres():
    # ~0.0001 degrees of latitude is ~11.1 m.
    distance = haversine_m(18.5204, 73.8567, 18.5205, 73.8567)
    assert 10 < distance < 13


def test_location_inside_geofence():
    evidence = evaluate_location(
        config=CONFIG,
        latitude=18.5205,
        longitude=73.8568,
        accuracy_m=20,
        client_timestamp=NOW,
        server_received_at=NOW,
    )
    assert evidence.status == GpsStatus.INSIDE_GEOFENCE
    assert evidence.distance_m is not None and evidence.distance_m < 80


def test_location_outside_geofence():
    evidence = evaluate_location(
        config=CONFIG,
        latitude=18.5300,
        longitude=73.8567,
        accuracy_m=20,
        client_timestamp=NOW,
        server_received_at=NOW,
    )
    assert evidence.status == GpsStatus.OUTSIDE_GEOFENCE
    assert evidence.distance_m > 80


def test_location_low_accuracy_takes_precedence():
    evidence = evaluate_location(
        config=CONFIG,
        latitude=18.5205,
        longitude=73.8568,
        accuracy_m=500,
        client_timestamp=NOW,
        server_received_at=NOW,
    )
    assert evidence.status == GpsStatus.LOW_ACCURACY


def test_location_stale_timestamp():
    evidence = evaluate_location(
        config=CONFIG,
        latitude=18.5205,
        longitude=73.8568,
        accuracy_m=20,
        client_timestamp=NOW - timedelta(minutes=10),
        server_received_at=NOW,
    )
    assert evidence.status == GpsStatus.STALE


def test_location_permission_and_unavailable_are_not_cheating():
    denied = evaluate_location(
        config=CONFIG,
        latitude=None,
        longitude=None,
        accuracy_m=None,
        client_timestamp=None,
        server_received_at=NOW,
        permission_denied=True,
    )
    assert denied.status == GpsStatus.PERMISSION_DENIED
    unavailable = evaluate_location(
        config=CONFIG,
        latitude=None,
        longitude=None,
        accuracy_m=None,
        client_timestamp=None,
        server_received_at=NOW,
        unavailable=True,
    )
    assert unavailable.status == GpsStatus.UNAVAILABLE


def _input(**overrides) -> RiskInput:
    base = dict(
        required=RequiredFactors(pin=True, geofence=True, face=False, liveness=False),
        qr_status=FactorStatus.PASSED,
        pin_status=FactorStatus.PASSED,
        gps_status=GpsStatus.INSIDE_GEOFENCE,
        face_status=FactorStatus.NOT_REQUIRED,
        liveness_status=FactorStatus.NOT_REQUIRED,
    )
    base.update(overrides)
    return RiskInput(**base)


def test_all_factors_accept():
    outcome = evaluate_risk(_input())
    assert outcome.decision == RiskDecision.ACCEPTED
    assert outcome.score == 0
    assert any(reason.code == "ALL_FACTORS_PASSED" for reason in outcome.reasons)


def test_outside_geofence_review_by_default():
    outcome = evaluate_risk(_input(gps_status=GpsStatus.OUTSIDE_GEOFENCE))
    assert outcome.decision == RiskDecision.REVIEW_REQUIRED
    assert outcome.score == 20
    assert "GPS_OUTSIDE_GEOFENCE_REVIEW" in [r.code for r in outcome.reasons]


def test_outside_geofence_reject_when_review_disabled():
    outcome = evaluate_risk(
        _input(gps_status=GpsStatus.OUTSIDE_GEOFENCE, allow_review_outside_geofence=False)
    )
    assert outcome.decision == RiskDecision.REJECTED


def test_missing_gps_permission_goes_to_review():
    outcome = evaluate_risk(_input(gps_status=GpsStatus.PERMISSION_DENIED))
    assert outcome.decision == RiskDecision.REVIEW_REQUIRED
    assert any(reason.code == "GPS_PERMISSION_DENIED" for reason in outcome.reasons)


def test_required_face_provider_unavailable_is_review_not_rejection():
    outcome = evaluate_risk(
        _input(
            required=RequiredFactors(pin=True, geofence=True, face=True, liveness=False),
            face_status=FactorStatus.UNAVAILABLE,
        )
    )
    assert outcome.decision == RiskDecision.REVIEW_REQUIRED
    assert any(reason.code == "FACE_UNAVAILABLE" for reason in outcome.reasons)


def test_face_mismatch_is_rejected():
    outcome = evaluate_risk(
        _input(
            required=RequiredFactors(pin=True, geofence=True, face=True, liveness=False),
            face_status=FactorStatus.FAILED,
        )
    )
    assert outcome.decision == RiskDecision.REJECTED


def test_liveness_failure_is_rejected():
    outcome = evaluate_risk(
        _input(
            required=RequiredFactors(pin=True, geofence=True, face=True, liveness=True),
            face_status=FactorStatus.PASSED,
            liveness_status=FactorStatus.FAILED,
        )
    )
    assert outcome.decision == RiskDecision.REJECTED


def test_duplicate_attendance_blocks():
    outcome = evaluate_risk(_input(duplicate_attendance=True))
    assert outcome.decision == RiskDecision.REJECTED


def test_pin_failure_is_rejected_and_scores_are_explainable():
    outcome = evaluate_risk(_input(pin_status=FactorStatus.FAILED))
    assert outcome.decision == RiskDecision.REJECTED
    assert outcome.score > 0
    assert outcome.factor_states["pin"] == FactorStatus.FAILED
    assert all({"code", "factor", "severity", "message"} <= set(r.as_dict()) for r in outcome.reasons)
