import json
from datetime import datetime, date, timezone
from unittest.mock import patch
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

PATH = 'maintenance/tests/fixtures/'


class FleetWideOverviewViewTestCases(APITestCase):
    fixtures = [f'{PATH}user_and_userprofile_fixture', f'{PATH}parts_fixture', f'{PATH}providers_fixture', f'{PATH}vehicles_fixture', f'{PATH}reports_fixture',
                f'{PATH}events_fixture']

    def setUp(self):
        access_token = AccessToken.for_user(User.objects.get(pk=1))  # This is the PK of the user created from the loaded fixtures
        self.client.cookies['access'] = access_token

    def test_failed_fleet_wide_overview_retrieval_with_unauthenticated_user(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_fleet_wide_overview_retrieval(self):
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the structure of the response is correct
        for first_layer_key in ('total_maintenance_cost', 'yoy', 'top_recurring_issues', 'vehicle_health_metrics'):
            self.assertIn(first_layer_key, response.data)

        for period in ('year', 'quarter', 'month'):
            self.assertIn(period, response.data['total_maintenance_cost'])
            for key in ('total', "vehicle_avg"):
                self.assertIn(key, response.data['total_maintenance_cost'][period])

        for issue in response.data['top_recurring_issues']:
            for key in ('part__name', 'count'):
                self.assertIn(key, issue)

        for vehicle_health_type in ('vehicle_avg_health', 'vehicle_insurance_health', 'vehicle_license_health'):
            self.assertIn(vehicle_health_type, response.data['vehicle_health_metrics'])
            for health_status in ('good', 'warning', 'critical'):
                self.assertIn(health_status, response.data['vehicle_health_metrics'][vehicle_health_type])

    def test_core_metrics_are_correct(self):
        def is_current(date_str: str, month=True) -> bool:
            """Check if a date is in the current month or quarter.
                Args:
                    date_str: Date in 'YYYY-MM-DD' format.
                    month: If True, checks current month; else checks current quarter.
                Returns:
                    bool: True if the date is in the current month / quarter, False otherwise.
                """

            def get_quarter(m: int) -> int:
                return (m - 1) // 3 + 1

            today = date(2025, 5, 1) # According to the fixtures, this date value represents today's date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            if month:
                return date_obj.year == today.year and date_obj.month == today.month

            return date_obj.year == today.year and get_quarter(date_obj.month) == get_quarter(today.month)

        try:
            with open(f'{PATH}reports_fixture.json', 'r') as reports_file, open(f'{PATH}vehicles_fixture.json', 'r') as vehicles_file:
                vehicles, reports = json.load(vehicles_file), json.load(reports_file)
        except FileNotFoundError:
            self.fail("Fixture files not found")

        self.assertTrue(vehicles, "Vehicle fixtures empty")
        self.assertTrue(reports, "Report fixtures empty")

        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert returned core metrics are correct
        yearly, monthly, quarterly = 0, 0, 0
        for report in reports:
            total = report['fields']['total_cost']
            start_date = report['fields']['start_date']
            yearly += total
            monthly += total if is_current(start_date) else 0
            quarterly += total if is_current(start_date, month=False) else 0

        for key, expected_cost in zip(['year', 'quarter', 'month'], [yearly, quarterly, monthly]):
            self.assertEqual(response.data['total_maintenance_cost'][key]['total'], expected_cost)
            self.assertEqual(response.data['total_maintenance_cost'][key]['vehicle_avg'], round(expected_cost / len(vehicles), 2))

        self.assertEqual(response.data['yoy'], 0.0)  # Our data has no reports in the previous year

    def test_vehicle_health_metrics_are_correct(self):
        pass

    def test_correct_number_for_vehicle_health(self):
        # We need to modify the dates of the service in our fleet
        # All vehicles have good health
        for vehicle in self.vehicles:
            vehicle.last_service_date = date(2025, 1, 1)
            vehicle.next_service_due = date(2025, 3, 1)
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.data["vehicle_avg_health"]["good"], 6.0)
