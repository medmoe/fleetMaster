from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from maintenance.models import MaintenanceReport
from maintenance.pagination import MonthlyPagination
from maintenance.serializers import MaintenanceReportSerializer
from vehicles.models import Vehicle


class MaintenanceReportListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        reports = MaintenanceReport.objects.filter(profile__user=request.user).order_by("start_date")
        paginator = PageNumberPagination()
        paginated_reports = paginator.paginate_queryset(reports, request)
        serializer = MaintenanceReportSerializer(paginated_reports, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = MaintenanceReportSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class VehicleReportsListView(APIView):
    permission_classes = [IsAuthenticated, ]
    def get_vehicle(self, pk, user):
        try:
            return Vehicle.objects.get(pk=pk, profile__user=user)
        except Vehicle.DoesNotExist:
            raise ValidationError(detail={"Vehicle does not exist!"})

    def get(self, request, pk):
        vehicle = self.get_vehicle(pk, request.user)
        reports = MaintenanceReport.objects.filter(profile__user=request.user, vehicle=vehicle).order_by("start_date")
        paginator = MonthlyPagination()
        paginated_reports = paginator.paginate_queryset(reports, request)
        serializer = MaintenanceReportSerializer(paginated_reports, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

class MaintenanceReportDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk, user):
        try:
            return MaintenanceReport.objects.get(pk=pk, profile__user=user)
        except MaintenanceReport.DoesNotExist:
            raise NotFound(detail="Maintenance report does not exist")

    def get(self, request, pk):
        maintenance_report = self.get_object(pk, request.user)
        serializer = MaintenanceReportSerializer(maintenance_report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        maintenance_report = self.get_object(pk, request.user)
        serializer = MaintenanceReportSerializer(maintenance_report, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            with transaction.atomic():
                maintenance_report = self.get_object(pk, request.user)
                maintenance_report.part_purchase_events.all().delete()
                maintenance_report.service_provider_events.all().delete()
                maintenance_report.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
