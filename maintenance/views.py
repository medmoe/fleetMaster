import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Part, ServiceProvider, PartsProvider, PartPurchaseEvent, MaintenanceReport
from .serializers import PartSerializer, ServiceProviderSerializer, PartsProviderSerializer, \
    PartPurchaseEventSerializer, MaintenanceReportSerializer
from .utils import ReportSummarizer


# Constants
DAYS_IN_A_WEEK = 7
DAYS_IN_TWO_WEEKS = 14
DAYS_IN_FOUR_WEEKS = 28
DAYS_IN_THREE_MONTHS = 90
DAYS_IN_A_YEAR = 365

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
        serializer = PartPurchaseEventSerializer(paginated_part_purchase_events, many=True,
                                                 context={"request": request})
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

class PartPurchaseEventBulkOperations(APIView):
    def delete(self, request):
        ids_params = request.query_params.get('ids', None)
        if not ids_params:
            return Response(status=status.HTTP_204_NO_CONTENT)
        try:
            ids = [int(id) for id in ids_params.split(',')]
        except ValueError:
            return Response(data={"Error": "Invalid IDs format"}, status=status.HTTP_400_BAD_REQUEST)

        events_to_delete = PartPurchaseEvent.objects.filter(id__in=ids)
        deleted_count, _ = events_to_delete.delete()
        if deleted_count == 0:
            return Response({"Error", "No matching records found"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"Message": f"{deleted_count} records deleted successfully"}, status=status.HTTP_200_OK)

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

    def fetch_and_summarize_reports(self):
        start_date = timezone.now() - datetime.timedelta(days=DAYS_IN_A_YEAR)
        current_report = MaintenanceReport.objects.filter(start_date__gte=start_date).prefetch_related('parts')
        previous_report = MaintenanceReport.objects.filter(start_date__lt=start_date)
        all_part_purchase_events = []
        for report in current_report:
            part_purchase_events = report.parts.all()
            serialize_events = PartPurchaseEventSerializer(part_purchase_events, many=True).data
            all_part_purchase_events.extend(serialize_events)

        return {
            "previous_report": ReportSummarizer().summarize_reports(previous_report),
            "current_report": ReportSummarizer().summarize_reports(current_report),
            "part_purchase_events": all_part_purchase_events,
        }

    def get(self, request):
        summarized_data = self.fetch_and_summarize_reports()
        return Response(summarized_data, status=status.HTTP_200_OK)


class GeneralMaintenanceDataView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        serialized_parts = PartSerializer(Part.objects.all(), many=True, context={'request': request})
        serialized_service_providers = ServiceProviderSerializer(ServiceProvider.objects.all(), many=True,
                                                                 context={'request': request})
        serialized_parts_providers = PartsProviderSerializer(PartsProvider.objects.all(), many=True,
                                                             context={'request': request})
        return Response(
            {"parts": serialized_parts.data,
             "service_providers": serialized_service_providers.data,
             "part_providers": serialized_parts_providers.data
             },
            status=status.HTTP_200_OK)
