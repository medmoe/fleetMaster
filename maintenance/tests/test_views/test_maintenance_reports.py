import copy
import random
from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from maintenance.factories import ServiceProviderEventFactory
from maintenance.factories import ServiceProviderFactory, PartFactory, PartsProviderFactory, MaintenanceReportFactory, PartPurchaseEventFactory
from maintenance.models import MaintenanceReport, PartPurchaseEvent, ServiceProviderEvent
from vehicles.factories import VehicleFactory


class MaintenanceReportListViewTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        MILEAGE = 20000

        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicle = VehicleFactory.create(profile=cls.user_profile, mileage=MILEAGE)
        cls.service_provider = ServiceProviderFactory.create()
        cls.parts = PartFactory.create_batch(size=20)
        cls.parts_provider = PartsProviderFactory.create()
        cls.maintenance_reports = MaintenanceReportFactory.create_batch(size=5, profile=cls.user_profile, vehicle=cls.vehicle)

    def setUp(self):
        self.client.cookies['access'] = self.access_token
        self.maintenance_report_data = {
            "profile": self.user_profile.id,
            "vehicle": self.vehicle.id,
            "start_date": date(2020, 12, 27).isoformat(),
            "end_date": date(2020, 12, 31).isoformat(),
            "description": "description",
            "mileage": 55555,
            "part_purchase_events": [
                {
                    "part": self.parts[0].id,
                    "provider": self.parts_provider.id,
                    "purchase_date": date(2020, 12, 31).isoformat(),
                    "cost": 2000}
            ],
            "service_provider_events": [
                {
                    "service_provider": self.service_provider.id,
                    "service_date": date(2020, 12, 31).isoformat(),
                    "cost": 2000,
                    "description": "description", }
            ],
        }

    def test_successful_retrieval_of_maintenance_reports(self):
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(self.maintenance_reports))

    def test_successful_creation_of_new_report(self):
        response = self.client.post(reverse("reports"), data=self.maintenance_report_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(self.maintenance_reports) + 1, MaintenanceReport.objects.count())
        self.assertIn("vehicle_details", response.data)
        self.assertIn("total_cost", response.data)
        total_cost = sum(event['cost'] for event in self.maintenance_report_data['part_purchase_events'])
        total_cost += sum(event['cost'] for event in self.maintenance_report_data['service_provider_events'])
        self.assertEqual(response.data["total_cost"], total_cost)

    def test_failed_creation_of_new_report_without_service_provider_event(self):
        self.maintenance_report_data.pop("service_provider_events")
        response = self.client.post(reverse('reports'), data=self.maintenance_report_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sync_latest_maintenance_report_to_vehicle(self):
        latest_report = MaintenanceReport.objects.order_by("-start_date").first()
        self.assertEqual(latest_report.mileage, self.vehicle.mileage)

    def test_unauthorised_access(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(reverse("reports"), data=self.maintenance_report_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MaintenanceReportDetailsTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicle = VehicleFactory.create(profile=cls.user_profile)
        cls.service_provider = ServiceProviderFactory.create()
        cls.maintenance_report = MaintenanceReportFactory.create(profile=cls.user_profile)
        cls.part_purchase_events = PartPurchaseEventFactory.create_batch(size=2, maintenance_report=cls.maintenance_report)
        cls.service_provider_events = ServiceProviderEventFactory.create_batch(size=1, maintenance_report=cls.maintenance_report)
        cls.part = PartFactory.create()
        cls.parts_provider = PartsProviderFactory.create()

    def setUp(self):
        self.client.cookies['access'] = self.access_token
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
                    "cost": 2000}
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
                "cost": 3000
            },
            {
                # New event without id
                "part": self.part.id,
                "provider": self.parts_provider.id,
                "purchase_date": date(2020, 12, 31).isoformat(),
                "cost": 2000
            }
        ]
        response = self.client.put(reverse('reports-details', args=[self.maintenance_report.id]),data=data,format='json')
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
        if ServiceProviderEvent.objects.filter(maintenance_report=self.maintenance_report).exists():
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        else:
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


