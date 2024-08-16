from rest_framework.permissions import BasePermission


class IsVehicleOwner(BasePermission):
    message = "Only owner can access this endpoint"

    def has_object_permission(self, request, view, obj):
        return obj.profile.user == request.user
