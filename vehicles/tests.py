import datetime
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory, UserProfile
from .factories import VehicleFactory
from .models import Vehicle, VehicleTypeChoices, StatusChoices


class VehiclesListTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicles = VehicleFactory.create_batch(size=2, profile=cls.user_profile)

    def setUp(self):
        self.client.cookies["access"] = self.access_token

    def test_successful_vehicles_retrieval(self):
        response = self.client.get(reverse("vehicles"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(self.vehicles))

    def test_failed_vehicles_retrieval_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.get(reverse("vehicles"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_vehicle_creation(self):
        data = {
            'profile': self.user_profile.id,
            'registration_number': 'REG123456',
            'make': 'Toyota',
            'model': 'Camry',
            'year': 2020,
            'vin': 'JT2BG28K1V0068507',
            'color': 'Blue',
            'type': VehicleTypeChoices.CAR,
            'status': StatusChoices.ACTIVE,
            'purchase_date': datetime.date(2025, 12, 31).isoformat(),
            'last_service_date': datetime.date(2025, 12, 31).isoformat(),
            'next_service_due': datetime.date(2025, 12, 31).isoformat(),
            'mileage': 15000,
            'fuel_type': 'Gasoline',
            'capacity': 5,
            'insurance_policy_number': 'INS123456789',
            'insurance_expiry_date': datetime.date(2025, 12, 31).isoformat(),
            'license_expiry_date': datetime.date(2025, 12, 31).isoformat(),
            'notes': 'Regular maintenance performed.',
            'created_at': datetime.date(2025, 12, 31).isoformat(),
            'updated_at': datetime.date(2025, 12, 31).isoformat(),
        }
        response = self.client.post(reverse("vehicles"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Vehicle.objects.count(), len(self.vehicles) + 1)
        self.assertTrue(Vehicle.objects.filter(registration_number=data['registration_number']))


