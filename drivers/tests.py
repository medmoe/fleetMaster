import re
from datetime import timedelta, datetime, date
from random import choice
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from factory import LazyAttribute
from factory import Sequence
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory, UserProfile
from vehicles.factories import VehicleFactory
from vehicles.models import Vehicle
from .authentication import DriverRefreshToken
from .factories import DriverFactory, DriverStartingShiftFactory
from .models import Driver, EmploymentStatusChoices, DriverStartingShift
from .serializers import DriverSerializer


class DriversListTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicles = VehicleFactory.create_batch(size=5, profile=cls.user_profile)
        cls.drivers = DriverFactory.create_batch(size=5, profile=cls.user_profile, vehicle=LazyAttribute(lambda _: choice(cls.vehicles)))
        cls.data = {
            "vehicle": cls.vehicles[0].id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "johndoe@example.com",
            "phone_number": "+1234567890",
            "license_number": "D123456789",
            "license_expiry_date": date(2025, 12, 31).isoformat(),
            "date_of_birth": date(1985, 5, 20).isoformat(),
            "address": "1234 Elm Street",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "country": "USA",
            "profile_picture": None,  # Or a file upload object if testing file upload
            "hire_date": date(2022, 1, 1).isoformat(),
            "employment_status": EmploymentStatusChoices.ACTIVE,
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "+0987654321",
            "notes": "Test driver creation."
        }

    def setUp(self):
        self.client.cookies["access"] = self.access_token

    def make_invalid_requests(self, field):
        del self.data[field]
        response = self.client.post(reverse("drivers"), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_drivers_retrieval(self):
        response = self.client.get(reverse("drivers"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(self.drivers))

    def test_failed_drivers_retrieval_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.get(reverse("drivers"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_driver_creation(self):
        response = self.client.post(reverse("drivers"), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Driver.objects.count(), len(self.drivers) + 1)
        self.assertTrue(Driver.objects.filter(first_name=self.data["first_name"], last_name=self.data["last_name"], email=self.data["email"]))
        self.assertIn("vehicle_details", response.data)
        # Assert that the vehicle details are the same as the provided vehicle
        self.assertEqual(response.data["vehicle_details"]["id"], self.data["vehicle"])
        self.assertTrue(re.match(r'^[2-9A-HJ-NP-Z]{6}-[2-9A-HJ-NP-Z]$', response.data['access_code']))

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

    def test_failed_driver_creation_with_no_license_expiry_date(self):
        self.make_invalid_requests("license_expiry_date")

    def test_failed_driver_creation_with_no_date_of_birth(self):
        self.make_invalid_requests("date_of_birth")

    def test_failed_driver_creation_with_no_hire_date(self):
        self.make_invalid_requests("hire_date")

    def test_successful_driver_creation_without_vehicle(self):
        self.data.pop("vehicle")
        response = self.client.post(reverse("drivers"), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Driver.objects.count(), len(self.drivers) + 1)


class DriverDetailTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_one = UserProfileFactory.create()
        cls.user_two = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_one.user)
        cls.vehicles_one = VehicleFactory.create_batch(size=2, profile=cls.user_one)
        cls.drivers_one = DriverFactory.create_batch(size=1, profile=cls.user_one, vehicle=LazyAttribute(lambda _: choice(cls.vehicles_one)))
        cls.vehicles_two = VehicleFactory.create_batch(size=2, profile=cls.user_two)
        cls.drivers_two = DriverFactory.create_batch(size=1, profile=cls.user_two, vehicle=LazyAttribute(lambda _: choice(cls.vehicles_two)))

        cls.data = {
            "vehicle": cls.vehicles_one[0].id,
            "first_name": cls.drivers_one[0].first_name,
            "last_name": cls.drivers_one[0].last_name,
            "email": cls.drivers_one[0].email,  # Updated email
            "phone_number": cls.drivers_one[0].phone_number,
            "license_number": "Updated License Number",  # Updated license number
            "license_expiry_date": date(2025, 12, 31).isoformat(),  # Updated expiry date
            "date_of_birth": date(2025, 12, 31).isoformat(),
            "address": cls.drivers_one[0].address,  # Updated address
            "city": cls.drivers_one[0].city,
            "state": cls.drivers_one[0].state,
            "zip_code": cls.drivers_one[0].zip_code,
            "country": cls.drivers_one[0].country,
            "hire_date": date(2025, 12, 31).isoformat(),
            "employment_status": EmploymentStatusChoices.INACTIVE,  # Updated employment status
            "emergency_contact_name": cls.drivers_one[0].emergency_contact_name,
            "emergency_contact_phone": cls.drivers_one[0].emergency_contact_phone,
            "notes": "Updated Notes"  # Updated notes
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
            elif isinstance(getattr(updated_driver, field), date):
                self.assertEqual(getattr(updated_driver, field).isoformat(), self.data[field])
            else:
                self.assertEqual(getattr(updated_driver, field), self.data[field])

    def test_failed_update_with_existing_email(self):
        self.data["email"] = self.drivers_two[0].email
        response = self.client.put(reverse("driver-detail", args=[self.drivers_one[0].id]), data=self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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

    def test_successful_update_of_driver_with_no_vehicle(self):
        # Create a driver without a vehicle
        driver = DriverFactory.create(profile=self.user_one, vehicle=None)
        serializer = DriverSerializer(driver)
        serializer.data['first_name'] = 'Updated first name'
        serializer.data['last_name'] = 'Updated last name'
        response = self.client.put(reverse('driver-detail', args=[driver.id]), serializer.data, format='json')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

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


class DriverLoginViewTests(APITestCase):
    def setUp(self):
        # Create a user and user profile
        self.user_profile = UserProfileFactory.create()

        # Create a driver with known credentials
        self.driver = DriverFactory.create(profile=self.user_profile)
        self.url = reverse('driver-login')

    def tearDown(self):
        cache.clear()

    def test_throttling_after_multiple_failed_attempts(self):
        data = {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth,
            "access_code": "INVALID-CODE"
        }
        for _ in range(10):  # Maximum number of failed attempts set in our settings
            response = self.client.post(self.url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_successful_login(self):
        """Test successful driver login with valid credentials."""
        data = {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth,
            "access_code": self.driver.access_code
        }

        response = self.client.post(self.url, data, format='json')
        # Check that the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('driver_id', response.data)
        self.assertEqual(response.data['driver_id'], self.driver.id)

        # Check that cookies are set
        self.assertIn('driver_refresh', response.cookies)
        self.assertIn('driver_access', response.cookies)

        # Verify the cookies are httponly and secure
        self.assertTrue(response.cookies['driver_refresh']['httponly'])
        self.assertTrue(response.cookies['driver_access']['httponly'])
        self.assertTrue(response.cookies['driver_refresh']['secure'])
        self.assertTrue(response.cookies['driver_access']['secure'])

    def test_invalid_credentials(self):
        """Test login failure with invalid credentials."""
        data = {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth,
            "access_code": "WRONG-CODE"  # Wrong access code
        }

        response = self.client.post(self.url, data, format='json')

        # Check that the response status code is 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["message"], "Invalid credentials")

        # Check that no cookies are set
        self.assertNotIn('refresh', response.cookies)
        self.assertNotIn('access', response.cookies)

    def test_missing_fields(self):
        """Test login with missing required fields."""
        # Test with missing first_name
        data = {
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth,
            "access_code": self.driver.access_code
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with missing last_name
        data = {
            "first_name": self.driver.first_name,
            "date_of_birth": self.driver.date_of_birth,
            "access_code": self.driver.access_code
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with missing date_of_birth
        data = {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "access_code": self.driver.access_code
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test with missing access_code
        data = {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth,
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_driver(self):
        """Test login with credentials that don't match any driver."""
        data = {
            "first_name": "Jane",  # Different name
            "last_name": "Smith",  # Different name
            "date_of_birth": "1990-01-15",
            "access_code": "ABC123-7"
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_case_sensitivity(self):
        """Test that first_name and last_name are case-sensitive."""
        data = {
            "first_name": self.driver.first_name.lower(),
            "last_name": self.driver.last_name.lower(),
            "date_of_birth": self.driver.date_of_birth,
            "access_code": self.driver.access_code
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_date_format(self):
        """Test that date_of_birth needs to be in the correct format."""
        # Test with different date format (MM/DD/YYYY instead of YYYY-MM-DD)
        data = {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth.strftime("%m/%d/%Y"),
            "access_code": self.driver.access_code
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], "Date of birth must be in YYYY-MM-DD format.")

    def test_failed_access_to_manager_endpoint(self):
        # Log the driver in
        data = {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth,
            "access_code": self.driver.access_code
        }
        self.client.post(self.url, data, format='json')
        response = self.client.get(reverse('drivers'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('drivers.authentication.DriverToken.for_driver')
    def test_token_generation_error(self, mock_for_driver):
        """Test handling of token generation errors."""
        # Mock the token generation to raise an exception
        mock_for_driver.side_effect = Exception("Token generation error")

        data = {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth,
            "access_code": self.driver.access_code,
        }

        # This should catch the exception and return a 500 error
        # Note: This assumes your view has error handling; if not, this test may fail
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_empty_request_body(self):
        """Test login with empty request body."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DriverStartingShiftViewAuthenticationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a user and user profile
        cls.user_profile = UserProfileFactory.create()
        # Create a driver
        cls.driver = DriverFactory.create(profile=cls.user_profile)
        cls.refresh = DriverRefreshToken.for_driver(cls.driver)
        cls.access = cls.refresh.access_token

        cls.login_data = {
            "first_name": cls.driver.first_name,
            "last_name": cls.driver.last_name,
            "date_of_birth": cls.driver.date_of_birth,
            "access_code": cls.driver.access_code
        }

        # Create some test data for creating a shift
        cls.shift_data = {
            "date": date.today().isoformat(),
            "time": "09:00:00",
            "load": 3000,
            "mileage": 50000,
            "delivery_areas": ["area1", "area2"],
            "status": True,
        }

    def test_authentication_required_for_post(self):
        """Test that authentication is required for POST requests"""
        # No authentication provided
        response = self.client.post(reverse('starting-shift'), self.shift_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authentication_required_for_get(self):
        """Test that authentication is required for GET requests"""
        # No authentication provided
        response = self.client.get(reverse('starting-shift'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_driver_jwt_authentication_accepted(self):
        """Test that DriverJWTAuthentication is accepted"""
        # Login to get the authentication cookies
        login_response = self.client.post(reverse('driver-login'), self.login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Now try to create a shift
        response = self.client.post(reverse('starting-shift'), self.shift_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('drivers.authentication.DriverJWTAuthentication.authenticate')
    def test_authentication_method_called(self, mock_authenticate):
        """Test that the DriverJWTAuthentication.authenticate method is called"""
        # Mock the authenticate method to return our driver
        mock_authenticate.return_value = (self.driver, self.access)

        # Make a request
        self.client.post(reverse('starting-shift'), self.shift_data, format='json')

        # Check that authenticate was called
        mock_authenticate.assert_called_once()

    def test_invalid_token_rejected(self):
        """Test that an invalid token is rejected"""
        # Set an invalid token in the cookie
        self.client.cookies['driver_access'] = 'invalid-token'

        # Make a request
        response = self.client.post(reverse('starting-shift'), self.shift_data, format='json')

        # Check that the request was rejected
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_token_rejected(self):
        """Test that an expired token is rejected"""
        # This would require more complex setup with token expiration
        # For simplicity, we'll mock the authentication to simulate an expired token
        with patch('drivers.authentication.DriverJWTAuthentication.authenticate') as mock_authenticate:
            from rest_framework_simplejwt.exceptions import InvalidToken
            mock_authenticate.side_effect = InvalidToken('Token is expired')

            # Make a request
            response = self.client.post(reverse('starting-shift'), self.shift_data, format='json')

            # Check that the request was rejected
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DriverStartingShiftViewPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a user profile and driver
        cls.user_profile = UserProfileFactory.create()
        cls.driver = DriverFactory.create(profile=cls.user_profile)

        # Create another user profile and driver
        cls.other_user_profile = UserProfileFactory.create()
        cls.other_driver = DriverFactory.create(profile=cls.other_user_profile)

        # Create login data for both drivers
        cls.login_data = {
            "first_name": cls.driver.first_name,
            "last_name": cls.driver.last_name,
            "date_of_birth": cls.driver.date_of_birth,
            "access_code": cls.driver.access_code
        }

        cls.other_login_data = {
            "first_name": cls.other_driver.first_name,
            "last_name": cls.other_driver.last_name,
            "date_of_birth": cls.other_driver.date_of_birth,
            "access_code": cls.other_driver.access_code
        }

        # Create shift data
        cls.shift_data = {
            "date": date.today().isoformat(),
            "time": "09:00:00",
            "load": 3000,
            "mileage": 50000,
            "delivery_areas": ["area1", "area2"],
            "status": True,
        }

    def test_driver_can_only_access_own_shifts(self):
        """Test that a driver can only access their own shifts"""
        # Create shifts for both drivers
        DriverStartingShiftFactory.create_batch(driver=self.driver, size=3)
        other_shifts = DriverStartingShiftFactory.create_batch(driver=self.other_driver, size=2)

        # Login as the first driver
        self.client.post(reverse('driver-login'), self.login_data, format='json')

        # Get shifts
        response = self.client.get(reverse('starting-shift'))

        # Check that only the first driver's shifts are returned
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

        # Verify none of the other driver's shifts are included
        shift_ids = [shift['id'] for shift in response.data['results']]
        for other_shift in other_shifts:
            self.assertNotIn(other_shift.id, shift_ids)


class DriverStartingShiftViewCRUDTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Create user profile and driver
        cls.user_profile = UserProfileFactory.create()
        cls.driver = DriverFactory.create(profile=cls.user_profile)

        # Create login data
        cls.login_data = {
            "first_name": cls.driver.first_name,
            "last_name": cls.driver.last_name,
            "date_of_birth": cls.driver.date_of_birth,
            "access_code": cls.driver.access_code
        }

        # Create shift data
        cls.shift_data = {
            "date": date.today().isoformat(),
            "time": "09:00:00",
            "load": 3000,
            "mileage": 50000,
            "delivery_areas": ["area1", "area2"],
            "status": True,
        }

    def setUp(self):
        # Login the driver before each test
        self.client.post(reverse('driver-login'), self.login_data, format='json')

    def test_create_shift_success(self):
        """Test successfully creating a shift"""
        initial_count = DriverStartingShift.objects.count()

        response = self.client.post(reverse('starting-shift'), self.shift_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DriverStartingShift.objects.count(), initial_count + 1)

        # Verify the shift data
        for key in self.shift_data:
            self.assertEqual(response.data[key], self.shift_data[key])

        # Verify the driver
        self.assertEqual(response.data['driver'], self.driver.id)

    def test_create_shift_invalid_data(self):
        """Test creating a shift with invalid data"""
        # Missing required field 'time'
        invalid_data = {
            "date": date.today().isoformat(),
            "load": 3000,
            "mileage": 50000,
            "delivery_areas": ["area1", "area2"],
            "status": True,
        }

        response = self.client.post(reverse('starting-shift'), invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time', response.data)

    def test_get_shifts_success(self):
        """Test successfully retrieving shifts"""
        # Create some shifts for this driver
        shifts = DriverStartingShiftFactory.create_batch(driver=self.driver, size=5)

        response = self.client.get(reverse('starting-shift'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 5)

        # Verify pagination
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)

    def test_get_shifts_ordering(self):
        """Test that shifts are ordered by date in descending order"""
        # Create shifts with different dates
        today = date.today()
        DriverStartingShiftFactory.create(driver=self.driver, date=today - timedelta(days=2))
        DriverStartingShiftFactory.create(driver=self.driver, date=today)
        DriverStartingShiftFactory.create(driver=self.driver, date=today - timedelta(days=1))

        response = self.client.get(reverse('starting-shift'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check ordering - should be newest first
        dates = [shift['date'] for shift in response.data['results']]
        self.assertEqual(dates, sorted(dates, reverse=True))


class DriverStartingShiftDetailTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a user and user profile
        cls.user_profile = UserProfileFactory.create()
        # Create a driver
        cls.driver = DriverFactory.create(profile=cls.user_profile)

    def setUp(self):
        # Authenticate the driver
        self.client.post(reverse('driver-login'), {
            "first_name": self.driver.first_name,
            "last_name": self.driver.last_name,
            "date_of_birth": self.driver.date_of_birth,
            "access_code": self.driver.access_code
        }, format='json')

    def test_successful_starting_shift_detail_retrieval(self):
        shift = DriverStartingShiftFactory.create(driver=self.driver)
        response = self.client.get(reverse('starting-shift-detail', args=[shift.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_successful_starting_shift_detail_update(self):
        shift = DriverStartingShiftFactory.create(driver=self.driver)
        data = {
            "date": date.today().isoformat(),
            "time": "09:00:00",
            "load": 3000,
            "mileage": 50000,
            "delivery_areas": ["area1", "area2", "area3"],
            "status": True,
        }
        response = self.client.put(reverse('starting-shift-detail', args=[shift.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        for key in ('date', 'time', 'load', 'mileage', 'delivery_areas', 'status'):
            self.assertEqual(response.data[key], data[key], f"Failed to update starting shift: {key} does not match")

    def test_successful_starting_shift_detail_delete(self):
        shift = DriverStartingShiftFactory.create(driver=self.driver)
        response = self.client.delete(reverse('starting-shift-detail', args=[shift.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DriverStartingShift.objects.filter(id=shift.id).exists())


class DriverAccessCodeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.driver = DriverFactory.create_batch(profile=cls.user_profile, size=2)

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_failed_update_with_unauthenticated_user(self):
        self.client.cookies["access"] = None
        response = self.client.put(reverse('access-code', args=[self.driver[0].id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_update_with_not_own_driver(self):
        other_user = UserProfileFactory.create()
        self.client.cookies['access'] = AccessToken.for_user(other_user.user)
        response = self.client.put(reverse('access-code', args=[self.driver[0].id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_does_not_exist(self):
        response = self.client.put(reverse('access-code', args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_update_of_driver_access_code(self):
        response = self.client.put(reverse('access-code', args=[self.driver[0].id]))
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data['access_code'] != self.driver[0].access_code)


class DriverOverdueFormsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        # Create a driver
        cls.driver = DriverFactory.create(profile=cls.user_profile)
        refresh = DriverRefreshToken.for_driver(cls.driver)
        # Set up tokens for driver authentication
        cls.access_token = refresh.access_token
        cls.url = reverse('overdue-forms')

        # Create another driver for comparison tests
        cls.other_driver = DriverFactory.create(profile=cls.user_profile)
        cls.other_token = DriverRefreshToken.for_driver(cls.other_driver).access_token

    def setUp(self):
        # Set up authentication for each test
        self.client.cookies['driver_access'] = self.access_token

    def test_authentication_required(self):
        self.client.cookies['driver_access'] = None
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_shifts_returns_all_dates(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('missing_dates', response.data)
        self.assertTrue(len(response.data['missing_dates']) == 30)
        start_date = datetime.now().date() - timedelta(days=29)
        for date in response.data['missing_dates']:
            self.assertEqual(date, start_date)
            start_date += timedelta(days=1)

    def test_with_some_shifts_present(self):
        """Test that dates with shifts are not included in missing dates"""
        today = datetime.now().date()
        start_date = today - timedelta(days=29)

        # Create a list of specific dates to create shifts for
        # Let's create shifts for every 5th day in the 30-day period
        shift_dates = [start_date + timedelta(days=i) for i in range(0, 30, 5)]

        # Use a sequence to cycle through these dates
        date_sequence = Sequence(lambda n: shift_dates[n % len(shift_dates)])

        # Create 6 shifts (one for each date in shift_dates)
        shifts = DriverStartingShiftFactory.create_batch(
            size=len(shift_dates),
            driver=self.driver,
            date=date_sequence
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have 30 - len(shift_dates) missing dates
        expected_missing_count = 30 - len(shift_dates)
        self.assertEqual(len(response.data['missing_dates']), expected_missing_count)

        # Convert response dates to date objects for comparison
        response_dates = [datetime.strptime(date, '%Y-%m-%d').date()
                          if isinstance(date, str) else date
                          for date in response.data['missing_dates']]

        # Verify none of the shift dates are in the response
        for date in shift_dates:
            self.assertNotIn(date, response_dates)

        # Also verify all the expected missing dates are present
        all_dates = [start_date + timedelta(days=i) for i in range(30)]
        expected_missing_dates = [date for date in all_dates if date not in shift_dates]
        self.assertEqual(sorted(response_dates), sorted(expected_missing_dates))

    def test_with_all_shifts_present(self):
        """Test that when a driver has shifts for all dates, no missing dates are returned"""
        today = datetime.now().date()
        start_date = today - timedelta(days=29)

        # Create shifts for all 30 days
        for i in range(30):
            DriverStartingShiftFactory.create(
                driver=self.driver,
                date=start_date + timedelta(days=i)
            )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have 0 missing dates
        self.assertEqual(len(response.data['missing_dates']), 0)

    def test_multiple_shifts_same_date(self):
        """Test that multiple shifts on the same date are correctly handled"""
        test_date = datetime.now().date() - timedelta(days=5)

        # Create multiple shifts for the same date
        DriverStartingShiftFactory.create_batch(
            size=3,
            driver=self.driver,
            date=test_date
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have 29 missing dates (30 - 1 with shifts)
        self.assertEqual(len(response.data['missing_dates']), 29)

        # Convert response dates to date objects for comparison
        response_dates = [datetime.strptime(date, '%Y-%m-%d').date()
                          if isinstance(date, str) else date
                          for date in response.data['missing_dates']]

        # Verify the test date is not in the response
        self.assertNotIn(test_date, response_dates)

    def test_driver_get_own_shifts_only(self):
        # create some shifts
        today = datetime.now().date()
        start_date = today - timedelta(days=29)
        for i in range(0, 30, 5):
            DriverStartingShiftFactory.create(
                driver=self.driver,
                date=start_date + timedelta(days=i)
            )
        self.client.cookies['driver_access'] = self.other_token
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['missing_dates']) == 30)
