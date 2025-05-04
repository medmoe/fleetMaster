import datetime
from collections import defaultdict
from datetime import timedelta
from typing import Optional, List, Dict

from django.db.models import F, Q, Sum, ExpressionWrapper, DurationField, Avg, Case, When, FloatField, Count
from django.db.models.functions import ExtractYear, ExtractMonth, ExtractQuarter
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from maintenance.models import MaintenanceReport, Part, ServiceProvider, PartsProvider, PartPurchaseEvent
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
        vehicle_type = request.query_params.get('vehicle_type', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        group_by = request.query_params.get('group_by', None)
        vehicles_count = Vehicle.objects.filter(profile__user=self.request.user).count()
        health_checks = self._get_health_checks()

        # Handle request when filters are not provided
        if not group_by and not end_date:
            core_metrics = self._get_core_metrics(vehicle_type)
            return Response(data=core_metrics | health_checks, status=status.HTTP_200_OK)

        grouped_metrics = {"grouped_metrics": self._get_grouped_maintenance_metrics(start_date, end_date, group_by, vehicles_count)}
        return Response(data=grouped_metrics | health_checks, status=status.HTTP_200_OK)

    def _get_grouped_maintenance_metrics(self, start_date: Optional[datetime.date], end_date: Optional[datetime.date], group_by: str, vehicle_count: int) -> List[Dict]:
        """Get maintenance costs grouped by time period with change metrics.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            group_by: Grouping strategy ('yearly', 'quarterly', 'monthly')
            vehicle_count: Number of vehicles for average calculation

        Returns:
            List of dictionaries containing metrics for each time period
        """
        PERCENT = 100

        # Input validation
        if not group_by or group_by not in ("yearly", "quarterly", "monthly"):
            group_by = "monthly"

        if vehicle_count <= 0:
            raise ValueError("vehicle_count must be positive")

        # Build filters
        filters = Q(profile__user=self.request.user)
        if start_date and end_date:
            filters &= Q(start_date__gte=start_date, end_date__lte=end_date)

        # Define grouping strategies
        grouping_strategies = {
            "yearly": (ExtractYear('start_date'), "yoy_change"),
            "quarterly": (ExtractQuarter('start_date'), "qoq_change"),
            "monthly": (ExtractMonth('start_date'), "mom_change")
        }

        date_extractor, change_metric_key = grouping_strategies[group_by]

        # Get base data
        grouped_data = list(
            MaintenanceReport.objects
            .filter(filters)
            .annotate(time_period=date_extractor)
            .values('time_period')
            .annotate(total_cost=Sum('total_cost'))
            .order_by('time_period')
        )

        # Calculate derived metrics
        for i in range(len(grouped_data)):
            # Add vehicle average
            grouped_data[i]["cost_per_vehicle"] = (
                    grouped_data[i]["total_cost"] / vehicle_count * PERCENT
            )

            # Add period-over-period change (except first period)
            if i > 0:
                prev_cost = grouped_data[i - 1]["total_cost"]
                current_cost = grouped_data[i]["total_cost"]

                if prev_cost != 0:
                    change_pct = (current_cost - prev_cost) / prev_cost * PERCENT
                else:
                    change_pct = 0.0

                grouped_data[i][change_metric_key] = change_pct

        return grouped_data

    def _get_health_checks(self):
        current = now().date()
        thirty = timedelta(days=30)
        zero = timedelta(days=0)
        raw_health_checks = Vehicle.objects.filter(profile__user=self.request.user).annotate(
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

        return self._format_health_checks(raw_health_checks)

    def _format_health_checks(self, raw_health_checks):
        formatted_version = defaultdict(lambda: defaultdict(float))
        for key, value in raw_health_checks.items():
            [health_type, status] = key.split("__")
            formatted_version[health_type][status] = value
        return formatted_version

    def _get_core_metrics(self, vehicle_type):
        # Consider implementing caching using Redis in the future.
        current_year = now().year
        current_month = now().month
        current_quarter = (current_month - 1) // 3
        start_month = current_quarter * 3 + 1
        end_month = start_month + 2
        filters = Q(profile__user=self.request.user, start_date__year=current_year)
        filters &= Q(vehicle__vehicle_type=vehicle_type) if vehicle_type else Q()
        maintenance_cost = MaintenanceReport.objects.filter(filters).aggregate(
            total_maintenance_cost__year=Sum('total_cost', default=0),
            total_maintenance_cost__quarter=Sum('total_cost', filter=Q(start_date__month__range=(start_month, end_month)), default=0),
            total_maintenance_cost__month=Sum('total_cost', filter=Q(start_date__month=current_month), default=0),
        )
        top_recurring_issues = PartPurchaseEvent.objects.filter(
            maintenance_report__profile__user=self.request.user,
            maintenance_report__start_date__year=current_year
        ).values('part__name').annotate(count=Count('id')).order_by('-count')[:3]

        previous_year_total_cost = MaintenanceReport.objects.filter(
            profile__user=self.request.user,
            start_date__year=current_year - 1
        ).aggregate(Sum('total_cost', default=0))['total_cost__sum']
        yoy = (maintenance_cost['total_maintenance_cost__year'] - previous_year_total_cost) / previous_year_total_cost * 100 if previous_year_total_cost else 0.0

        return self._format_maintenance_cost(maintenance_cost) | {'yoy': yoy} | {"top_recurring_issues": list(top_recurring_issues)}

    def _format_maintenance_cost(self, raw_maintenance_cost):
        vehicle_count = Vehicle.objects.filter(profile__user=self.request.user).count()
        formatted_version = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for key, value in raw_maintenance_cost.items():
            [total_maintenance_cost, time_period] = key.split("__")
            formatted_version[total_maintenance_cost][time_period]["total"] = value
            formatted_version[total_maintenance_cost][time_period]["vehicle_avg"] = value / vehicle_count * 100

        return formatted_version
