import json
from collections import Counter
from datetime import datetime, date, timedelta

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

            nonlocal today
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            if month:
                return date_obj.year == today.year and date_obj.month == today.month

            return date_obj.year == today.year and get_quarter(date_obj.month) == get_quarter(today.month)

        # Load fixtures
        fixtures = self._load_fixtures(reports='reports_fixture.json', vehicles='vehicles_fixture.json')
        reports, vehicles = fixtures.get('reports', []), fixtures.get('vehicles', [])
        self.assertTrue(vehicles, "Vehicle fixtures empty")
        self.assertTrue(reports, "Report fixtures empty")

        # API call
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert returned core metrics are correct
        current_year, current_month, current_quarter = 0, 0, 0
        previous_year_cost = 0
        today = date(2025, 5, 1)  # According to the fixtures, this date value represents today's date
        for report in reports:
            total = report['fields']['total_cost']
            start_date = report['fields']['start_date']
            if datetime.strptime(start_date, "%Y-%m-%d").date().year == today.year:
                current_year += total
            else:
                previous_year_cost += total
            current_month += total if is_current(start_date) else 0
            current_quarter += total if is_current(start_date, month=False) else 0

        for key, expected_cost in zip(['year', 'quarter', 'month'], [current_year, current_quarter, current_month]):
            self.assertEqual(response.data['total_maintenance_cost'][key]['total'], expected_cost)
            self.assertEqual(response.data['total_maintenance_cost'][key]['vehicle_avg'], round(expected_cost / len(vehicles), 2))

        self.assertTrue(previous_year_cost != 0)
        self.assertEqual(response.data['yoy'], round((current_year - previous_year_cost) / previous_year_cost * 100, 2))

    def test_vehicle_health_metrics_are_correct(self):
        def parse_date(date_str: str) -> date:
            return datetime.strptime(date_str, "%Y-%m-%d").date()

        def get_condition(duration: timedelta) -> str:
            if duration > timedelta(days=30): return 'good'
            if duration > timedelta(days=0): return 'warning'
            return 'critical'

        # Load fixtures
        fixtures = self._load_fixtures(vehicles="vehicles_fixture.json")
        vehicles = fixtures.get('vehicles', [])
        self.assertTrue(vehicles, "Vehicles fixture empty")

        # API call and manual calculations
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        calculated_metrics = {"vehicle_avg_health": {'good': 0.0, 'warning': 0.0, 'critical': 0.0},
                              "vehicle_insurance_health": {'good': 0.0, 'warning': 0.0, 'critical': 0.0},
                              "vehicle_license_health": {'good': 0.0, 'warning': 0.0, 'critical': 0.0}}
        for vehicle in vehicles:
            fields = vehicle['fields']
            calculated_metrics['vehicle_avg_health'][get_condition(parse_date(fields['next_service_due']) - parse_date(fields['last_service_date']))] += 1.0
            calculated_metrics['vehicle_insurance_health'][get_condition(parse_date(fields['insurance_expiry_date']) - date.today())] += 1.0
            calculated_metrics['vehicle_license_health'][get_condition(parse_date(fields['license_expiry_date']) - date.today())] += 1.0

        for key in calculated_metrics.keys():
            for condition, count in calculated_metrics[key].items():
                calculated_metrics[key][condition] = count / len(vehicles) * 100

        # Assert fleet health metrics are correct
        vehicle_health_metrics = response.data['vehicle_health_metrics']
        for key in calculated_metrics.keys():
            for condition, avg in calculated_metrics[key].items():
                self.assertEqual(vehicle_health_metrics[key][condition], avg, f'{key} metric with {condition} is not correct')

    def test_top_recurring_part_issues(self):
        def is_current_year(date_str: str) -> bool:
            return datetime.strptime(date_str, "%Y-%m-%d").year == 2025  # Fixed year due to the nature of our fixtures

        # Load fixtures
        fixtures = self._load_fixtures(reports='reports_fixture.json', events='events_fixture.json', parts='parts_fixture.json')
        reports, events, parts = fixtures.get('reports', []), fixtures.get('events', []), fixtures.get('parts', [])
        self.assertTrue(reports, "reports fixture empty")
        self.assertTrue(events, 'events fixture empty')
        self.assertTrue(parts, 'parts fixture empty')

        # API call
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manual calculations
        report_ids = set([report['pk'] for report in reports if is_current_year(report['fields']['start_date'])])
        parts = {part['pk']: part['fields']['name'] for part in parts}
        part_names_counter = [(parts[part_id], count) for part_id, count in Counter([event['fields']['part'] for event in events if event['model'] == 'maintenance.partpurchaseevent' and event['fields']['maintenance_report'] in report_ids]).items()]
        top_repeated_names = sorted(part_names_counter, key=lambda x: (-x[1], x[0]))[:3]

        # Assert API response values are correct
        self.assertEqual(len(response.data['top_recurring_issues']), len(top_repeated_names))
        for [part_name, count], item in zip(top_repeated_names, response.data['top_recurring_issues']):
            self.assertEqual(part_name, item['part__name'], f'{part_name} did not match with {item['part__name']}')
            self.assertEqual(count, item['count'], f'count of {part_name} did not match with the count of {item['part__name']}')

    def _load_fixtures(self, **kwargs):
        loaded_data = {}
        for key, path in kwargs.items():
            with open(f'{PATH}{path}', 'r') as file:
                loaded_data[key] = json.load(file)
        return loaded_data

