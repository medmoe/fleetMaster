from rest_framework.permissions import BasePermission
from accounts.models import UserProfile


class IsDriverOwner(BasePermission):
    message = "Only owner can access this endpoint"

    def has_object_permission(self, request, view, obj):
        return obj.profile.user == request.user
