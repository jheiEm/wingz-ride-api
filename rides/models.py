from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

class UserManager(BaseUserManager):
    """Email is the login field, so the default UserManager will not do."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        DRIVER = "driver", "Driver"
        RIDER = "rider", "Rider"

    id_user = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RIDER, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=32, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN

class Ride(models.Model):
    class Status(models.TextChoices):
        EN_ROUTE = "en-route", "En route"
        PICKUP = "pickup", "Pickup"
        DROPOFF = "dropoff", "Dropoff"

    id_ride = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    id_rider = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="rides_as_rider", db_column="id_rider"
    )
    id_driver = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="rides_as_driver", db_column="id_driver"
    )
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride"
        indexes = [
            models.Index(fields=["pickup_latitude", "pickup_longitude"], name="ride_pickup_geo_idx"),
            models.Index(fields=["status", "pickup_time"], name="ride_status_time_idx"),
        ]

    def __str__(self):
        return f"Ride #{self.id_ride} ({self.status})"