from django.db.models import Sum
from .models import MaintenanceChoices, ServiceChoices


class ReportSummarizer:
    TOTAL_MAINTENANCE = "total_maintenance"
    TOTAL_MAINTENANCE_COST = "total_maintenance_cost"
    PREVENTIVE = "preventive"
    PREVENTIVE_COST = "preventive_cost"
    CURATIVE = "curative"
    CURATIVE_COST = "curative_cost"
    TOTAL_SERVICE_COST = "total_service_cost"
    MECHANIC = "mechanic"
    ELECTRICIAN = "electrician"
    CLEANING = "cleaning"

    def summarize_reports(self, maintenance_reports):
        report = self.initialize_report_summary()

        for maintenance_report in maintenance_reports:
            self.update_total_maintenance(report)
            self.update_costs(report, maintenance_report)
            self.update_maintenance_type_counts(report, maintenance_report)
            self.update_service_provider_counts(report, maintenance_report)

        return report

    def initialize_report_summary(self):
        return {
            self.TOTAL_MAINTENANCE: 0,
            self.TOTAL_MAINTENANCE_COST: 0,
            self.PREVENTIVE: 0,
            self.PREVENTIVE_COST: 0,
            self.CURATIVE: 0,
            self.CURATIVE_COST: 0,
            self.TOTAL_SERVICE_COST: 0,
            self.MECHANIC: 0,
            self.ELECTRICIAN: 0,
            self.CLEANING: 0,
        }

    def update_total_maintenance(self, report):
        report[self.TOTAL_MAINTENANCE] += 1

    def update_costs(self, report, maintenance_report):
        report[self.TOTAL_MAINTENANCE_COST] += maintenance_report.total_cost
        report[self.TOTAL_SERVICE_COST] += maintenance_report.service_provider_events.aggregate(Sum('cost'))["cost__sum"] or 0

    def update_maintenance_type_counts(self, report, maintenance_report):
        if maintenance_report.maintenance_type == MaintenanceChoices.PREVENTIVE:
            report[self.PREVENTIVE] += 1
            report[self.PREVENTIVE_COST] += maintenance_report.total_cost
        elif maintenance_report.maintenance_type == MaintenanceChoices.CURATIVE:
            report[self.CURATIVE] += 1
            report[self.CURATIVE_COST] += maintenance_report.total_cost

    def update_service_provider_counts(self, report, maintenance_report):
        service_type_mapping = {
            ServiceChoices.MECHANIC: self.MECHANIC,
            ServiceChoices.ELECTRICIAN: self.ELECTRICIAN,
            ServiceChoices.CLEANING: self.CLEANING,
        }
        for service_provider_event in maintenance_report.service_provider_events.all():
            service_type = service_provider_event.service_provider.service_type
            if service_type in service_type_mapping:
                report[service_type_mapping[service_type]] += 1


def has_gap_between_periods(period1: str, period2: str) -> bool:
    """
    Determines whether there is a gap between two specified periods. The periods can be in yearly, monthly,
    or quarterly format. The function evaluates whether the difference between the two periods exceeds one
    unit of their format (one year, one month, or one quarter).

    Parameters:
    period1: str
        The first period in the format 'YYYY', 'YYYY-MM', or 'YYYY-QN', where 'YYYY' indicates a year,
        'YYYY-MM' a year and month, and 'YYYY-QN' a quarterly identifier (e.g., '2023-Q1').
    period2: str
        The second period in the same format constraints as period1.

    Returns:
    bool
        True if there is a gap of at least two units (years, months, or quarters) between the two periods,
        False otherwise.

    Raises:
    ValueError
        Raised when either of the provided string periods does not conform to the expected formats:
        'YYYY', 'YYYY-MM', or 'YYYY-QN'.
    """
    # Ensure consistent ordering (early to late)
    if period1 > period2:
        period1, period2 = period2, period1

    # Parse the periods
    try:
        if period1.isdigit() and period2.isdigit():
            return int(period1) - int(period2) > 1

        if 'Q' in period1:  # Quarterly format
            year1, q1 = int(period1.split('-')[0]), int(period1.split('Q')[1])
            year2, q2 = int(period2.split('-')[0]), int(period2.split('Q')[1])

            # Convert to absolute quarters (quarters since year 0)
            abs_quarter1 = year1 * 4 + q1
            abs_quarter2 = year2 * 4 + q2

            # Check if there's a gap
            return abs_quarter2 - abs_quarter1 > 1

        else:  # Monthly format
            year1, month1 = map(int, period1.split('-'))
            year2, month2 = map(int, period2.split('-'))

            # Convert to absolute months (months since year 0)
            abs_month1 = year1 * 12 + month1
            abs_month2 = year2 * 12 + month2

            # Check if there's a gap
            return abs_month2 - abs_month1 > 1

    except (ValueError, IndexError):
        raise ValueError(f"Invalid period format. Expected 'YYYY', 'YYYY-MM' or 'YYYY-QN', got '{period1}' and '{period2}'")


def period_key_comparator(item):
    """
    Compares period keys and provides a sorting mechanism for periodic data.

    The function is used to compare keys that represent periods in various date
    formats. It supports yearly, quarterly, and monthly formats. If the period
    key does not match any valid format or fails parsing, it will assign a
    default value that ensures such a key is sorted at the end.

    Arguments:
        item (tuple[str, Any]): A tuple with the first element being a period
        string ('YYYY', 'YYYY-QN', or 'YYYY-MM') and additional data as the
        second element.

    Returns:
        tuple[int, int]: A tuple representing the parsed period for sorting.
        For yearly data, it returns (year, ). For quarterly data, it returns
        (year, quarter). For monthly data, it returns (year, month). If parsing
        fails, it returns (float('inf'), float('inf')) to ensure sorting at the
        end.
    """
    period, _ = item  # Extract just the period string

    try:
        if period.isdigit(): # Handle yearly format ('YYYY')
            return int(period)

        if 'Q' in period:  # Handle quarterly format ('YYYY-QN')
            year, quarter = period.split('-')
            quarter = int(quarter.replace('Q', ''))
            return int(year), quarter
        else:  # Handle monthly format ('YYYY-MM')
            year, month = period.split('-')
            return int(year), int(month)
    except (ValueError, IndexError):
        # If parsing fails, return a default value that will sort at the end
        return float('inf'), float('inf')