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


class VehicleDetailTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_one = UserProfileFactory.create()
        cls.user_two = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_one.user)
        cls.vehicles_one = VehicleFactory.create_batch(size=2, profile=cls.user_one)
        cls.vehicles_two = VehicleFactory.create_batch(size=2, profile=cls.user_two)

        cls.data = {
            'registration_number': 'REG123456',
            'make': 'Toyota',
            'model': '4Runner',
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

    def setUp(self):
        self.client.cookies["access"] = self.access_token

    def test_failed_vehicle_retrieval_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.get(reverse("vehicle-detail", args=[self.vehicles_one[0].id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_vehicle_retrieval_with_not_own_vehicle(self):
        response = self.client.get(reverse("vehicle-detail", args=[self.vehicles_two[0].id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_retrieval_of_non_existing_vehicle(self):
        response = self.client.get(reverse("vehicle-detail", args=["9999"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_retrieval_of_vehicle(self):
        response = self.client.get(reverse("vehicle-detail", args=[self.vehicles_one[0].id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fields = (
            "registration_number", "make", "model", "year", "vin", "color", "type", "status", "purchase_date", "last_service_date",
            "next_service_due",
            "mileage", "fuel_type", "capacity", "insurance_policy_number", "insurance_expiry_date", "license_expiry_date", "notes")
        for field in fields:
            self.assertIn(field, response.data)
            if isinstance(getattr(self.vehicles_one[0], field), datetime.date):
                self.assertEqual(getattr(self.vehicles_one[0], field).isoformat(), response.data[field])
            else:
                self.assertEqual(response.data[field], getattr(self.vehicles_one[0], field))

    def test_failed_vehicle_update_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.put(reverse("vehicle-detail", args=[self.vehicles_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_vehicle_update_with_not_own_vehicle(self):
        response = self.client.put(reverse("vehicle-detail", args=[self.vehicles_two[0].id]), data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_update_of_non_existing_vehicle(self):
        response = self.client.put(reverse("vehicle-detail", args=["9999"]), data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_failed_update_with_invalid_data(self):
        self.data["type"] = "invalid_type"
        response = self.client.put(reverse("vehicle-detail", args=[self.vehicles_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_update_of_vehicle(self):
        response = self.client.put(reverse("vehicle-detail", args=[self.vehicles_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        # Verify that all fields are updated correctly
        updated_vehicle = Vehicle.objects.get(id=self.vehicles_one[0].id)
        for field in self.data:
            if field in ("created_at", "updated_at"):
                continue
            if isinstance(getattr(updated_vehicle, field), datetime.date):
                self.assertEqual(getattr(updated_vehicle, field).isoformat(), self.data[field])
            elif field == "profile":
                self.assertEqual(getattr(updated_vehicle, field).id, self.data[field])
            else:
                self.assertEqual(getattr(updated_vehicle, field), self.data[field])

    def test_failed_vehicle_delete_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.delete(reverse("vehicle-detail", args=[self.vehicles_one[0].id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_vehicle_delete_with_not_own_vehicle(self):
        response = self.client.delete(reverse("vehicle-detail", args=[self.vehicles_two[0].id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_vehicle_delete_of_non_existing_vehicle(self):
        response = self.client.delete(reverse("vehicle-detail", args=["9999"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_delete_of_vehicle(self):
        response = self.client.delete(reverse("vehicle-detail", args=[self.vehicles_one[0].id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        vehicles = Vehicle.objects.filter(profile=self.user_one)
        self.assertEqual(len(vehicles), len(self.vehicles_one) - 1)
