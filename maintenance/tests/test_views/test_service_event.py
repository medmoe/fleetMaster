from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from maintenance.factories import MaintenanceReportFactory, ServiceProviderEventFactory, ServiceProviderFactory
from maintenance.models import ServiceProviderEvent
from vehicles.factories import VehicleFactory


class ServiceProviderEventDetailsTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicle = VehicleFactory.create(profile=cls.user_profile)
        cls.maintenance_report = MaintenanceReportFactory.create(profile=cls.user_profile, vehicle=cls.vehicle)
        cls.service_provider_event = ServiceProviderEventFactory.create(maintenance_report=cls.maintenance_report)
        cls.service_provider = ServiceProviderFactory.create()

    def setUp(self):
        self.client.cookies['access'] = self.access_token
        self.service_provider_event_data = {
            "service_provider": self.service_provider.id,
            "maintenance_report": self.maintenance_report.id,
            "service_date": date(2020, 12, 31).isoformat(),
            "cost": 2000,
            "description": "Service description",
        }

    def test_failed_service_provider_event_update_with_unauthenticated_user(self) -> None:
        self.client.cookies['access'] = None
        response = self.client.put(reverse('service-provider-event-details', args=[self.service_provider_event.id]),
                                   data=self.service_provider_event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_service_provider_event_update_with_non_existed_maintenance_report(self) -> None:
        self.service_provider_event_data["maintenance_report"] = 9999
        response = self.client.put(reverse('service-provider-event-details', args=[self.service_provider_event.id]),
                                   data=self.service_provider_event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_service_provider_event_update_with_non_existed_service_provider(self) -> None:
        self.service_provider_event_data["service_provider"] = 9999
        response = self.client.put(reverse('service-provider-event-details', args=[self.service_provider_event.id]),
                                   data=self.service_provider_event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_service_provider_event_update_with_invalid_date(self) -> None:
        self.service_provider_event_data["service_date"] = "invalid date format"
        response = self.client.put(reverse('service-provider-event-details', args=[self.service_provider_event.id]),
                                   data=self.service_provider_event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_service_provider_event_update_with_invalid_cost(self) -> None:
        self.service_provider_event_data["cost"] = "invalid cost"
        response = self.client.put(reverse('service-provider-event-details', args=[self.service_provider_event.id]),
                                   data=self.service_provider_event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_service_provider_event_update(self):
        response = self.client.put(reverse('service-provider-event-details', args=[self.service_provider_event.id]),
                                   data=self.service_provider_event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(ServiceProviderEvent.objects.get(id=self.service_provider_event.id).cost, self.service_provider_event_data["cost"])

    def test_failed_deletion_for_last_service_provider_event(self):
        response = self.client.delete(reverse('service-provider-event-details', args=[self.service_provider_event.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_service_provider_event_deletion(self):
        ServiceProviderEventFactory.create(maintenance_report=self.maintenance_report)
        response = self.client.delete(reverse('service-provider-event-details', args=[self.service_provider_event.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(ServiceProviderEvent.DoesNotExist):
            ServiceProviderEvent.objects.get(id=self.service_provider_event.id)
