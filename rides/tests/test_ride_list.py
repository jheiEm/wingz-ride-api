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

    def test_todays_events_only_contains_last_24_hours(self):
        response = self.client.get(self.url)
        for ride in response.data["results"]:
            descriptions = [e["description"] for e in ride["todays_ride_events"]]
            self.assertEqual(descriptions, ["recent"])

    def test_nested_rider_and_driver_are_expanded(self):
        ride = self.client.get(self.url).data["results"][0]
        self.assertEqual(ride["id_rider"]["email"], "rider@example.com")
        self.assertEqual(ride["id_driver"]["email"], "driver@example.com")

    def test_filter_by_status_and_rider_email(self):
        response = self.client.get(self.url, {"status": "pickup"})
        self.assertTrue(all(r["status"] == "pickup" for r in response.data["results"]))
        self.assertEqual(
            self.client.get(self.url, {"rider_email": "nobody@example.com"}).data["count"], 0
        )
        self.assertEqual(
            self.client.get(self.url, {"rider_email": "rider@example.com"}).data["count"], 5
        )

    def test_sort_by_pickup_time(self):
        times = [r["pickup_time"] for r in self.client.get(self.url, {"ordering": "pickup_time"}).data["results"]]
        self.assertEqual(times, sorted(times))
        times = [r["pickup_time"] for r in self.client.get(self.url, {"ordering": "-pickup_time"}).data["results"]]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_list_uses_three_queries(self):
        """1 ride+joins, 1 prefetch, 1 count. force_authenticate avoids a
        token lookup query that would otherwise inflate this number."""
        with self.assertNumQueries(3):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data["results"]), 5)

    def test_query_count_is_constant_as_rides_grow(self):
        for i in range(20):
            ride = Ride.objects.create(
                status=Ride.Status.DROPOFF, id_rider=self.plain, id_driver=self.driver,
                pickup_latitude=10.0, pickup_longitude=120.0,
                dropoff_latitude=10.0, dropoff_longitude=120.0,
                pickup_time=self.now,
            )
            RideEvent.objects.create(id_ride=ride, description="recent", created_at=self.now)
        with self.assertNumQueries(3):
            self.client.get(self.url, {"page_size": 25})
    def test_sort_by_distance_is_ascending_from_origin(self):
        response = self.client.get(
            self.url, {"ordering": "distance", "pickup_lat": 14.5, "pickup_lng": 120.9}
        )
        distances = [r["distance_km"] for r in response.data["results"]]
        self.assertEqual(distances, sorted(distances))
        self.assertAlmostEqual(distances[0], 0.0, places=3)

    def test_distance_sort_survives_pagination(self):
        first = self.client.get(
            self.url, {"ordering": "distance", "pickup_lat": 14.5, "pickup_lng": 120.9, "page_size": 2}
        ).data
        second = self.client.get(
            self.url,
            {"ordering": "distance", "pickup_lat": 14.5, "pickup_lng": 120.9, "page_size": 2, "page": 2},
        ).data
        self.assertEqual(first["count"], 5)
        self.assertEqual(len(first["results"]), 2)
        self.assertLessEqual(first["results"][-1]["distance_km"], second["results"][0]["distance_km"])

    def test_distance_sort_requires_coordinates(self):
        self.assertEqual(self.client.get(self.url, {"ordering": "distance"}).status_code, 400)

    def test_invalid_ordering_is_rejected(self):
        self.assertEqual(self.client.get(self.url, {"ordering": "banana"}).status_code, 400)

    def test_invalid_latitude_is_rejected(self):
        response = self.client.get(
            self.url, {"ordering": "distance", "pickup_lat": 999, "pickup_lng": 120.9}
        )
        self.assertEqual(response.status_code, 400)

    def test_radius_filter_narrows_results(self):
        response = self.client.get(
            self.url,
            {"ordering": "distance", "pickup_lat": 14.5, "pickup_lng": 120.9, "radius_km": 50},
        )
        self.assertEqual(response.data["count"], 1)
