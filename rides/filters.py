import django_filters as filters

from .models import Ride


class RideFilter(filters.FilterSet):
    """Filtering by ride status and by rider email.
    `rider_email` lookup the FK, which Django resolves as a JOIN on the
    already-joined user table. It adds no extra query.
    """

    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    rider_email = filters.CharFilter(field_name="id_rider__email", lookup_expr="iexact")
    rider_email_contains = filters.CharFilter(field_name="id_rider__email", lookup_expr="icontains")

    class Meta:
        model = Ride
        fields = ["status", "rider_email", "rider_email_contains"]
