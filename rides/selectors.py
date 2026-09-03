"""Query constructs for the Ride list endpoint.
"""
from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from .geo import bounding_box, haversine_km
from .models import Ride, RideEvent

TODAYS_EVENTS_ATTR = "todays_events"
EVENT_WINDOW = timedelta(hours=24)


def todays_events_prefetch(now=None) -> Prefetch:
    """Prefetch only the last 24 hours of RideEvents.

    The filter lives in the Prefetch queryset, so the WHERE clause is pushed
    into the database. The full RideEvent list for a ride is never loaded, which
    is the whole point once that table is large.
    Question#4
    """
    cutoff = (now or timezone.now()) - EVENT_WINDOW
    return Prefetch(
        "ride_events",
        queryset=RideEvent.objects.filter(created_at__gte=cutoff).order_by("-created_at"),
        to_attr=TODAYS_EVENTS_ATTR,
    )


def ride_list_queryset(*, latitude=None, longitude=None, radius_km=None, now=None):
    """Base queryset for the list endpoint.

    Query budget:
      1. rides + rider + driver, via select_related (one JOIN, no extra round trip)
      2. the filtered RideEvent prefetch (a single IN query for the whole page)
      (+1 COUNT issued by the paginator)
    Question#4
    """
    queryset = (
        Ride.objects.select_related("id_rider", "id_driver")
        .prefetch_related(todays_events_prefetch(now=now))
    )

    if latitude is not None and longitude is not None:
        if radius_km:
            # Initialized indexable prefilter before the non-indexable distance computation.
            queryset = queryset.filter(bounding_box(latitude, longitude, radius_km))
        queryset = queryset.annotate(distance_km=haversine_km(latitude, longitude))

    return queryset
