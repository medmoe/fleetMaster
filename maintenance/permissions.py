from rest_framework.permissions import BasePermission


class IsPartPurchaseEventOwner(BasePermission):
    message = "Only owner can access this endpoint"

    def has_object_permission(self, request, view, obj):
        return obj.profile.user == request.user
