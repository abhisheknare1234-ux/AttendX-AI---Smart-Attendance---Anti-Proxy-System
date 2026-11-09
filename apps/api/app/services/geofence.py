"""Geospatial evidence evaluation (pure functions, no I/O)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from app.core.timeutil import ensure_utc
from app.models import GpsStatus

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(min(1.0, sqrt(a)))


@dataclass(frozen=True, slots=True)
class GeofenceConfig:
    center_latitude: float
    center_longitude: float
    radius_m: float = 60.0
    max_accuracy_m: float = 100.0


@dataclass(slots=True)
class LocationEvidence:
    status: GpsStatus
    distance_m: float | None = None
    accuracy_m: float | None = None
    reason_code: str | None = None
    recorded_at: datetime | None = None
    details: dict = field(default_factory=dict)


def evaluate_location(
    *,
    config: GeofenceConfig,
    latitude: float | None,
    longitude: float | None,
    accuracy_m: float | None,
    client_timestamp: datetime | None,
    server_received_at: datetime,
    stale_after_seconds: int = 120,
    permission_denied: bool = False,
    unavailable: bool = False,
) -> LocationEvidence:
    """Classify browser location evidence.

    GPS is treated as *evidence*, never as proof of exact classroom presence.
    Missing permission or a weak fix is not evidence of misconduct; the risk
    engine decides whether that becomes a review or a rejection.
    """
    if permission_denied:
        return LocationEvidence(
            status=GpsStatus.PERMISSION_DENIED,
            reason_code="GPS_PERMISSION_DENIED",
            details={"message": "Location permission was denied by the browser."},
        )
    if unavailable or latitude is None or longitude is None:
        return LocationEvidence(
            status=GpsStatus.UNAVAILABLE,
            reason_code="GPS_UNAVAILABLE",
            details={"message": "No location fix was available."},
        )

    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return LocationEvidence(
            status=GpsStatus.UNAVAILABLE,
            reason_code="GPS_INVALID_COORDINATES",
        )

    if client_timestamp is not None:
        skew = abs((ensure_utc(server_received_at) - ensure_utc(client_timestamp)).total_seconds())
        if skew > stale_after_seconds:
            return LocationEvidence(
                status=GpsStatus.STALE,
                distance_m=None,
                accuracy_m=accuracy_m,
                reason_code="GPS_STALE",
                recorded_at=client_timestamp,
                details={"skew_seconds": round(skew, 1)},
            )

    distance = haversine_m(
        config.center_latitude, config.center_longitude, latitude, longitude
    )

    if accuracy_m is None or accuracy_m < 0:
        return LocationEvidence(
            status=GpsStatus.LOW_ACCURACY,
            distance_m=round(distance, 1),
            accuracy_m=accuracy_m,
            reason_code="GPS_ACCURACY_UNKNOWN",
            recorded_at=client_timestamp,
        )

    if accuracy_m > config.max_accuracy_m:
        return LocationEvidence(
            status=GpsStatus.LOW_ACCURACY,
            distance_m=round(distance, 1),
            accuracy_m=accuracy_m,
            reason_code="GPS_ACCURACY_TOO_LOW",
            recorded_at=client_timestamp,
            details={"max_accuracy_m": config.max_accuracy_m},
        )

    if distance > config.radius_m:
        return LocationEvidence(
            status=GpsStatus.OUTSIDE_GEOFENCE,
            distance_m=round(distance, 1),
            accuracy_m=accuracy_m,
            reason_code="GPS_OUTSIDE_GEOFENCE",
            recorded_at=client_timestamp,
            details={
                "radius_m": config.radius_m,
                "distance_m": round(distance, 1),
            },
        )

    return LocationEvidence(
        status=GpsStatus.INSIDE_GEOFENCE,
        distance_m=round(distance, 1),
        accuracy_m=accuracy_m,
        recorded_at=client_timestamp,
        details={"radius_m": config.radius_m},
    )
