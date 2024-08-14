from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Driver
from .pagination import CustomPageNumberPagination
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
    pass
