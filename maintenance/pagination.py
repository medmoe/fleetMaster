from collections import defaultdict
from datetime import datetime

from rest_framework.pagination import BasePagination
from rest_framework.response import Response


class MonthlyPagination(BasePagination):
    """
    Pagination class that groups maintenance reports by month
    """

    page_query_param = 'month'
    page_query_description = 'Month in YYYY-MM format to filter reports.'

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.month_param = request.query_params.get(self.page_query_param)

        # Group all reports by month
        self.reports_by_month = defaultdict(list)
        for report in queryset:
            month_key = report.start_date.strftime('%Y-%m')
            self.reports_by_month[month_key].append(report)

        # Return the list of reports for the current month if requested
        if not self.month_param:
            self.available_months = sorted(self.reports_by_month.keys(), reverse=True)
            self.current_month_data = []

            # Only return the list of available months, not the actual reports
            return []

        # Return reports for the requested month
        try:
            # Validate month format
            datetime.strptime(self.month_param, '%Y-%m')
            self.current_month_data = self.reports_by_month.get(self.month_param, [])
            return self.current_month_data
        except ValueError:
            self.current_month_data = []
            return []

    def get_paginated_response(self, data):
        if not self.month_param:
            # When no month is specified, return the list of available months
            return Response({
                'available_months': self.available_months,
                'results': []
            })

        # When a specific month is requested, return the list of reports for that month
        return Response({
            'month': self.month_param,
            'count': len(self.current_month_data),
            'results': data
        })
