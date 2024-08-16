from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Vehicle
from .pagination import CustomPageNumberPagination
from .permissions import IsVehicleOwner
from .serializers import VehicleSerializer


class VehiclesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vehicles = Vehicle.objects.filter(profile__user=request.user).order_by("pk")
        paginator = CustomPageNumberPagination()
        paginated_vehicles = paginator.paginate_queryset(vehicles, request)
        serializer = VehicleSerializer(paginated_vehicles, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = VehicleSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        raise ValidationError(detail=serializer.errors)


class VehicleDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVehicleOwner]

    def get_object(self, pk):
        try:
            return Vehicle.objects.get(id=pk)
        except Vehicle.DoesNotExist:
            raise NotFound(detail="Vehicle does not exist.")

    def check_object_permissions(self, request, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(request, message=getattr(permission, "message", None))

    def get(self, request, pk):
        vehicle = self.get_object(pk)
        self.check_object_permissions(request, vehicle)
        serializer = VehicleSerializer(vehicle)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        vehicle = self.get_object(pk)
        self.check_object_permissions(request, vehicle)
        serializer = VehicleSerializer(vehicle, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        vehicle = self.get_object(pk)
        self.check_object_permissions(request, vehicle)
        vehicle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
