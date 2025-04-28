from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    message = "Only owner can access this endpoint"
    def has_object_permission(self, request, view, obj):
        # The model that uses this permission must have 'profile.user' field.
        return obj.profile.user == request.user

