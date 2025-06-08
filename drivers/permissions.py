from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsDriverOwner(BasePermission):
    message = "Only owner can access this endpoint"

    def has_object_permission(self, request, view, obj):
        return obj.profile.user == request.user


class IsDriver(permissions.BasePermission):
    """
    Permission that checks if the request contains a driver token
    """
    message = "Driver authentication required"

    def has_permission(self, request, view):
        # Check if request has a driver attached (set by DriverJWTAuthentication)
        return hasattr(request, 'driver') and request.driver is not None


class IsDriverOrManager(permissions.BasePermission):
    """
    Permission that allows access to either authenticated managers or drivers
    """

    def has_permission(self, request, view):
        # Allow authenticated users (managers)
        if request.user and request.user.is_authenticated:
            return True

        # Allow authenticated drivers
        if hasattr(request, 'driver') and request.driver is not None:
            return True

        return False
