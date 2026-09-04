from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from .filters import RideFilter
from .models import Ride, RideEvent, User
from .pagination import RidePagination
from .permissions import IsAdminRole
from .selectors import ride_list_queryset
from .serializers import (
    RideEventSerializer,
    RideEventWriteSerializer,
    RideReadSerializer,
    RideWriteSerializer,
    UserSerializer,
    UserWriteSerializer,
)

SIMPLE_ORDERINGS = {
    "pickup_time": "pickup_time",
    "-pickup_time": "-pickup_time",
    "distance": "distance_km",
    "-distance": "-distance_km",
}


def _float_param(request, name):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: "Must be a number."})


class RideViewSet(viewsets.ModelViewSet):
    """CRUD for rides.

    Query parameters:
      status               filter by ride status
      rider_email          exact rider email match
      rider_email_contains partial rider email match
      ordering             pickup_time | -pickup_time | distance | -distance
      pickup_lat/pickup_lng  required when ordering by distance
      radius_km            optional, enables the indexed bounding-box prefilter
      page / page_size     pagination
    """

    permission_classes = [IsAdminRole]
    pagination_class = RidePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RideFilter
    queryset = Ride.objects.all()  # for the router's basename

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RideReadSerializer
        return RideWriteSerializer

    def get_queryset(self):
        if self.action not in ("list", "retrieve"):
            return Ride.objects.all()

        latitude = _float_param(self.request, "pickup_lat")
        longitude = _float_param(self.request, "pickup_lng")
        radius_km = _float_param(self.request, "radius_km")
        ordering = self.request.query_params.get("ordering", "pickup_time")

        if ordering not in SIMPLE_ORDERINGS:
            raise ValidationError(
                {"ordering": f"Must be one of: {', '.join(SIMPLE_ORDERINGS)}."}
            )

        wants_distance = ordering in ("distance", "-distance")
        if wants_distance and (latitude is None or longitude is None):
            raise ValidationError(
                {"ordering": "pickup_lat and pickup_lng are required when ordering by distance."}
            )
        if latitude is not None and not -90 <= latitude <= 90:
            raise ValidationError({"pickup_lat": "Must be between -90 and 90."})
        if longitude is not None and not -180 <= longitude <= 180:
            raise ValidationError({"pickup_lng": "Must be between -180 and 180."})

        queryset = ride_list_queryset(
            latitude=latitude if wants_distance else None,
            longitude=longitude if wants_distance else None,
            radius_km=radius_km,
        )
        # Tiebreaker if both queries resulted with same value, will proceed with the
        # simple sort order
        return queryset.order_by(SIMPLE_ORDERINGS[ordering], "id_ride")


class RideEventViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    pagination_class = RidePagination
    queryset = RideEvent.objects.select_related("id_ride").order_by("-created_at")

    def get_serializer_class(self):
        return RideEventSerializer if self.action in ("list", "retrieve") else RideEventWriteSerializer


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    pagination_class = RidePagination
    queryset = User.objects.all().order_by("id_user")

    def get_serializer_class(self):
        return UserSerializer if self.action in ("list", "retrieve") else UserWriteSerializer
