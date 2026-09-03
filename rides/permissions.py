from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """authenticated users whose `role` is = 'admin' may touch the API."""

    message = "Endpoint is restricted to users with the 'admin' role."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "admin")
