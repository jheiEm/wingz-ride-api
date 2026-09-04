from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from rides.models import Ride, RideEvent, User


class RideListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.now = timezone.now()
        cls.admin = User.objects.create_user(
            email="admin@example.com", password="pw", role=User.Role.ADMIN,
            first_name="Ada", last_name="Admin",
        )
        cls.plain = User.objects.create_user(
            email="rider@example.com", password="pw", role=User.Role.RIDER,
            first_name="Rita", last_name="Rider",
        )
        cls.driver = User.objects.create_user(
            email="driver@example.com", password="pw", role=User.Role.DRIVER,
            first_name="Dan", last_name="Driver",
        )
        for i in range(5):
            ride = Ride.objects.create(
                status=Ride.Status.EN_ROUTE if i % 2 else Ride.Status.PICKUP,
                id_rider=cls.plain, id_driver=cls.driver,
                pickup_latitude=14.5 + i, pickup_longitude=120.9 + i,
                dropoff_latitude=14.0, dropoff_longitude=121.0,
                pickup_time=cls.now - timedelta(hours=i),
            )
            RideEvent.objects.create(
                id_ride=ride, description="recent", created_at=cls.now - timedelta(hours=1)
            )
            RideEvent.objects.create(
                id_ride=ride, description="old", created_at=cls.now - timedelta(days=5)
            )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    @property
    def url(self):
        return reverse("ride-list")

    def test_non_admin_is_rejected(self):
        self.client.force_authenticate(self.plain)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)