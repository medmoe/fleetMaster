import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from vehicles.factories import VehicleFactory
from .factories import DriverFactory
from .models import Driver, EmploymentStatusChoices


class DriversListTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicles = VehicleFactory.create_batch(size=5, profile=cls.user_profile)
        cls.drivers = DriverFactory.create_batch(size=5, profile=cls.user_profile)
        for driver in cls.drivers:
            driver.vehicles.set(cls.vehicles)

    def setUp(self):
        self.client.cookies["access"] = self.access_token

    def test_successful_drivers_retrieval(self):
        response = self.client.get(reverse("drivers"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(self.drivers))

        # Verify the content of the response
        driver_fields = [field.name for field in Driver._meta.get_fields()]
        for driver in response.data['results']:
            for field in driver_fields:
                self.assertIn(field, driver)

    def test_failed_drivers_retrieval_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.get(reverse("drivers"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_driver_creation(self):
        data = {
            "profile": self.user_profile.id,
            "vehicles": [vehicle.id for vehicle in self.vehicles],
            "first_name": "John",
            "last_name": "Doe",
            "email": "johndoe@example.com",
            "phone_number": "+1234567890",
            "licence_number": "D123456789",
            "licence_expiry_date": datetime.date(2025, 12, 31).isoformat(),
            "date_of_birth": datetime.date(1985, 5, 20).isoformat(),
            "address": "1234 Elm Street",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "country": "USA",
            "profile_picture": None,  # Or a file upload object if testing file upload
            "hire_date": datetime.date(2022, 1, 1).isoformat(),
            "employment_status": EmploymentStatusChoices.ACTIVE,
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "+0987654321",
            "notes": "Test driver creation."
        }
        response = self.client.post(reverse("drivers"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Driver.objects.count(), len(self.drivers) + 1)
        self.assertTrue(Driver.objects.filter(first_name=data["first_name"], last_name=data["last_name"], email=data["email"]))
