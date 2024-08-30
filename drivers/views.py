from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Driver
from .pagination import CustomPageNumberPagination
from .permissions import IsDriverOwner
from .serializers import DriverSerializer


class DriversListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        drivers = Driver.objects.filter(profile__user=request.user).order_by("pk")

        paginator = CustomPageNumberPagination()
        paginated_drivers = paginator.paginate_queryset(drivers, request)
        serializer = DriverSerializer(paginated_drivers, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = DriverSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class DriversDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDriverOwner]

    def get_object(self, pk):
        try:
            return Driver.objects.get(id=pk)
        except Driver.DoesNotExist:
            raise NotFound(detail="Driver does not exist.")

    def check_object_permissions(self, request, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(request, message=getattr(permission, "message", None))

    def get(self, request, pk):
        driver = self.get_object(pk)
        self.check_object_permissions(request, driver)
        serializer = DriverSerializer(driver)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        driver = self.get_object(pk)
        self.check_object_permissions(request, driver)
        serializer = DriverSerializer(driver, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        driver = self.get_object(pk)
        self.check_object_permissions(request, driver)
        driver.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
