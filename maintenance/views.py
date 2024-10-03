import datetime

from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Part, ServiceProvider, PartsProvider, PartPurchaseEvent, MaintenanceReport, MaintenanceChoices, ServiceChoices
from .serializers import PartSerializer, ServiceProviderSerializer, PartsProviderSerializer, PartPurchaseEventSerializer, MaintenanceReportSerializer


# Create your views here.

class PartsListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        parts = Part.objects.all().order_by('name')
        serializer = PartSerializer(parts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PartSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class PartDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk):
        try:
            return Part.objects.get(id=pk)
        except Part.DoesNotExist:
            raise NotFound(detail="Part does not exist")

    def get(self, request, pk):
        part = self.get_object(pk)
        serializer = PartSerializer(part)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        part = self.get_object(pk)
        serializer = PartSerializer(part, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        part = self.get_object(pk)
        part.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ServiceProviderListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        providers = ServiceProvider.objects.all().order_by('name')
        serializer = ServiceProviderSerializer(providers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ServiceProviderSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class ServiceProviderDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk):
        try:
            return ServiceProvider.objects.get(id=pk)
        except ServiceProvider.DoesNotExist:
            raise NotFound(detail="Service Provider does not exist")

    def get(self, request, pk):
        provider = self.get_object(pk)
        serializer = ServiceProviderSerializer(provider)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        provider = self.get_object(pk)
        serializer = ServiceProviderSerializer(provider, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        provider = self.get_object(pk)
        provider.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PartsProvidersListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        parts_providers = PartsProvider.objects.all().order_by('name')
        serializer = PartsProviderSerializer(parts_providers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PartsProviderSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class PartsProviderDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk):
        try:
            return PartsProvider.objects.get(id=pk)
        except PartsProvider.DoesNotExist:
            raise NotFound(detail="Part Provider does not exist")

    def get(self, request, pk):
        provider = self.get_object(pk)
        serializer = PartsProviderSerializer(provider)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        provider = self.get_object(pk)
        serializer = PartsProviderSerializer(provider, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        provider = self.get_object(pk)
        provider.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PartPurchaseEventsListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        part_purchase_events = PartPurchaseEvent.objects.filter(profile__user=request.user).order_by('purchase_date')
        paginator = PageNumberPagination()
        paginated_part_purchase_events = paginator.paginate_queryset(part_purchase_events, request)
        serializer = PartPurchaseEventSerializer(paginated_part_purchase_events, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = PartPurchaseEventSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class PartPurchaseEventDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk, user):
        try:
            return PartPurchaseEvent.objects.get(pk=pk, profile__user=user)

        except PartPurchaseEvent.DoesNotExist:
            raise NotFound(detail="Part purchase even does not exist")

    def get(self, request, pk):
        part_purchase_event = self.get_object(pk, request.user)
        serializer = PartPurchaseEventSerializer(part_purchase_event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        part_purchase_event = self.get_object(pk, request.user)
        serializer = PartPurchaseEventSerializer(part_purchase_event, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        part_purchase_event = self.get_object(pk, request.user)
        part_purchase_event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaintenanceReportListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        maintenance_reports = MaintenanceReport.objects.filter(profile__user=request.user).order_by('start_date')
        paginator = PageNumberPagination()
        paginated_maintenance_reports = paginator.paginate_queryset(maintenance_reports, request)
        serializer = MaintenanceReportSerializer(paginated_maintenance_reports, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = MaintenanceReportSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


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
        serializer = MaintenanceReportSerializer(maintenance_report, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        maintenance_report = self.get_object(pk, request.user)
        maintenance_report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaintenanceReportOverviewView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_maintenance_report(self, month=None, year=None, user=None):
        if year:
            total_maintenance_reports = MaintenanceReport.objects.filter(profile=user, start_date__year=year)
        elif month:
            total_maintenance_reports = MaintenanceReport.objects.filter(profile=user, start_date__month=month)
        else:
            total_maintenance_reports = MaintenanceReport.objects.all()

        report = {
            "total_maintenance": len(total_maintenance_reports),
            "total_maintenance_cost": 0,
            "preventive": 0,
            "preventive_cost": 0,
            "curative": 0,
            "curative_cost": 0,
            "total_service_cost": 0,
            "mechanic": 0,
            "electrician": 0,
            "cleaning": 0
        }
        for maintenance_report in total_maintenance_reports:
            report["total_maintenance_cost"] += maintenance_report.total_cost
            report["preventive"] += (1 if maintenance_report.maintenance_type == MaintenanceChoices.PREVENTIVE else 0)
            report["preventive_cost"] += (
                maintenance_report.total_cost if maintenance_report.maintenance_type == MaintenanceChoices.PREVENTIVE else 0)
            report["curative"] += (1 if maintenance_report.maintenance_type == MaintenanceChoices.CURATIVE else 0)
            report["curative_cost"] += (maintenance_report.total_cost if maintenance_report.maintenance_type == MaintenanceChoices.CURATIVE else 0)
            report["total_service_cost"] += maintenance_report.cost
            report["mechanic"] += (maintenance_report.cost if maintenance_report.service_provider.service_type == ServiceChoices.MECHANIC else 0)
            report["electrician"] += (
                maintenance_report.cost if maintenance_report.service_provider.service_type == ServiceChoices.ELECTRICIAN else 0)
            report["cleaning"] += (maintenance_report.cost if maintenance_report.service_provider.service_type == ServiceChoices.CLEANING else 0)

        return report

    def get(self, request):
        year = request.GET.get('year')
        month = request.GET.get('month')

        if year:
            report_of_current_year = self.get_maintenance_report(year=year, user=request.user.userprofile)
            report_of_previous_year = self.get_maintenance_report(year=year - 1, user=request.user.userprofile)
            return Response({"previous_year": report_of_previous_year, "current_year": report_of_current_year}, status=status.HTTP_200_OK)

        if month:
            year = datetime.date.today().year
            report_of_current_month = self.get_maintenance_report(month=month, user=request.user.userprofile)
            report_of_previous_month = self.get_maintenance_report(month=12, year=year - 1,
                                                                   user=request.user.userprofile) if month == 1 else self.get_maintenance_report(
                month=month, year=year, user=request.user.userprofile)
            return Response({"previous_month": report_of_previous_month, "current_month": report_of_current_month}, status=status.HTTP_200_OK)


class GeneralMaintenanceDataView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        serialized_parts = PartSerializer(Part.objects.all(), many=True, context={'request': request})
        serialized_service_providers = ServiceProviderSerializer(ServiceProvider.objects.all(), many=True, context={'request': request})
        serialized_parts_providers = PartsProviderSerializer(PartsProvider.objects.all(), many=True, context={'request': request})
        return Response(
            {"parts": serialized_parts.data,
             "service_providers": serialized_service_providers.data,
             "part_providers": serialized_parts_providers.data
             },
            status=status.HTTP_200_OK)
