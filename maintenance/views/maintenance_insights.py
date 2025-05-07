from collections import defaultdict
from datetime import timedelta, datetime, date
from typing import DefaultDict, Any, Union

from django.db.models import F, Q, Sum, ExpressionWrapper, DurationField, Avg, Case, When, FloatField, Count
from django.db.models.functions import ExtractYear, ExtractMonth, ExtractQuarter, Round
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from maintenance.models import MaintenanceReport, Part, ServiceProvider, PartsProvider, PartPurchaseEvent
from maintenance.serializers import MaintenanceReportSerializer, PartSerializer, ServiceProviderSerializer, PartsProviderSerializer
from maintenance.utils import has_gap_between_periods
from vehicles.models import Vehicle


class MaintenanceReportOverviewView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self, request):
        """
        Fetch maintenance reports for the current and previous years of a given vehicle.
        """
        current_year = now().year
        previous_start_date = date(current_year - 1, 1, 1)
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
        vehicle_health_metrics = self._get_health_metrics()

        # Handle request when filters are not provided
        if not group_by and not end_date:
            core_metrics = self._get_core_metrics(vehicle_type)
            return Response(data=core_metrics | {"vehicle_health_metrics": vehicle_health_metrics}, status=status.HTTP_200_OK)

        grouped_metrics = {"grouped_metrics": self._get_grouped_maintenance_metrics(start_date, end_date, group_by, vehicles_count)}
        return Response(data=grouped_metrics | {"vehicle_health_metrics": vehicle_health_metrics}, status=status.HTTP_200_OK)

    def _get_grouped_maintenance_metrics(self, start_date: str, end_date: str, group_by: str, vehicle_count: int) -> DefaultDict[Any, DefaultDict[str, Union[float, str]]]:
        """Get maintenance costs grouped by time period with change metrics.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            group_by: Grouping strategy ('yearly', 'quarterly', 'monthly')
            vehicle_count: Number of vehicles for average calculation

        Returns:
            List of dictionaries containing metrics for each time period
        """
        PERCENTAGE_MULTIPLIER = 100

        if not group_by or group_by not in ("yearly", "quarterly", "monthly"):
            group_by = "monthly"

        if vehicle_count <= 0:
            raise  ValidationError("Cannot process request: No vehicles found in your fleet.")

        # Build filters
        filters = Q(profile__user=self.request.user)
        if start_date and end_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            filters &= Q(start_date__gte=start_date, start_date__lte=end_date)

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
            .annotate(time_period=date_extractor, year=ExtractYear('start_date'))
            .values('time_period', 'year')
            .annotate(total_cost=Sum('total_cost'))
            .order_by('year', 'time_period')
        )
        grouped_data = self._format_grouped_data(grouped_data, group_by)
        # Calculate derived metrics
        returned_data = defaultdict(lambda: defaultdict(float))
        for i in range(len(grouped_data)):
            # Add vehicle average
            time_period, total_cost = grouped_data[i]['time_period'], grouped_data[i]['total_cost']
            returned_data[time_period]['vehicle_avg'] = round(total_cost / vehicle_count, 2)

            # Add period-over-period change (except the first period)
            change_pct = 0.0
            if i > 0 and not has_gap_between_periods(time_period, grouped_data[i - 1]['time_period']):
                prev_cost = grouped_data[i - 1]["total_cost"]
                if prev_cost != 0:
                    change_pct = round((total_cost - prev_cost) / prev_cost * PERCENTAGE_MULTIPLIER, 2)

            returned_data[time_period][change_metric_key] = change_pct
        return returned_data

    def _get_health_metrics(self):
        current = now().date()
        thirty = timedelta(days=30)
        zero = timedelta(days=0)
        raw_health_metrics = Vehicle.objects.filter(profile__user=self.request.user).annotate(
            service_gap=ExpressionWrapper(
                F('next_service_due') - F('last_service_date'), output_field=DurationField()
            ),
            insurance_gap=ExpressionWrapper(
                F('insurance_expiry_date') - current, output_field=DurationField()
            ),
            license_gap=ExpressionWrapper(
                F('license_expiry_date') - current, output_field=DurationField()
            ),
        ).aggregate(
            # Service health metrics
            vehicle_avg_health__good=Round(Avg(Case(When(service_gap__gt=thirty, then=1), default=0.0, output_field=FloatField())) * 100, precision=2),
            vehicle_avg_health__warning=Round(Avg(Case(When(service_gap__gt=zero, service_gap__lte=thirty, then=1), default=0.0, output_field=FloatField())) * 100, precision=2),
            vehicle_avg_health__critical=Round(Avg(Case(When(service_gap__lte=zero, then=1), default=0.0, output_field=FloatField())) * 100, precision=2),

            # Insurance health metrics
            vehicle_insurance_health__good=Round(Avg(Case(When(insurance_gap__gt=thirty, then=1), default=0.0, output_field=FloatField())) * 100, precision=2),
            vehicle_insurance_health__warning=Round(Avg(Case(When(insurance_gap__gt=zero, insurance_gap__lte=thirty, then=1), default=0.0, output_field=FloatField())) * 100, precision=2),
            vehicle_insurance_health__critical=Round(Avg(Case(When(insurance_gap__lte=zero, then=1), default=0.0, output_field=FloatField())) * 100, precision=2),

            # License health metrics
            vehicle_license_health__good=Round(Avg(Case(When(license_gap__gt=thirty, then=1), default=0.0, output_field=FloatField())) * 100, precision=2),
            vehicle_license_health__warning=Round(Avg(Case(When(license_gap__gt=zero, license_gap__lte=thirty, then=1), default=0.0, output_field=FloatField())) * 100, precision=2),
            vehicle_license_health__critical=Round(Avg(Case(When(license_gap__lte=zero, then=1), default=0.0, output_field=FloatField())) * 100, precision=2)
        )

        return self._format_health_metrics(raw_health_metrics)

    def _format_health_metrics(self, raw_health_metrics):
        """
        Format vehicle health metrics by grouping health statuses according to health type.

        Args:
            raw_health_metrics (dict): A dictionary where each key is in the format
                "<health_type>__<status>" and the value is a float representing the metric.

        Returns:
            defaultdict: A nested defaultdict such that each item is in this format
                "<health_type>": {"<status>": float }

        """
        formatted_version = defaultdict(lambda: defaultdict(float))
        for key, value in raw_health_metrics.items():
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
        maintenance_cost_metrics = MaintenanceReport.objects.filter(filters).aggregate(
            total_maintenance_cost__year=Sum('total_cost', default=0),
            total_maintenance_cost__quarter=Sum('total_cost', filter=Q(start_date__month__range=(start_month, end_month)), default=0),
            total_maintenance_cost__month=Sum('total_cost', filter=Q(start_date__month=current_month), default=0),
        )
        top_recurring_issues = PartPurchaseEvent.objects.filter(
            maintenance_report__profile__user=self.request.user,
            maintenance_report__start_date__year=current_year
        ).values('part__name').annotate(count=Count('id')).order_by('-count', 'part__name')[:3]

        previous_year_total_cost = MaintenanceReport.objects.filter(
            profile__user=self.request.user,
            start_date__year=current_year - 1
        ).aggregate(Sum('total_cost', default=0))['total_cost__sum']
        yoy = round((maintenance_cost_metrics['total_maintenance_cost__year'] - previous_year_total_cost) / previous_year_total_cost * 100,
                    2) if previous_year_total_cost else 0.0

        return self._format_maintenance_cost_metrics(maintenance_cost_metrics) | {'yoy': yoy} | {"top_recurring_issues": list(top_recurring_issues)}

    def _format_maintenance_cost_metrics(self, raw_maintenance_cost_metrics: dict[str, int]) -> DefaultDict[str, DefaultDict[str, DefaultDict[str, float]]]:
        """
        Format maintenance cost metrics by grouping values by period (e.g., year, quarter, month),
        and calculating per-vehicle averages.

        Args:
            raw_maintenance_cost_metrics (dict[str, int]): A dictionary where each key is in the format
                "<cost_type>__<time_period>" (e.g., "total_maintenance_cost__2024-Q1") and the value is the
                corresponding total cost for that period.

        Returns:
            DefaultDict[str, DefaultDict[str, DefaultDict[str, float]]]: A nested defaultdict where the first level
                groups by cost type (e.g., "total_maintenance_cost"), the second by time period, and the third contains:
                - "total": the raw total cost,
                - "vehicle_avg": the average cost per vehicle, rounded to two decimal places.

        Example:
            {
                "total_maintenance_cost": {
                    "2024-Q1": {"total": 10000, "vehicle_avg": 1250.0},
                    "2024-Q2": {"total": 8000, "vehicle_avg": 1000.0},
                }
            }
        """
        vehicle_count = Vehicle.objects.filter(profile__user=self.request.user).count()
        formatted_version = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for key, value in raw_maintenance_cost_metrics.items():
            [total_maintenance_cost, time_period] = key.split("__")
            formatted_version[total_maintenance_cost][time_period]["total"] = value
            formatted_version[total_maintenance_cost][time_period]["vehicle_avg"] = round(value / vehicle_count, 2) if vehicle_count else 0.0

        return formatted_version

    def _format_grouped_data(self, grouped_data, group_by):
        """
        Formats grouped data into a structured list with a time period and total cost.

        This method processes the given grouped data by formatting its time periods
        according to the specified grouping type (yearly, quarterly, or custom format) and
        associates each formatted time period with its corresponding total cost.

        Args:
            grouped_data (list[dict]): A list of dictionaries containing grouped data. Each
                dictionary should include keys 'time_period', 'year', and 'total_cost'.
            group_by (str): A string indicating how the data is grouped. Acceptable values
                are 'yearly', 'quarterly', or other formats.

        Returns:
            list[dict]: A list of dictionaries formatted with the time period string and
                associated total cost.
        """

        def get_period(entry):
            if group_by == "yearly": return f'{entry['time_period']}'
            if group_by == "quarterly": return f'{entry['year']}-Q{entry['time_period']}'
            return f'{entry['year']}-{entry['time_period']}'

        return [{'time_period': get_period(entry), "total_cost": entry['total_cost']} for entry in grouped_data]
