from rest_framework import serializers

from .models import Ride, RideEvent, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id_user", "role", "first_name", "last_name", "email", "phone_number"]


class RideEventSerializer(serializers.ModelSerializer):
    id_ride = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = RideEvent
        fields = ["id_ride_event", "id_ride", "description", "created_at"]


class RideReadSerializer(serializers.ModelSerializer):
    id_rider = UserSerializer(read_only=True)
    id_driver = UserSerializer(read_only=True)
    todays_ride_events = RideEventSerializer(source="todays_events", many=True, read_only=True)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            "id_ride",
            "status",
            "id_rider",
            "id_driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
            "todays_ride_events",
            "distance_km",
        ]

    def get_distance_km(self, obj):
        """Only present when the caller asked for a distance sort."""
        distance = getattr(obj, "distance_km", None)
        return round(distance, 3) if distance is not None else None


class RideWriteSerializer(serializers.ModelSerializer):
    """Plain PK input for create/update. Keeping read and write shapes separate
    avoids the usual nested-writable-serializer mess."""

    class Meta:
        model = Ride
        fields = [
            "id_ride",
            "status",
            "id_rider",
            "id_driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
        ]
        read_only_fields = ["id_ride"]

    def validate(self, attrs):
        rider = attrs.get("id_rider") or getattr(self.instance, "id_rider", None)
        driver = attrs.get("id_driver") or getattr(self.instance, "id_driver", None)
        if rider and driver and rider.pk == driver.pk:
            raise serializers.ValidationError("A ride cannot have the same user as rider and driver.")
        return attrs


class RideEventWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideEvent
        fields = ["id_ride_event", "id_ride", "description", "created_at"]
        read_only_fields = ["id_ride_event"]


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id_user", "role", "first_name", "last_name", "email", "phone_number", "password"]
        read_only_fields = ["id_user"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
