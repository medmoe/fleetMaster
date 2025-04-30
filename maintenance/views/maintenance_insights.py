import datetime
import heapq
from collections import defaultdict

from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import vehicles
from maintenance.models import MaintenanceReport, Part, ServiceProvider, PartsProvider
from maintenance.serializers import MaintenanceReportSerializer, PartSerializer, ServiceProviderSerializer, PartsProviderSerializer
from vehicles.models import Vehicle


class MaintenanceReportOverviewView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self, request):
        """
        Fetch maintenance reports for the current and previous years of a given vehicle.
        """
        current_year = now().year
        previous_start_date = datetime.date(current_year - 1, 1, 1)
        vehicle_id = request.query_params.get('vehicle_id', None)

        if not vehicle_id or not vehicle_id.isdigit():
            raise ValidationError(detail={"vehicle_id": "Vehicle ID is required"})

        # Combine the conditions for current and previous year
        reports_queryset = MaintenanceReport.objects.filter(
            profile__user=self.request.user,
            vehicle=vehicle_id,
            start_date__gte=previous_start_date  # Covers both previous and current year start dates
        ).order_by("start_date")  # Sort by start date chronologically

        return reports_queryset

    def get(self, request):
        report_queryset = self.get_queryset(request)
        reports_serializer = MaintenanceReportSerializer(report_queryset, many=True, context={'request': request})
        return Response(reports_serializer.data, status=status.HTTP_200_OK)


class GeneralMaintenanceDataView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        serialized_parts = PartSerializer(Part.objects.all(), many=True, context={'request': request})
        serialized_service_providers = ServiceProviderSerializer(ServiceProvider.objects.all(), many=True, context={'request': request})
        serialized_parts_providers = PartsProviderSerializer(PartsProvider.objects.all(), many=True, context={'request': request})
        response_data = {"parts": serialized_parts.data, "service_providers": serialized_service_providers.data,
                         "part_providers": serialized_parts_providers.data}
        return Response(response_data, status=status.HTTP_200_OK)


class FleetWideOverviewView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        data = {"total_maintenance_spend": {"year": 0, "month": 0, "quarter": 0},
                "YoY": 0.0,
                "vehicle_avg_cost": 0.0,
                "vehicle_avg_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
                "vehicle_insurance_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
                "vehicle_license_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
                "top_recurring_issues":[],
                }

        # Core analytics
        current_year = now().year
        current_month = now().month
        current_quarter = (current_month - 1) // 3 + 1
        current_year_reports = MaintenanceReport.objects.filter(start_date__year=current_year, profile__user=request.user)
        part_counter = defaultdict(int)
        for report in current_year_reports:
            data["total_maintenance_spend"]["year"] += report.total_cost
            data["total_maintenance_spend"]["month"] += report.total_cost if report.start_date.month == current_month else 0
            data["total_maintenance_spend"]["quarter"] += report.total_cost if report.start_date.month - 1 // 3 + 1 == current_quarter else 0
            for purchase_event in report.part_purchase_events.all():
                part_counter[purchase_event.part.name] += 1

        previous_year_reports = MaintenanceReport.objects.filter(start_date__year=current_year - 1, profile__user=request.user)
        previous_year_total_cost = sum([report.total_cost for report in previous_year_reports])
        data["YoY"] = (data["total_maintenance_spend"]["year"] - previous_year_total_cost) / previous_year_total_cost * 100
        data["vehicle_avg_cost"] = data["total_maintenance_spend"]["year"] / Vehicle.objects.filter(profile__user=request.user).count()

        # Vehicle health overview
        vehicles = Vehicle.objects.all()
        state_counter = defaultdict(int)
        for vehicle in vehicles:
            date = vehicle.next_service_due - vehicle.last_service_date
            self._populate_health_counter(date, "vehicle_avg_health", data, len(vehicles))
            legal_date = now() - vehicle.insurance_expiry_date
            self._populate_health_counter(legal_date, "vehicle_insurance_health", data, len(vehicles))
            license_date = now() - vehicle.license_expiry_date
            self._populate_health_counter(license_date, "vehicle_license_health", data, len(vehicles))

        items = [(count, name) for name, count in part_counter.items()]
        heapq.heapify(items)
        top_recurring_issues = heapq.nlargest(3, items)
        data['top_recurring_issues'] = [name for _ , name in top_recurring_issues]


    def _populate_health_counter(self, date , key, data, vehicles):
        health_counter = defaultdict(int)
        if date.days > 30:
            health_counter["good"] += 1
        elif date.days >= 0:
            health_counter["warning"] += 1
        else:
            health_counter["critical"] += 1

        data[key]["good"] = health_counter["good"] / vehicles * 100
        data[key]["warning"] = health_counter["warning"] / vehicles * 100
        data[key]["critical"] = health_counter["critical"] / vehicles * 100




