import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from rides.models import Ride, RideEvent, User


class Command(BaseCommand):
    help = "Create demo users, rides and ride events for local testing."

    def add_arguments(self, parser):
        parser.add_argument("--rides", type=int, default=200)

    def handle(self, *args, **options):
        random.seed(42)
        admin, created = User.objects.get_or_create(
            email="admin@wingz.test",
            defaults={"role": User.Role.ADMIN, "first_name": "Ada", "last_name": "Admin",
                      "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin12345")
            admin.save()

        drivers = [
            User.objects.get_or_create(
                email=f"driver{i}@wingz.test",
                defaults={"role": User.Role.DRIVER, "first_name": n, "last_name": s,
                          "phone_number": f"+6391700000{i:02d}"},
            )[0]
            for i, (n, s) in enumerate([("Chris", "Halloway"), ("Howard", "Yamada"), ("Randy", "Wu")])
        ]
        riders = [
            User.objects.get_or_create(
                email=f"rider{i}@wingz.test",
                defaults={"role": User.Role.RIDER, "first_name": f"Rider{i}", "last_name": "Test",
                          "phone_number": f"+6391800000{i:02d}"},
            )[0]
            for i in range(10)
        ]

        now = timezone.now()
        statuses = [s for s, _ in Ride.Status.choices]
        created_rides = 0
        for i in range(options["rides"]):
            pickup_time = now - timedelta(hours=random.randint(0, 24 * 120))
            ride = Ride.objects.create(
                status=random.choice(statuses),
                id_rider=random.choice(riders),
                id_driver=random.choice(drivers),
                pickup_latitude=14.5995 + random.uniform(-0.6, 0.6),
                pickup_longitude=120.9842 + random.uniform(-0.6, 0.6),
                dropoff_latitude=14.5995 + random.uniform(-0.6, 0.6),
                dropoff_longitude=120.9842 + random.uniform(-0.6, 0.6),
                pickup_time=pickup_time,
            )
            created_rides += 1
            duration = timedelta(minutes=random.choice([20, 35, 61, 75, 130]))
            RideEvent.objects.create(
                id_ride=ride, description=RideEvent.PICKUP_DESCRIPTION, created_at=pickup_time
            )
            RideEvent.objects.create(
                id_ride=ride, description=RideEvent.DROPOFF_DESCRIPTION, created_at=pickup_time + duration
            )
            # A few recent events so todays_ride_events is not always empty.
            if random.random() < 0.4:
                RideEvent.objects.create(
                    id_ride=ride,
                    description="Status changed to en-route",
                    created_at=now - timedelta(hours=random.randint(0, 23)),
                )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_rides} rides. Admin login: admin@wingz.test / admin12345"
        ))
