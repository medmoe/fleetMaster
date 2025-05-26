from collections import defaultdict, OrderedDict
from datetime import timedelta, datetime
from typing import Optional, DefaultDict, Any, Union

from django.db.models import Sum, F, Q, ExpressionWrapper, DurationField, Avg, Case, When, FloatField, Value, CharField, Count
from django.db.models.functions import Round, ExtractYear, ExtractQuarter, ExtractMonth
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError

from maintenance.models import MaintenanceReport, PartPurchaseEvent
from maintenance.utils import has_gap_between_periods
from vehicles.models import Vehicle


class FleetHealthService:
    @staticmethod
    def get_health_metrics(user, vehicle_type: Optional[str] = None) -> (dict[str, float], dict[str, list[str]]):
        """
        Generates vehicle health metrics for the authenticated user.

        This function calculates and aggregates various health metrics for vehicles
        belonging to the authenticated user. The metrics are computed based on service
        gap, insurance expiry gap, and license expiry gap. Each metric is categorized
        into three health levels: good, warning, and critical. The computed metrics
        are returned in a formatted structure.

        Returns:
            tuple[dict, dict]: A tuple containing:
                1. A dictionary with aggregated health metrics for vehicles, categorized into service
                   health, insurance health, and license health, with percentages for good, warning,
                   and critical levels
                2. A dictionary with lists of vehicle details (registration, make, model, year) for
                   each health category and status
        """
        current = now().date()
        thirty = timedelta(days=30)
        zero = timedelta(days=0)
        filters = Q(profile__user=user)
        filters &= Q(type=vehicle_type) if vehicle_type else Q()
        raw_health_metrics = Vehicle.objects.filter(filters).annotate(
            service_gap=ExpressionWrapper(
                F('next_service_due') - F('last_service_date'), output_field=DurationField()
            ),
            insurance_gap=ExpressionWrapper(
                F('insurance_expiry_date') - current, output_field=DurationField()
            ),
            license_gap=ExpressionWrapper(
                F('license_expiry_date') - current, output_field=DurationField()
            ),
        )

        # Get aggregated percentages
        health_percentages = raw_health_metrics.aggregate(
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

        # Categorize vehicles by their health status and get their IDs
        with_health_annotation = raw_health_metrics.annotate(
            service_health=Case(
                When(service_gap__gt=thirty, then=Value("good")),
                When(service_gap__gt=zero, service_gap__lte=thirty, then=Value("warning")),
                default=Value("critical"),
                output_field=CharField()
            ),
            insurance_health=Case(
                When(insurance_gap__gt=thirty, then=Value("good")),
                When(insurance_gap__gt=zero, insurance_gap__lte=thirty, then=Value("warning")),
                default=Value("critical"),
                output_field=CharField()
            ),
            license_health=Case(
                When(license_gap__gt=thirty, then=Value("good")),
                When(license_gap__gt=zero, license_gap__lte=thirty, then=Value("warning")),
                default=Value("critical"),
                output_field=CharField()
            )
        )

        # Get lists of vehicle names and IDs for each health category
        health_vehicles = {
            'vehicle_avg_health': {
                # 'good': list(with_health_annotation.filter(service_health="good").values_list('registration_number', 'make', 'model', 'year')),
                'warning': list(with_health_annotation.filter(service_health="warning").values_list('registration_number', 'make', 'model', 'year')),
                'critical': list(with_health_annotation.filter(service_health="critical").values_list('registration_number', 'make', 'model', 'year'))
            },
            'vehicle_insurance_health': {
                # 'good': list(with_health_annotation.filter(insurance_health="good").values_list('registration_number', 'make', 'model', 'year')),
                'warning': list(with_health_annotation.filter(insurance_health="warning").values_list('registration_number', 'make', 'model', 'year')),
                'critical': list(with_health_annotation.filter(insurance_health="critical").values_list('registration_number', 'make', 'model', 'year'))
            },
            'vehicle_license_health': {
                # 'good': list(with_health_annotation.filter(license_health="good").values_list('registration_number', 'make', 'model', 'year')),
                'warning': list(with_health_annotation.filter(license_health="warning").values_list('registration_number', 'make', 'model', 'year')),
                'critical': list(with_health_annotation.filter(license_health="critical").values_list('registration_number', 'make', 'model', 'year'))
            }
        }

        return FleetHealthService.format_health_metrics(health_percentages), health_vehicles

    @staticmethod
    def format_health_metrics(raw_health_metrics):
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


class FleetMaintenanceService:
    @staticmethod
    def get_core_metrics(user, vehicle_type):
        """
        Calculates maintenance cost metrics and analyzes top recurring issues for a specific vehicle type
        within the current user's maintenance reports.

        Parameters:
            user: The authenticated user.
            vehicle_type: Optional[str]
            The type of vehicle to filter maintenance reports. If None, metrics for all vehicle
            types are considered.

        Returns:
        Dict
            A dictionary containing the following keys:
            - total_maintenance_cost__year: Total maintenance cost for the current year.
            - total_maintenance_cost__quarter: Total maintenance cost for the current quarter.
            - total_maintenance_cost__month: Total maintenance cost for the current month.
            - yoy: Year-over-Year percentage change in maintenance costs compared to the previous year.
            - top_recurring_issues: A list of the top three most frequent maintenance issues.

        Notes:
        Caching of metrics using Redis could be implemented in the future to optimize performance.

        Raises:
        KeyError
            If any key used in calculations from aggregated results is not present.
        ZeroDivisionError
            If previous year's data is zero when calculating YoY percentage change.
        """
        # Consider implementing caching using Redis in the future.
        current_year = now().year
        current_month = now().month
        current_quarter = (current_month - 1) // 3
        start_month = current_quarter * 3 + 1
        end_month = start_month + 2
        filters = Q(profile__user=user, start_date__year=current_year)
        filters &= Q(vehicle__type=vehicle_type) if vehicle_type else Q()
        maintenance_cost_metrics = MaintenanceReport.objects.filter(filters).aggregate(
            total_maintenance_cost__year=Sum('total_cost', default=0),
            total_maintenance_cost__quarter=Sum('total_cost', filter=Q(start_date__month__range=(start_month, end_month)), default=0),
            total_maintenance_cost__month=Sum('total_cost', filter=Q(start_date__month=current_month), default=0),
        )
        filters = Q(maintenance_report__profile__user=user, maintenance_report__start_date__year=current_year)
        filters &= Q(maintenance_report__vehicle__type=vehicle_type) if vehicle_type else Q()
        top_recurring_issues = PartPurchaseEvent.objects.filter(filters).values('part__name').annotate(count=Count('id')).order_by('-count', 'part__name')[:3]

        filters = Q(profile__user=user, start_date__year=current_year - 1)
        filters &= Q(vehicle__type=vehicle_type) if vehicle_type else Q()
        previous_year_total_cost = MaintenanceReport.objects.filter(filters).aggregate(Sum('total_cost', default=0))['total_cost__sum']
        yoy = round((maintenance_cost_metrics['total_maintenance_cost__year'] - previous_year_total_cost) / previous_year_total_cost * 100,
                    2) if previous_year_total_cost else 0.0

        return FleetMaintenanceService.format_maintenance_cost_metrics(user, maintenance_cost_metrics) | {'yoy': yoy} | {"top_recurring_issues": list(top_recurring_issues)}

    @staticmethod
    def format_maintenance_cost_metrics(user, raw_maintenance_cost_metrics: dict[str, int]) -> DefaultDict[str, DefaultDict[str, DefaultDict[str, float]]]:
        """
        Format maintenance cost metrics by grouping values by period (e.g., year, quarter, month),
        and calculating per-vehicle averages.

        Args:
            user: The authenticated user.
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
        vehicle_count = Vehicle.objects.filter(profile__user=user).count()
        formatted_version = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for key, value in raw_maintenance_cost_metrics.items():
            [total_maintenance_cost, time_period] = key.split("__")
            formatted_version[total_maintenance_cost][time_period]["total"] = value
            formatted_version[total_maintenance_cost][time_period]["vehicle_avg"] = round(value / vehicle_count, 2) if vehicle_count else 0.0

        return formatted_version

    @staticmethod
    def get_grouped_maintenance_metrics(user, start_date: str, end_date: str, group_by: str, vehicle_count: int, vehicle_type: Optional[str]) -> DefaultDict[Any, DefaultDict[str, Union[float, str]]]:
        """Get maintenance costs grouped by time period with change metrics.

        Args:
            user: The authenticated user.
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
            raise ValidationError("Cannot process request: No vehicles found in your fleet.")

        # Build filters
        filters = Q(profile__user=user)
        if start_date and end_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            filters &= Q(start_date__gte=start_date, start_date__lte=end_date)

        if vehicle_type:
            filters &= Q(vehicle__type=vehicle_type)

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
        grouped_data = FleetMaintenanceService.format_grouped_data(grouped_data, group_by)
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

    @staticmethod
    def format_grouped_data(grouped_data, group_by):
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
            if group_by == "yearly": return f"{entry['time_period']}"
            if group_by == "quarterly": return f"{entry['year']}-Q{entry['time_period']}"
            return f"{entry['year']}-{entry['time_period']}"

        return [{'time_period': get_period(entry), "total_cost": entry['total_cost']} for entry in grouped_data]


class VehicleMaintenanceService:
    @staticmethod
    def format_yearly_maintenance_data(cursor_results):
        """
        Format raw query results into a structured yearly and monthly maintenance report.

        Args:
            cursor_results: Raw results from database cursor

        Returns:
            List of yearly maintenance data with costs and top recurring issues
        """
        # Create a dictionary to organize data by year
        data = OrderedDict()
        for row in cursor_results:
            data_type, year, month, total_cost, previous_year_cost, change_pct, part_name, part_count, part_cost, part_rank = row
            if data_type == 'yearly_cost':
                data[int(year)] = {'total_cost': total_cost, 'top_recurring_issues': [], 'yoy_change': change_pct}
            elif data_type == 'monthly_cost':
                data[int(year)][int(month)] = {'total_cost': total_cost, 'top_recurring_issues': [], 'mom_change': change_pct}
            elif data_type == 'yearly_part':
                data[int(year)]['top_recurring_issues'].append({'part_name': part_name, 'part_count': part_count, 'part_cost': part_cost, 'part_rank': part_rank})
            elif data_type == 'monthly_part':
                data[int(year)][int(month)]['top_recurring_issues'].append({'part_name': part_name, 'part_count': part_count, 'part_cost': part_cost, 'part_rank': part_rank})

        return list(data.items())
