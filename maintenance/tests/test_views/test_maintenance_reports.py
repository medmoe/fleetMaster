import copy
import random
from datetime import date

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from maintenance.factories import PartPurchaseEventFactory
from maintenance.factories import ServiceProviderEventFactory
from maintenance.models import MaintenanceReport, PartPurchaseEvent, ServiceProviderEvent, Part, PartsProvider, ServiceProvider
from vehicles.models import Vehicle

PATH = 'maintenance/tests/fixtures/'
MILEAGE = 20000


class MaintenanceReportListViewTestCases(APITestCase):
    fixtures = [f'{PATH}user_and_userprofile_fixture', f'{PATH}parts_fixture', f'{PATH}providers_fixture', f'{PATH}vehicles_fixture', f'{PATH}reports_fixture',
                f'{PATH}events_fixture']

    def setUp(self):
        access_token = AccessToken.for_user(User.objects.get(pk=1))  # This is the PK of the user created from the loaded fixtures
        self.client.cookies['access'] = access_token
        self.reports_count = MaintenanceReport.objects.filter(profile__user__pk=1).count()
        self.vehicle = Vehicle.objects.filter(profile__user__pk=1, pk=1).first()

        # The IDs are used based on what we have in the fixtures.
        self.maintenance_report_data = {
            "profile": 1,
            "vehicle": self.vehicle.id,
            "start_date": date(2030, 12, 27).isoformat(),
            "end_date": date(2030, 12, 31).isoformat(),
            "description": "description",
            "mileage": 55555,
            "part_purchase_events": [
                {
                    "part": 1,
                    "provider": 1,
                    "purchase_date": date(2020, 12, 31).isoformat(),
                    "cost": 2000,
                }
            ],
            "service_provider_events": [
                {
                    "service_provider": 1,
                    "service_date": date(2020, 12, 31).isoformat(),
                    "cost": 2000,
                    "description": "description", }
            ],
        }

    def test_successful_retrieval_of_maintenance_reports(self):
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], self.reports_count)

    def test_successful_creation_of_new_report(self):
        response = self.client.post(reverse("reports"), data=self.maintenance_report_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.reports_count + 1, MaintenanceReport.objects.filter(profile__user__pk=1).count())
        self.assertIn("vehicle_details", response.data)
        self.assertIn("total_cost", response.data)
        total_cost = sum(event['cost'] for event in self.maintenance_report_data['part_purchase_events'])
        total_cost += sum(event['cost'] for event in self.maintenance_report_data['service_provider_events'])
        self.assertEqual(response.data["total_cost"], total_cost)

    def test_correct_total_cost_after_report_creation(self):
        data = copy.deepcopy(self.maintenance_report_data)
        data["part_purchase_events"][0]['cost'] = 500
        data["service_provider_events"][0]['cost'] = 200
        response = self.client.post(reverse("reports"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["total_cost"], 700)

    def test_failed_creation_of_new_report_without_service_provider_event(self):
        self.maintenance_report_data.pop("service_provider_events")
        response = self.client.post(reverse('reports'), data=self.maintenance_report_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sync_latest_maintenance_report_to_vehicle(self):
        self.client.post(reverse("reports"), data=self.maintenance_report_data, format="json")
        latest_report = MaintenanceReport.objects.filter(profile__user__pk=1).order_by("-start_date").first()
        self.assertEqual(latest_report.mileage, Vehicle.objects.filter(pk=self.vehicle.id).first().mileage)

    def test_unauthorised_access(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(reverse("reports"), data=self.maintenance_report_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MaintenanceReportDetailsTestCases(APITestCase):
    fixtures = [f'{PATH}user_and_userprofile_fixture', f'{PATH}parts_fixture', f'{PATH}providers_fixture', f'{PATH}vehicles_fixture', f'{PATH}reports_fixture',
                f'{PATH}events_fixture']

    def setUp(self):
        access_token = AccessToken.for_user(User.objects.get(pk=1))  # This is the PK of the user created from the loaded fixtures
        self.vehicle = Vehicle.objects.filter(profile__user__pk=1, pk=1).first()
        self.part = Part.objects.all().first()
        self.parts_provider = PartsProvider.objects.filter(profile__user__pk=1, pk=1).first()
        self.service_provider = ServiceProvider.objects.filter(profile__user__pk=1, pk=1).first()
        self.maintenance_report = MaintenanceReport.objects.filter(profile__user__pk=1, pk=1).first()
        self.client.cookies['access'] = access_token
        self.data = {
            "start_date": date(2020, 12, 27).isoformat(),
            "end_date": date(2020, 12, 31).isoformat(),
            "cost": random.randint(0, 10 ** 8),
            "description": "description",
            "mileage": 55555,
            "vehicle": self.vehicle.id,
            "part_purchase_events": [
                {
                    "part": self.part.id,
                    "provider": self.parts_provider.id,
                    "purchase_date": date(2020, 12, 31).isoformat(),
                    "cost": 2000,
                }
            ],
            "service_provider_events": [
                {
                    "service_provider": self.service_provider.id,
                    "service_date": date(2020, 12, 31).isoformat(),
                    "cost": 2000,
                    "description": "updated description", }
            ],
            "vehicle_events": [
                {"vehicle": self.vehicle.id, }
            ]
        }

    def test_successful_maintenance_report_retrieval(self):
        response = self.client.get(reverse('reports-details', args=[self.maintenance_report.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.maintenance_report.id)

    def test_unauthorised_access(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse('reports-details', args=[self.maintenance_report.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_maintenance_report_update(self):
        response = self.client.put(reverse('reports-details', args=[self.maintenance_report.id]), data=self.data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        total_cost = sum(event['cost'] for event in self.data['part_purchase_events'])
        total_cost += sum(event['cost'] for event in self.data['service_provider_events'])
        self.assertEqual(response.data['total_cost'], total_cost)

    def test_update_with_existing_and_new_part_purchase_events(self):
        """Test updating a maintenance report with both existing and new part purchase events."""
        # Create an existing part purchase event for this maintenance report
        existing_event = PartPurchaseEventFactory.create(
            maintenance_report=self.maintenance_report,
            part=self.part,
            provider=self.parts_provider
        )
        # Add both the existing event (with id) and a new event to the update data
        data = copy.deepcopy(self.data)
        data["part_purchase_events"] = [
            {
                "id": existing_event.id,  # Existing event
                "part": self.part.id,
                "provider": self.parts_provider.id,
                "purchase_date": date(2020, 12, 30).isoformat(),
                "cost": 3000,
            },
            {
                # New event without id
                "part": self.part.id,
                "provider": self.parts_provider.id,
                "purchase_date": date(2020, 12, 31).isoformat(),
                "cost": 2000,
            }
        ]
        response = self.client.put(reverse('reports-details', args=[self.maintenance_report.id]), data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Verify that the new part purchase event was created
        self.assertEqual(self.maintenance_report.part_purchase_events.count(), 2)
        total_cost = sum(event['cost'] for event in data['part_purchase_events'])
        total_cost += sum(event['cost'] for event in data['service_provider_events'])
        self.assertEqual(PartPurchaseEvent.objects.filter(maintenance_report=self.maintenance_report).count(), 2)
        self.assertEqual(response.data['total_cost'], total_cost)

    def test_update_with_existing_and_new_service_provider_events(self):
        """Test updating a maintenance report with both existing and new service provider events."""
        # Create an existing service provider event for this maintenance report
        existing_event = ServiceProviderEventFactory.create(
            maintenance_report=self.maintenance_report,
            service_provider=self.service_provider
        )

        # Add both the existing event (with id) and a new event to the update data
        data = copy.deepcopy(self.data)
        data["service_provider_events"] = [
            {
                "id": existing_event.id,  # Existing event
                "service_provider": self.service_provider.id,
                "service_date": date(2020, 12, 30).isoformat(),
                "cost": 3000,
                "description": "updated existing description"
            },
            {
                # New event without id
                "service_provider": self.service_provider.id,
                "service_date": date(2020, 12, 31).isoformat(),
                "cost": 2000,
                "description": "new service description"
            }
        ]

        response = self.client.put(
            reverse('reports-details', args=[self.maintenance_report.id]),
            data=data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        # Verify that the new service provider event was created
        self.assertEqual(self.maintenance_report.service_provider_events.count(), 2)
        total_cost = sum(event['cost'] for event in data['service_provider_events'])
        total_cost += sum(event['cost'] for event in data['part_purchase_events'])
        self.assertEqual(response.data['total_cost'], total_cost)

    def test_update_with_part_details_and_provider_details(self):
        """Test that part_details and provider_details are properly handled in update."""
        data = copy.deepcopy(self.data)
        data["part_purchase_events"] = [
            {
                "part": self.part.id,
                "provider": self.parts_provider.id,
                "purchase_date": date(2020, 12, 31).isoformat(),
                "cost": 2000,
                "part_details": {"name": "Test Part"},  # These should be removed by the update method
                "provider_details": {"name": "Test Provider"}  # These should be removed by the update method
            }
        ]

        response = self.client.put(
            reverse('reports-details', args=[self.maintenance_report.id]),
            data=data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Verify that a part purchase event was created
        self.assertEqual(self.maintenance_report.part_purchase_events.count(), 1)

    def test_update_with_service_provider_details(self):
        """Test that service_provider_details are properly handled in update."""
        data = copy.deepcopy(self.data)
        data["service_provider_events"] = [
            {
                "service_provider": self.service_provider.id,
                "service_date": date(2020, 12, 31).isoformat(),
                "cost": 2000,
                "description": "updated description",
                "service_provider_details": {"name": "Test Service Provider"}  # These should be removed by the update method
            }
        ]

        response = self.client.put(
            reverse('reports-details', args=[self.maintenance_report.id]),
            data=data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        # Verify that a service provider event was created
        self.assertEqual(self.maintenance_report.service_provider_events.count(), 1)

    def test_update_with_empty_events_lists(self):
        """Test update with empty part_purchase_events and service_provider_events lists."""
        data = copy.deepcopy(self.data)
        data["part_purchase_events"] = []
        data["service_provider_events"] = []

        response = self.client.put(
            reverse('reports-details', args=[self.maintenance_report.id]),
            data=data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_with_vehicle_details(self):
        """Test updating with vehicle_details in the data."""
        data = copy.deepcopy(self.data)
        data["vehicle_details"] = {"make": "Toyota", "model": "Corolla"}

        response = self.client.put(
            reverse('reports-details', args=[self.maintenance_report.id]),
            data=data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        # Verify that basic fields were updated correctly despite vehicle_details presence
        updated_report = MaintenanceReport.objects.get(id=self.maintenance_report.id)
        self.assertEqual(str(updated_report.start_date), data["start_date"])

    def test_successful_maintenance_report_deletion(self):
        # Store the report ID before deletion for later queries
        report_id = self.maintenance_report.id

        # Verify we have events before deletion (optional, but good practice)
        self.assertTrue(PartPurchaseEvent.objects.filter(maintenance_report_id=report_id).exists())
        self.assertTrue(ServiceProviderEvent.objects.filter(maintenance_report_id=report_id).exists())

        # Perform the deletion
        response = self.client.delete(reverse("reports-details", args=[report_id]))

        # Assert response is successful
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Assert main report is deleted
        self.assertFalse(MaintenanceReport.objects.filter(id=report_id).exists())

        # Assert all related events are deleted
        self.assertFalse(
            PartPurchaseEvent.objects.filter(maintenance_report_id=report_id).exists(),
            "Part purchase events were not deleted with the maintenance report"
        )
        self.assertFalse(
            ServiceProviderEvent.objects.filter(maintenance_report_id=report_id).exists(),
            "Service provider events were not deleted with the maintenance report"
        )

class VehicleReportsListTestCases(APITestCase):
    fixtures = [f'{PATH}user_and_userprofile_fixture', f'{PATH}parts_fixture', f'{PATH}providers_fixture', f'{PATH}vehicles_fixture', f'{PATH}reports_fixture',
                f'{PATH}events_fixture']

    def setUp(self):
        access_token = AccessToken.for_user(User.objects.get(pk=1))  # This is the PK of the user created from the loaded fixtures
        self.vehicle = Vehicle.objects.filter(profile__user__pk=1, pk=1).first()
        self.client.cookies['access'] = access_token

    def test_failed_request_on_unauthorised_access(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse("vehicle-reports-list", args=[self.vehicle.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_request_on_non_existing_vehicle(self):
        response = self.client.get(reverse("vehicle-reports-list", args=[100]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_request_on_month_not_given(self):
        response = self.client.get(reverse("vehicle-reports-list", args=[self.vehicle.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ('available_months', 'results'):
            self.assertIn(key, response.data, f"Missing key {key} in response data")
        self.assertFalse(response.data['results'])

        # enumerate available months
        vehicle_reports = MaintenanceReport.objects.filter(profile__user__pk=1, vehicle__id=self.vehicle.id).order_by('start_date')
        available_months = set()
        for report in vehicle_reports:
            available_months.add(report.start_date.strftime("%Y-%m"))

        # assert available months are correct
        available_months = sorted(available_months, reverse=True)
        self.assertEqual(response.data['available_months'], available_months)

    def test_successful_request_on_month_given(self):
        response = self.client.get(reverse("vehicle-reports-list", args=[self.vehicle.id]), data={"month": "2025-01"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ('month', 'count', 'results'):
            self.assertIn(key, response.data, f"Missing key {key} in response data")
        self.assertEqual(response.data['month'], "2025-01")
        vehicle_reports_count = MaintenanceReport.objects.filter(profile__user__pk=1,
                                                                 vehicle__id=self.vehicle.id,
                                                                 start_date__year=2025,
                                                                 start_date__month=1).count()
        self.assertEqual(response.data['count'], vehicle_reports_count)

    def test_request_on_invalid_month(self):
        response = self.client.get(reverse("vehicle-reports-list", args=[self.vehicle.id]), data={"month": "invalid format"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['results'])



