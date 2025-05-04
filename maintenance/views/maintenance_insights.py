import datetime
from collections import defaultdict
from datetime import timedelta

from django.db.models import F, Q, Sum, ExpressionWrapper, DurationField, Avg, Case, When, FloatField
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
        core_metrics = {"total_maintenance_cost": {"year": 0, "month": 0, "quarter": 0},
                        "YoY": 0.0,
                        "vehicle_avg_cost": 0.0,
                        "top_recurring_issues": [],
                        }

        filtered_data = {
            "group_by": {
                "monthly": defaultdict(lambda: [0, 0, 0.0]),  # [Total cost in the month, MoM change, vehicle avg cost]
                "quarterly": defaultdict(lambda: [0, 0, 0.0]),  # [total cost in the quarter, QoQ change, vehicle avg cost]
                "yearly": defaultdict(lambda: [0, 0, 0.0]),  # [total cost in the year, YoY change, vehicle avg cost]
            }
        }

        health_checks = {
            "vehicle_avg_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
            "vehicle_insurance_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
            "vehicle_license_health": {"good": 0.0, "warning": 0.0, "critical": 0.0},
        }

        vehicle_type = request.query_params.get('vehicle_type', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        group_by = request.query_params.get('group_by', None)

        vehicles_count = Vehicle.objects.filter(profile__user=request.user).count()

        if not group_by and not end_date:
            self._populate_core_metrics(core_metrics, requested_reports, vehicles_count, vehicle_type)
            return Response(data=core_metrics | health_checks, status=status.HTTP_200_OK)

        if group_by:
            self._populate_filtered_data(filtered_data, group_by, requested_reports, vehicles_count)
        else:
            self._populate_filtered_data(filtered_data, "monthly", requested_reports, vehicles_count)

        return Response(data=filtered_data | health_checks, status=status.HTTP_200_OK)

    def _populate_filtered_data(self, filtered_data, group_by, requested_reports, vehicles_count):
        for report in requested_reports:
            # Create keys according to grouping by type
            key = self._get_key(group_by, report)
            filtered_data['group_by'][group_by][key][0] += report.total_cost
        for time_range, [current_total_cost, _, _] in filtered_data['group_by'][group_by].items():
            previous_total_cost, _ = filtered_data['group_by'][group_by].get(time_range - 1, [0, 0])
            if previous_total_cost:
                filtered_data['group_by'][group_by][time_range][1] = (current_total_cost - previous_total_cost) / previous_total_cost * 100
            filtered_data['group_by'][group_by][time_range][2] = current_total_cost / vehicles_count

    def _get_health_checks(self):
        current = now().date()
        thirty = timedelta(days=30)
        zero = timedelta(days=0)
        return Vehicle.objects.filter(profile__user=self.request.user).annotate(
            service_gap=ExpressionWrapper(
                F('next_service_due') - F('last_service_date'), output_field=DurationField()
            ),
            insurance_gap=ExpressionWrapper(
                current - F('insurance_expiry_date'), output_field=DurationField()
            ),
            license_gap=ExpressionWrapper(
                current - F('license_expiry_date'), output_field=DurationField()
            ),
        ).aggregate(
            # Service health metrics
            vehicle_avg_health__good=Avg(Case(When(service_gap__gt=thirty, then=1), default=0.0, output_field=FloatField())) * 100,
            vehicle_avg_health__warning=Avg(Case(When(service_gap__gt=zero, service_gap__lte=thirty, then=1), default=0.0, output_field=FloatField())) * 100,
            vehicle_avg_health__critical=Avg(Case(When(service_gap__lte=zero, then=1), default=0.0, output_field=FloatField())) * 100,

            # Insurance health metrics
            vehicle_insurance_health__good=Avg(Case(When(insurance_gap__gt=thirty, then=1), default=0.0, output_field=FloatField())) * 100,
            vehicle_insurance_health__warning=Avg(Case(When(insurance_gap__gt=zero, insurance_gap__lte=thirty, then=1), default=0.0, output_field=FloatField())) * 100,
            vehicle_insurance_health__critical=Avg(Case(When(insurance_gap__lte=zero, then=1), default=0.0, output_field=FloatField())) * 100,

            # License health metrics
            vehicle_license_health__good=Avg(Case(When(license_gap__gt=thirty, then=1), default=0.0, output_field=FloatField())) * 100,
            vehicle_license_health__warning=Avg(Case(When(license_gap__gt=zero, license_gap__lte=thirty, then=1), default=0.0, output_field=FloatField())) * 100,
            vehicle_license_health__critical=Avg(Case(When(license_gap__lte=zero, then=1), default=0.0, output_field=FloatField())) * 100
        )

    def _format_health_checks(self, raw_health_checks):
        pass
    def _populate_core_metrics(self, core_metrics, requested_reports, vehicles_count, vehicle_type):
        current_year = now().year
        current_month = now().month
        current_quarter = now().month // 3 + 1
        top_recurring_parts = defaultdict(int)

        # for report in requested_reports:
        #     core_metrics["total_maintenance_cost"]["year"] += report.total_cost
        #     core_metrics["total_maintenance_cost"]["month"] += report.total_cost if report.start_date.month == current_month else 0
        #     core_metrics["total_maintenance_cost"]["quarter"] += report.total_cost if report.start_date.month - 1 // 3 + 1 == current_quarter else 0
        #     for part_purchase_event in report.part_purchase_events.all():
        #         top_recurring_parts[part_purchase_event.part.name] += 1

        # Get previous year reports
        filters = Q(start_date__year=current_year - 1) & Q(profile__user=self.request.user)
        filters &= Q(vehicle__vehicle_type=vehicle_type) if vehicle_type else Q()
        previous_year_total_cost = MaintenanceReport.objects.filter(filters).aggregate(Sum('total_cost'))['total_cost__sum']
        core_metrics["YoY"] = self._calculate_yoy_change(core_metrics["total_maintenance_cost"]["year"], previous_year_total_cost)
        core_metrics["vehicle_avg_cost"] = core_metrics["total_maintenance_cost"]["year"] / max(vehicles_count, 1)
        core_metrics["top_recurring_issues"] = sorted(top_recurring_parts.items(), key=lambda x: x[1], reverse=True)[:3]

    def _calculate_yoy_change(self, current_year: int, previous_year: int) -> float:
        if not previous_year:
            return 0.0
        change = (current_year - previous_year) / previous_year * 100
        return round(change, 2)

    def _get_key(self, group_by: str, report: MaintenanceReport) -> int:
        if group_by == "monthly": return report.start_date.month
        if group_by == "quarterly": return report.start_date.month - 1 // 3 + 1
        return report.start_date.year
