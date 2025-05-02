import datetime
import heapq
from collections import defaultdict

from dateutil import parser
from django.db.models import Q
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
        data = {"total_maintenance_cost": {"year": 0, "month": 0, "quarter": 0},
                "YoY": 0.0,
                "vehicle_avg_cost": 0.0,
                "vehicle_avg_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
                "vehicle_insurance_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
                "vehicle_license_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
                "top_recurring_issues": [],
                "filtered_data": {
                    "core_metrics": {"total_maintenance_cost": 0, "YoY": 0.0, "vehicle_avg_cost": 0.0},
                    "group_by": {
                        "monthly": {},
                        "quarterly": {},
                        "yearly": {}
                    }
                }
                }
        current_year = now().year
        current_month = now().month
        current_quarter = (current_month - 1) // 3 + 1

        vehicle_type = request.query_params.get('vehicle_type', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        group_by = request.query_params.get('group_by', None)

        filters = Q(profile__user=request.user)
        if vehicle_type:
            filters &= Q(vehicle__vehicle_type=vehicle_type)
        if end_date:
            filters &= Q(start_date__lte=end_date) & Q(start_date__gte=start_date)
        else:
            filters &= Q(start_date__year=current_year)

        # Core analytics
        requested_reports = MaintenanceReport.objects.filter(filters)
        part_counter = defaultdict(int)
        vehicles_count = Vehicle.objects.filter(profile__user=request.user).count()

        # Group core metrics according to user request
        if group_by:
            if group_by == "monthly":
                self._handle_group_by_request(data, requested_reports, vehicles_count, group_by_key="monthly", metric_key="MoM")
            elif group_by == "quarterly":
                self._handle_group_by_request(data, requested_reports, vehicles_count, group_by_key="quarterly", metric_key="QoQ")
            elif group_by == "yearly":
                self._handle_group_by_request(data, requested_reports, vehicles_count, group_by_key="yearly", metric_key="YoY")
        else:
            if not end_date:
                for report in requested_reports:
                    data["total_maintenance_cost"]["year"] += report.total_cost
                    data["total_maintenance_cost"]["month"] += report.total_cost if report.start_date.month == current_month else 0
                    data["total_maintenance_cost"]["quarter"] += report.total_cost if report.start_date.month - 1 // 3 + 1 == current_quarter else 0
                    for purchase_event in report.part_purchase_events.all():  # Add caching to optimize performance
                        part_counter[purchase_event.part.name] += 1

                filters &= Q(start_date__year=current_year - 1)
                previous_year_reports = MaintenanceReport.objects.filter(filters)
                previous_year_total_cost = sum([report.total_cost for report in previous_year_reports])
                data["YoY"] = self._calculate_yoy_change(data["total_maintenance_cost"]["year"], previous_year_total_cost)
                data["vehicle_avg_cost"] = data["total_maintenance_cost"]["year"] / max(vehicles_count, 1)
            else:
                data["filtered_data"]["core_metrics"]["total_maintenance_cost"] = sum(report.total_cost for report in requested_reports)
                filters = Q(vehicle__vehicle_type=vehicle_type) if vehicle_type else Q()
                filters &= Q(profile__user=request.user) & Q(start_date__year=parser.parse(start_date).year - 1) & Q(
                    end_date__year=parser.parse(end_date).year - 1)
                previous_reports = MaintenanceReport.objects.filter(filters)
                previous_reports_total_cost = sum([report.total_cost for report in previous_reports])
                data['filtered_data']['core_metrics']['YoY'] = self._calculate_yoy_change(
                    data["filtered_data"]["core_metrics"]["total_maintenance_cost"], previous_reports_total_cost)
                data["filtered_data"]["core_metrics"]["vehicle_avg_cost"] = data["filtered_data"]["core_metrics"]["total_maintenance_cost"] / max(
                    vehicles_count, 1)

            # Vehicle health overview
        vehicles = Vehicle.objects.filter(profile__user=request.user)
        for vehicle in vehicles:
            self._populate_health_counter(vehicle.next_service_due - vehicle.last_service_date, "vehicle_avg_health", data, len(vehicles))
            self._populate_health_counter(now().date() - vehicle.insurance_expiry_date, "vehicle_insurance_health", data, len(vehicles))
            self._populate_health_counter(now().date() - vehicle.license_expiry_date, "vehicle_license_health", data, len(vehicles))

        items = [(count, name) for name, count in part_counter.items()]
        heapq.heapify(items)
        top_recurring_issues = heapq.nlargest(3, items)
        data['top_recurring_issues'] = [name for _, name in top_recurring_issues]

        return Response(data, status=status.HTTP_200_OK)

    def _handle_group_by_request(self, data, requested_reports, vehicles_count, group_by_key="yearly", metric_key="YoY"):
        for report in requested_reports:
            if group_by_key == "monthly":
                key = report.start_date.month
            elif group_by_key == "quarterly":
                key = report.start_date.month - 1 // 3 + 1
            else:
                key = report.start_date.year
            data["filtered_data"]["group_by"][group_by_key][key]["total_maintenance_cost"] += report.total_cost

        for time_range, metrics in data["filtered_data"]["group_by"][group_by_key].items():
            previous_time_range_metrics = data["filtered_date"]["group_by"][group_by_key].get(time_range - 1, {})
            if previous_time_range_metrics:
                data["filtered_data"]["group_by"][group_by_key][time_range][metric_key] = (metrics["total_maintenance_cost"] -
                                                                                           previous_time_range_metrics[
                                                                                               "total_maintenance_cost"]) / max(
                    previous_time_range_metrics["total_maintenance_cost"], 1) * 100

            data["filtered_data"]["group_by"][group_by_key][time_range]["vehicle_avg_cost"] = metrics["total_maintenance_cost"] / max(vehicles_count,
                                                                                                                                      1)

    def _populate_health_counter(self, date, key, data, vehicles_count):
        health_counter = defaultdict(int)
        if date.days > 30:
            health_counter["good"] += 1
        elif date.days >= 0:
            health_counter["warning"] += 1
        else:
            health_counter["critical"] += 1

        data[key]["good"] = health_counter["good"] / vehicles_count * 100
        data[key]["warning"] = health_counter["warning"] / vehicles_count * 100
        data[key]["critical"] = health_counter["critical"] / vehicles_count * 100

    def _calculate_yoy_change(self, current_year: int, previous_year: int) -> float:
        if previous_year == 0:
            return 0.0
        change = (current_year - previous_year) / previous_year * 100
        return round(change, 2)
