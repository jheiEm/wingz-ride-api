"""Distance helpers.
ORM expressions that would facilitate the distance sorth inside the database, sorting in Python would break pagination so used LIMIT/OFFSET was applied to a resulted order-ready SQL. 

Uses Haversine method
"""
import math

from django.db.models import ExpressionWrapper, F, FloatField, Q, Value
from django.db.models.functions import ACos, Cos, Least, Radians, Sin

EARTH_RADIUS_KM = 6371.0
KM_PER_DEGREE_LAT = 111.045


def _f(value):
    return Value(float(value), output_field=FloatField())


def haversine_km(latitude: float, longitude: float):
    """Great circle distance, in km, from (latitude, longitude) to a Ride pickup point.
    """
    cosine_term = (
        Cos(Radians(_f(latitude)))
        * Cos(Radians(F("pickup_latitude")))
        * Cos(Radians(F("pickup_longitude")) - Radians(_f(longitude)))
        + Sin(Radians(_f(latitude))) * Sin(Radians(F("pickup_latitude")))
    )
    return ExpressionWrapper(
        _f(EARTH_RADIUS_KM) * ACos(Least(_f(1.0), cosine_term)),
        output_field=FloatField(),
    )


def bounding_box(latitude: float, longitude: float, radius_km: float) -> Q:
    """An indexable prefilter around a point.
    """
    delta_lat = radius_km / KM_PER_DEGREE_LAT
    cos_lat = max(math.cos(math.radians(latitude)), 1e-6)
    delta_lng = radius_km / (KM_PER_DEGREE_LAT * cos_lat)
    return Q(
        pickup_latitude__gte=latitude - delta_lat,
        pickup_latitude__lte=latitude + delta_lat,
        pickup_longitude__gte=longitude - delta_lng,
        pickup_longitude__lte=longitude + delta_lng,
    )
