from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from maintenance.factories import MaintenanceReportFactory, PartPurchaseEventFactory, PartFactory, PartsProviderFactory
from maintenance.models import PartPurchaseEvent
from vehicles.factories import VehicleFactory


class PartPurchaseEventDetailsTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicle = VehicleFactory.create(profile=cls.user_profile)
        cls.maintenance_report = MaintenanceReportFactory.create(profile=cls.user_profile, vehicle=cls.vehicle)
        cls.part_purchase_event = PartPurchaseEventFactory.create(maintenance_report=cls.maintenance_report)
        cls.part = PartFactory.create()
        cls.parts_provider = PartsProviderFactory.create()

    def setUp(self):
        self.client.cookies['access'] = self.access_token
        self.part_purchase_event_data = {
            "part": self.part.id,
            "provider": self.parts_provider.id,
            "maintenance_report": self.maintenance_report.id,
            "purchase_date": date(2020, 12, 31).isoformat(),
            "cost": 2000,
        }

    def test_failed_part_purchase_event_update_with_unauthenticated_user(self) -> None:
        self.client.cookies['access'] = None
        response = self.client.put(reverse('part-purchase-event-details', args=[self.part_purchase_event.id]), data=self.part_purchase_event_data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_part_purchase_event_update_with_non_existed_maintenance_report(self) -> None:
        self.part_purchase_event_data["maintenance_report"] = 9999
        response = self.client.put(reverse('part-purchase-event-details', args=[self.part_purchase_event.id]), data=self.part_purchase_event_data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_part_purchase_event_update_with_non_existed_part(self) -> None:
        self.part_purchase_event_data["part"] = 9999
        response = self.client.put(reverse('part-purchase-event-details', args=[self.part_purchase_event.id]), data=self.part_purchase_event_data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_part_purchase_event_update_with_non_existed_parts_provider(self) -> None:
        self.part_purchase_event_data["provider"] = 9999
        response = self.client.put(reverse('part-purchase-event-details', args=[self.part_purchase_event.id]), data=self.part_purchase_event_data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_part_purchase_event_with_invalid_date(self) -> None:
        self.part_purchase_event_data["purchase_date"] = "some wrong date format"
        response = self.client.put(reverse('part-purchase-event-details', args=[self.part_purchase_event.id]), data=self.part_purchase_event_data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_part_purchase_event_with_invalid_cost(self) -> None:
        self.part_purchase_event_data["cost"] = "cost"
        response = self.client.put(reverse('part-purchase-event-details', args=[self.part_purchase_event.id]), data=self.part_purchase_event_data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_part_purchase_event_update(self):
        response = self.client.put(reverse('part-purchase-event-details', args=[self.part_purchase_event.id]), data=self.part_purchase_event_data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(PartPurchaseEvent.objects.get(id=self.part_purchase_event.id).cost, self.part_purchase_event_data["cost"])

    def test_successful_part_purchase_event_deletion(self):
        response = self.client.delete(reverse('part-purchase-event-details', args=[self.part_purchase_event.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(PartPurchaseEvent.DoesNotExist):
            PartPurchaseEvent.objects.get(id=self.part_purchase_event.id)
