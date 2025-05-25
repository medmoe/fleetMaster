import json
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from maintenance.factories import PartFactory, ServiceProviderFactory, PartsProviderFactory
from maintenance.models import MaintenanceReport
from maintenance.utils import has_gap_between_periods, period_key_comparator
from vehicles.models import Vehicle

PATH = 'maintenance/tests/fixtures/'

class MaintenanceReportOverviewTestCases(APITestCase):
    fixtures = [f'{PATH}user_and_userprofile_fixture', f'{PATH}parts_fixture', f'{PATH}providers_fixture', f'{PATH}vehicles_fixture', f'{PATH}reports_fixture',
                f'{PATH}events_fixture']

    def setUp(self):
        access_token = AccessToken.for_user(User.objects.get(pk=1)) # Picked a user from our loaded fixture
        self.vehicle = Vehicle.objects.filter(profile__user__pk=1, pk=1).first()
        self.client.cookies['access'] = access_token

    def test_successful_maintenance_report_retrieval(self):
        response = self.client.get(reverse('overview'), data={"vehicle_id": self.vehicle.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.vehicle.maintenance_reports.count(), len(response.data))


class GeneralMaintenanceDataTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.parts = PartFactory.create_batch(size=5, profile=cls.user_profile)
        cls.service_providers = ServiceProviderFactory.create_batch(size=5, profile=cls.user_profile)
        cls.parts_providers = PartsProviderFactory.create_batch(size=5, profile=cls.user_profile)

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_successful_data_retrieval(self):
        response = self.client.get(reverse("general-data"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, items in (
                ("parts", self.parts), ("service_providers", self.service_providers),
                ("part_providers", self.parts_providers)):
            self.assertIn(key, response.data)
            self.assertEqual(len(response.data[key]), len(items))

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
        for first_layer_key in ('total_maintenance_cost', 'yoy', 'top_recurring_issues', 'vehicle_health_metrics', 'health_alerts'):
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
            self.assertIn(vehicle_health_type, response.data['health_alerts'])
            for health_status in ('good', 'warning', 'critical'):
                self.assertIn(health_status, response.data['vehicle_health_metrics'][vehicle_health_type])
                if health_status == 'good': continue
                self.assertIn(health_status, response.data['health_alerts'][vehicle_health_type])

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
        alerts = {
            'vehicle_avg_health': {
                'warning': [],
                'critical': [],
            },
            'vehicle_insurance_health': {
                'warning': [],
                'critical': [],
            },
            'vehicle_license_health': {
                'warning': [],
                'critical': [],
            }
        }
        for vehicle in vehicles:
            fields = vehicle['fields']
            condition = get_condition(parse_date(fields['next_service_due']) - parse_date(fields['last_service_date']))
            if condition != 'good':
                alerts['vehicle_avg_health'][condition].append((fields['registration_number'], fields['make'], fields['model'], fields['year']))
            calculated_metrics['vehicle_avg_health'][condition] += 1.0
            condition = get_condition(parse_date(fields['insurance_expiry_date']) - date.today())
            if condition != 'good':
                alerts['vehicle_insurance_health'][condition].append((fields['registration_number'], fields['make'], fields['model'], fields['year']))
            calculated_metrics['vehicle_insurance_health'][condition] += 1.0
            condition = get_condition(parse_date(fields['license_expiry_date']) - date.today())
            if condition != 'good':
                alerts['vehicle_license_health'][condition].append((fields['registration_number'], fields['make'], fields['model'], fields['year']))
            calculated_metrics['vehicle_license_health'][condition] += 1.0

        for key in calculated_metrics.keys():
            for condition, count in calculated_metrics[key].items():
                calculated_metrics[key][condition] = count / len(vehicles) * 100

        # Assert fleet health metrics are correct
        vehicle_health_metrics = response.data['vehicle_health_metrics']
        for key in calculated_metrics.keys():
            for condition, avg in calculated_metrics[key].items():
                self.assertEqual(vehicle_health_metrics[key][condition], avg, f'{key} metric with {condition} is not correct')

        for key in alerts.keys():
            for condition, vehicles in alerts[key].items():
                self.assertEqual(len(response.data['health_alerts'][key][condition]), len(vehicles), f'{key} alert with {condition} is not correct')
                for vehicle in vehicles:
                    self.assertIn(vehicle, response.data['health_alerts'][key][condition], f'{key} alert with {condition} is not correct')

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
        part_names_counter = [(parts[part_id], count) for part_id, count in Counter(
            [event['fields']['part'] for event in events if event['model'] == 'maintenance.partpurchaseevent' and event['fields']['maintenance_report'] in report_ids]).items()]
        top_repeated_names = sorted(part_names_counter, key=lambda x: (-x[1], x[0]))[:3]

        # Assert API response values are correct
        self.assertEqual(len(response.data['top_recurring_issues']), len(top_repeated_names))
        for [part_name, count], item in zip(top_repeated_names, response.data['top_recurring_issues']):
            self.assertEqual(part_name, item['part__name'], f'{part_name} did not match with {item['part__name']}')
            self.assertEqual(count, item['count'], f'count of {part_name} did not match with the count of {item['part__name']}')

    def test_response_structure_when_filters_are_given(self):
        response = self.client.get(reverse('fleet-wide-overview', ), {"group_by": "monthly"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("grouped_metrics", response.data)
        for key, container in response.data["grouped_metrics"].items():
            self.assertIn("vehicle_avg", container)
            self.assertIn('mom_change', container)

    def test_correct_metrics_when_grouping_filter_is_given(self):
        for grouping_type in ('monthly', 'quarterly', 'yearly'):
            self._calculate_metrics_and_assert_response(group_by=grouping_type)

    def test_correct_metrics_when_time_range_is_given(self):
        self._calculate_metrics_and_assert_response(start_date="2024-10-01", end_date="2025-5-01")

    def test_empty_metrics_when_range_is_out_of_reports_range(self):
        self._calculate_metrics_and_assert_response(start_date="2026-12-01", end_date="2027-12-01")

    def test_correct_metrics_when_grouping_and_time_range_filters_are_given(self):
        self._calculate_metrics_and_assert_response(group_by="quarterly", start_date="2024-10-01", end_date="2025-5-01")

    def test_successful_response_when_vehicle_type_is_given(self):
        response = self.client.get(reverse('fleet-wide-overview'), {"vehicle_type": "TRUCK"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ('vehicle_health_metrics', 'total_maintenance_cost'):
            self.assertIn(key, response.data)

    def test_successful_response_when_vehicle_type_is_given_with_filters(self):
        response = self.client.get(reverse('fleet-wide-overview'), {"vehicle_type": "TRUCK", "group_by": "monthly"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ('vehicle_health_metrics', 'grouped_metrics'):
            self.assertIn(key, response.data)

    def test_fleet_overview_with_filters_when_no_vehicles_exist(self):
        Vehicle.objects.all().delete()
        response = self.client.get(reverse('fleet-wide-overview'), {"group_by": "monthly"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fleet_overview_when_no_reports_exist(self):
        MaintenanceReport.objects.all().delete()
        Vehicle.objects.all().delete()
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_fleet_overview_with_filters_when_no_reports_exist(self):
        MaintenanceReport.objects.all().delete()
        response = self.client.get(reverse('fleet-wide-overview'), {'group_by': 'quarterly', 'start_date': '2024-10-01'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def _calculate_metrics_and_assert_response(self, **kwargs) -> None:
        def get_period(date):
            if group_by == "yearly": return f'{date.year}'
            if group_by == "quarterly": return f'{date.year}-Q{(date.month - 1) // 3 + 1}'
            return f'{date.year}-{date.month}'

        # Load fixtures
        fixtures = self._load_fixtures(reports='reports_fixture.json', vehicles='vehicles_fixture.json')
        vehicles, reports = fixtures.get('vehicles', []), fixtures.get('reports', [])
        self.assertTrue(vehicles, "vehicles fixture empty")
        self.assertTrue(reports, "reports fixture empty")
        group_by = kwargs.get('group_by', 'monthly')
        start_date = kwargs.get('start_date', None)
        end_date = kwargs.get('end_date', None)

        # Manual calculations based on the grouping method
        calculated_cost = defaultdict(int)
        for report in reports:
            fields = report['fields']
            if start_date and end_date and not self._parse_date(start_date) <= self._parse_date(fields['start_date']) <= self._parse_date(end_date): continue
            calculated_cost[get_period(datetime.strptime(fields['start_date'], "%Y-%m-%d"))] += fields['total_cost']

        # Sort periods for consistent ordering
        calculated_cost = sorted(calculated_cost.items(), key=period_key_comparator)

        # Calculate metrics with yoy/qoq/mom changes
        metrics = [(calculated_cost[0][0], 0.0, round(calculated_cost[0][1] / len(vehicles), 2))] if calculated_cost else []

        for i in range(1, len(calculated_cost)):
            current_period, current_total_cost = calculated_cost[i]
            previous_period, previous_total_cost = calculated_cost[i - 1]
            period_change = 0.0
            if not has_gap_between_periods(current_period, previous_period) and previous_total_cost:
                period_change = round((current_total_cost - previous_total_cost) / previous_total_cost * 100, 2)
            metrics.append((current_period, period_change, round(current_total_cost / len(vehicles), 2)))

        # API call
        response = self.client.get(reverse('fleet-wide-overview'), kwargs)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        grouped_metrics = response.data['grouped_metrics']
        # Determine which change field to check based on grouping
        change_field = {"yearly": "yoy_change", "quarterly": "qoq_change", "monthly": "mom_change"}[group_by]

        # Assert returned data is correct
        for period, change, avg in metrics:
            self.assertIn(period, grouped_metrics)
            self.assertEqual(grouped_metrics[period][change_field], change, f'{period}: periodic change')
            self.assertEqual(grouped_metrics[period]['vehicle_avg'], avg, f'{period}: vehicle average')

    def _parse_date(self, date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").date()

    def _load_fixtures(self, **kwargs):
        """loads JSON fixture files from specified paths and returns them as a dictionary.

            Reads one or more JSON fixture files from the configured fixtures directory,
            with each file loaded into a dictionary key corresponding to the keyword argument name.

            Args:
                **kwargs: Keyword arguments where:
                         - key (str): The name to assign to the loaded fixture data
                         - value (str): The filename (relative to FIXTURES_PATH) of the JSON file to load
                         Example: `reports='reports.json'` will load 'reports.json' and store it
                         under the 'reports' key in the returned dictionary.

            Returns:
                dict: A dictionary mapping each input keyword to its corresponding loaded JSON data.
                      Example: {'reports': [...], 'events': [...]}

            Raises:
                FileNotFoundError: If any specified fixture file cannot be found.
                JSONDecodeError: If any file contains invalid JSON.
            """
        loaded_data = {}
        for key, path in kwargs.items():
            with open(f'{PATH}{path}', 'r') as file:
                loaded_data[key] = json.load(file)
        return loaded_data
