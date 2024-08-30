import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory, UserProfile
from vehicles.factories import VehicleFactory
from vehicles.models import Vehicle
from .factories import DriverFactory
from .models import Driver, EmploymentStatusChoices


class DriversListTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicles = VehicleFactory.create_batch(size=5, profile=cls.user_profile)
        cls.drivers = DriverFactory.create_batch(size=5, profile=cls.user_profile)
        cls.data = {
            "vehicle": cls.vehicles[0].id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "johndoe@example.com",
            "phone_number": "+1234567890",
            "license_number": "D123456789",
            "license_expiry_date": datetime.date(2025, 12, 31).isoformat(),
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
        response = self.client.post(reverse("drivers"), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Driver.objects.count(), len(self.drivers) + 1)
        self.assertTrue(Driver.objects.filter(first_name=self.data["first_name"], last_name=self.data["last_name"], email=self.data["email"]))

    def test_successful_driver_creation_without_email(self):
        del self.data["email"]
        response = self.client.post(reverse("drivers"), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Driver.objects.count(), len(self.drivers) + 1)

    def test_failed_driver_creation_with_duplicate_license_number(self):
        # Create a driver
        driver_data = self.data.copy()
        driver_data["profile"] = self.user_profile
        driver_data["vehicle"] = self.vehicles[1]
        Driver.objects.create(**driver_data)
        # Create a new driver with the same license number
        response = self.client.post(reverse("drivers"), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Driver.objects.count(), len(self.drivers) + 1)

    def test_failed_driver_creation_with_invalid_date_format(self):
        # Try to create a driver with an invalid date format
        self.data["hire_date"] = "01-01-2022"
        response = self.client.post(reverse("drivers"), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DriverDetailTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_one = UserProfileFactory.create()
        cls.user_two = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_one.user)
        cls.vehicles_one = VehicleFactory.create_batch(size=2, profile=cls.user_one)
        cls.drivers_one = DriverFactory.create_batch(size=1, profile=cls.user_one)
        cls.vehicles_two = VehicleFactory.create_batch(size=2, profile=cls.user_two)
        cls.drivers_two = DriverFactory.create_batch(size=1, profile=cls.user_two)

        cls.data = {
            "vehicle": cls.vehicles_one[0].id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "johndoe_updated@example.com",  # Updated email
            "phone_number": "+1234567890",
            "license_number": "D123456789",  # Updated license number
            "license_expiry_date": datetime.date(2026, 12, 31).isoformat(),  # Updated expiry date
            "date_of_birth": datetime.date(1985, 5, 20).isoformat(),
            "address": "4567 Maple Avenue",  # Updated address
            "city": "Los Angeles",
            "state": "CA",
            "zip_code": "90001",
            "country": "USA",
            "hire_date": datetime.date(2022, 1, 1).isoformat(),
            "employment_status": EmploymentStatusChoices.INACTIVE,  # Updated employment status
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "+0987654321",
            "notes": "Updated driver information."  # Updated notes
        }

    def setUp(self):
        self.client.cookies["access"] = self.access_token

    def test_failed_driver_retrieval_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.get(reverse("driver-detail", args=[self.drivers_one[0].id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_driver_retrieval_with_not_own_driver(self):
        response = self.client.get(reverse("driver-detail", args=[self.drivers_two[0].id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_retrieval_of_no_existing_driver(self):
        response = self.client.get(reverse("driver-detail", args=["9999"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_retrieval_of_driver(self):
        response = self.client.get(reverse("driver-detail", args=[self.drivers_one[0].id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fields = ("first_name", "last_name", "email", "phone_number", "address")
        for field in fields:
            self.assertIn(field, response.data)
            self.assertEqual(response.data[field], getattr(self.drivers_one[0], field))

    def test_failed_driver_update_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_driver_update_with_not_own_driver(self):
        response = self.client.put(reverse("driver-detail", args=[self.drivers_two[0].id]), data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_update_of_no_existing_driver(self):
        response = self.client.put(reverse("driver-detail", args=["9999"]), data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_failed_update_with_invalid_data(self):
        self.data["employment_status"] = 'invalid_status'
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_update_of_driver(self):
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        # Verify that all fields are updated correctly
        updated_driver = Driver.objects.get(id=self.drivers_one[0].id)
        for field in self.data:
            if isinstance(getattr(updated_driver, field), Vehicle):
                self.assertEqual(getattr(updated_driver, field).id, self.data[field])
            elif isinstance(getattr(updated_driver, field), UserProfile):
                self.assertEqual(getattr(updated_driver, field).id, self.data[field])
            elif isinstance(getattr(updated_driver, field), datetime.date):
                self.assertEqual(getattr(updated_driver, field).isoformat(), self.data[field])
            else:
                self.assertEqual(getattr(updated_driver, field), self.data[field])

    def test_failed_update_with_existing_email(self):
        self.data["email"] = self.drivers_two[0].email
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['email'][0].code, 'unique')
        self.assertEqual(response.data['email'][0], 'driver with this email already exists.')

    def test_failed_update_with_existing_phone_number(self):
        self.data["phone_number"] = self.drivers_two[0].phone_number
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['phone_number'][0].code, 'unique')
        self.assertEqual(response.data['phone_number'][0], 'driver with this phone number already exists.')

    def test_failed_update_with_existing_license_number(self):
        self.data["license_number"] = self.drivers_two[0].license_number
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['license_number'][0].code, 'unique')
        self.assertEqual(response.data['license_number'][0], 'driver with this license number already exists.')

    def test_update_vehicle_assigned_to_driver(self):
        self.data["vehicle"] = self.vehicles_two[0].id
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['vehicle'], self.vehicles_two[0].id)

    def test_failed_update_with_wrong_date_format(self):
        # Update date fields with wrong format
        self.data["hire_date"] = "2022-13-01"  # Invalid month
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['hire_date'][0].code, 'invalid')
        self.assertEqual(response.data['hire_date'][0], 'Date has wrong format. Use one of these formats instead: YYYY-MM-DD.')

    def test_failed_driver_delete_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.delete(reverse("driver-detail", args=[self.drivers_one[0].id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_driver_delete_with_not_own_driver(self):
        response = self.client.delete(reverse("driver-detail", args=[self.drivers_two[0].id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_driver_delete_of_no_existing_driver(self):
        response = self.client.delete(reverse("driver-detail", args=["9999"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_delete_of_driver(self):
        response = self.client.delete(reverse("driver-detail", args=[self.drivers_one[0].id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        drivers = Driver.objects.filter(profile=self.user_one)
        self.assertFalse(drivers)
