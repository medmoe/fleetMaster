import random
from datetime import datetime, timedelta, date

import factory
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from vehicles.factories import VehicleFactory
from .factories import PartFactory, PartsProviderFactory, ServiceProviderFactory, PartPurchaseEventFactory, \
    MaintenanceReportFactory, ServiceProviderEventFactory
from .models import Part, PartsProvider, ServiceProvider, MaintenanceReport


class PartsTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.parts = PartFactory.create_batch(size=10)

    def setUp(self):
        self.client.cookies['access'] = self.access_token
        self.part = {
            "name": "part name",
            "description": "part description",
        }

    def test_failed_parts_retrieval_with_unauthenticated_user(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse('parts'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_parts_retrieval(self):
        response = self.client.get(reverse("parts"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(self.parts))

    def test_failed_part_creation_with_unauthenticated_user(self):
        self.client.cookies['access'] = None
        response = self.client.post(reverse('parts'), self.part, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_part_creation(self):
        response = self.client.post(reverse('parts'), self.part, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key, value in self.part.items():
            self.assertEqual(response.data.get(key), value)

        self.assertEqual(Part.objects.count(), len(self.parts) + 1)
        part = Part.objects.get(id=response.data.get('id'))
        for key, value in self.part.items():
            self.assertEqual(getattr(part, key), value)


class PartDetailsTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.part = PartFactory.create()

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_successful_retrieval_of_part(self):
        response = self.client.get(reverse("part-details", args=[self.part.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in response.data.items():
            self.assertEqual(getattr(self.part, key), value)

    def test_failed_retrieval_of_non_existed_part(self):
        response = self.client.get(reverse('part-details', args=['9999']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_part_update(self):
        updated_part = {
            "name": "updated part name",
            "description": "updated part description",
        }
        response = self.client.put(reverse('part-details', args=[self.part.id]), updated_part, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        for key, value in updated_part.items():
            self.assertEqual(getattr(Part.objects.get(id=self.part.id), key), value)

    def test_failed_update_of_non_existed_part(self):
        updated_part = {
            "name": "updated part name",
            "description": "updated part description",
        }
        response = self.client.put(reverse('part-details', args=['9999']), updated_part, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_part_delete(self):
        response = self.client.delete(reverse('part-details', args=[self.part.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(Part.DoesNotExist):
            Part.objects.get(id=self.part.id)

    def test_failed_delete_of_non_existed_part(self):
        response = self.client.delete(reverse('part-details', args=['9999']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_access(self):
        # Unset access token to simulate unauthenticated user
        self.client.cookies['access'] = None

        # Test GET method
        response = self.client.get(reverse("part-details", args=[self.part.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test PUT method
        updated_part = {
            "name": "test part name",
            "description": "test part description",
        }
        response = self.client.put(reverse('part-details', args=[self.part.id]), updated_part, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test DELETE method
        response = self.client.delete(reverse('part-details', args=[self.part.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ServiceProviderListTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.service_providers = ServiceProviderFactory.create_batch(size=10)

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_failed_service_provider_retrieval_with_unauthenticated_user(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse('service-providers'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_service_provider_retrieval(self):
        response = self.client.get(reverse("service-providers"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(self.service_providers))


class ServiceProviderDetailsTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.service_provider = ServiceProviderFactory.create()

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_successful_retrieval_of_service_provider(self):
        response = self.client.get(reverse("service-provider-details", args=[self.service_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in response.data.items():
            self.assertEqual(getattr(self.service_provider, key), value)

    def test_failed_retrieval_of_non_existed_service_provider(self):
        response = self.client.get(reverse('service-provider-details', args=['9999']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_service_provider_update(self):
        updated_service_provider = {
            "name": "updated service provider name",
            "address": "updated address",
        }
        response = self.client.put(reverse('service-provider-details', args=[self.service_provider.id]),
                                   updated_service_provider, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        for key, value in updated_service_provider.items():
            self.assertEqual(getattr(ServiceProvider.objects.get(id=self.service_provider.id), key), value)

    def test_failed_update_of_non_existed_service_provider(self):
        updated_service_provider = {
            "name": "updated service provider name",
            "address": "updated address",
        }
        response = self.client.put(reverse('service-provider-details', args=['9999']), updated_service_provider,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_service_provider_delete(self):
        response = self.client.delete(reverse('service-provider-details', args=[self.service_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(ServiceProvider.DoesNotExist):
            ServiceProvider.objects.get(id=self.service_provider.id)

    def test_failed_delete_of_non_existed_service_provider(self):
        response = self.client.delete(reverse('service-provider-details', args=['9999']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_access(self):
        # Unset access token to simulate unauthenticated user
        self.client.cookies['access'] = None

        # Test GET method
        response = self.client.get(reverse("service-provider-details", args=[self.service_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test PUT method
        updated_service_provider = {
            "name": "test service provider name",
            "address": "updated address",
        }
        response = self.client.put(reverse('service-provider-details', args=[self.service_provider.id]),
                                   updated_service_provider, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test DELETE method
        response = self.client.delete(reverse('service-provider-details', args=[self.service_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PartsProviderListTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.part_providers = PartsProviderFactory.create_batch(size=10)

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_failed_parts_providers_retrieval_with_unauthenticated_user(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse('parts-providers'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_parts_providers_retrieval(self):
        response = self.client.get(reverse("parts-providers"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(self.part_providers))


class PartsProviderDetailsTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.parts_provider = PartsProviderFactory.create()

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_successful_retrieval_of_parts_provider(self):
        response = self.client.get(reverse("parts-provider-details", args=[self.parts_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in response.data.items():
            self.assertEqual(getattr(self.parts_provider, key), value)

    def test_failed_retrieval_of_non_existed_parts_provider(self):
        response = self.client.get(reverse('parts-provider-details', args=['9999']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_parts_provider_update(self):
        updated_parts_provider = {
            "name": "updated parts provider name",
            "address": "updated address",
            "phone_number": "9298778585"
        }
        response = self.client.put(reverse('parts-provider-details', args=[self.parts_provider.id]),
                                   updated_parts_provider, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        for key, value in updated_parts_provider.items():
            self.assertEqual(getattr(PartsProvider.objects.get(id=self.parts_provider.id), key), value)

    def test_failed_update_of_non_existed_parts_provider(self):
        updated_parts_provider = {
            "name": "updated parts provider name",
            "address": "updated address",
        }
        response = self.client.put(reverse('parts-provider-details', args=['9999']), updated_parts_provider,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_parts_provider_delete(self):
        response = self.client.delete(reverse('parts-provider-details', args=[self.parts_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(PartsProvider.DoesNotExist):
            PartsProvider.objects.get(id=self.parts_provider.id)

    def test_failed_delete_of_non_existed_parts_provider(self):
        response = self.client.delete(reverse('parts-provider-details', args=['9999']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_access(self):
        # Unset access token to simulate unauthenticated user
        self.client.cookies['access'] = None

        # Test GET method
        response = self.client.get(reverse("parts-provider-details", args=[self.parts_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test PUT method
        updated_parts_provider = {
            "name": "test parts provider name",
            "address": "updated address",
        }
        response = self.client.put(reverse('parts-provider-details', args=[self.parts_provider.id]),
                                   updated_parts_provider, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test DELETE method
        response = self.client.delete(reverse('parts-provider-details', args=[self.parts_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MaintenanceReportListViewTestCases(APITestCase):

    @classmethod
    def setUpTestData(cls):
        current_date = datetime.now().date()
        first_day_current_month = current_date.replace(day=1)
        first_day_previous_month = (first_day_current_month - timedelta(days=1)).replace(day=1)
        last_day_previous_month = first_day_current_month - timedelta(days=1)

        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicle = VehicleFactory.create(profile=cls.user_profile)
        cls.service_provider = ServiceProviderFactory.create()
        cls.parts = PartFactory.create_batch(size=20)
        cls.parts_provider = PartsProviderFactory.create()
        cls.current_month_reports = MaintenanceReportFactory.create_batch(size=5, profile=cls.user_profile, vehicle=cls.vehicle)
        for i, report in enumerate(cls.current_month_reports):
            report.start_date = first_day_current_month + timedelta(days=i + 1)
            report.save()
        cls.previous_month_reports = MaintenanceReportFactory.create_batch(size=5, profile=cls.user_profile, vehicle=cls.vehicle)
        for i, report in enumerate(cls.previous_month_reports):
            report.start_date = first_day_previous_month + timedelta(days=i + 1)
            report.save()


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
        response = self.client.get(reverse("reports"), data={"year": "2025", "month": "2", "vehicle_id": self.vehicle.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(self.current_month_reports))

    def test_creation_of_new_report(self):
        response = self.client.post(reverse("reports"), data=self.maintenance_report_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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
        cls.part_purchase_events = PartPurchaseEventFactory.create_batch(size=10)
        cls.maintenance_report = MaintenanceReportFactory.create(profile=cls.user_profile)
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

    def test_successful_maintenance_report_update(self):
        response = self.client.put(reverse('reports-details', args=[self.maintenance_report.id]), data=self.data,
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_successful_maintenance_report_deletion(self):
        response = self.client.delete(reverse("reports-details", args=[self.maintenance_report.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class MaintenanceReportOverviewTestCases(APITestCase):

    @classmethod
    def setUpTestData(cls):
        current_year = timezone.now().year
        previous_year = current_year - 1

        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicle = VehicleFactory.create(profile=cls.user_profile)
        cls.service_providers = ServiceProviderFactory.create_batch(size=5)
        cls.current_maintenance_reports = MaintenanceReportFactory.create_batch(size=10, profile=cls.user_profile, start_date=factory.LazyFunction(
            lambda: date(current_year, random.randint(1, 12), random.randint(1, 28))))
        cls.previous_maintenance_reports = MaintenanceReportFactory.create_batch(size=5, profile=cls.user_profile, start_date=factory.LazyFunction(
            lambda: date(previous_year, random.randint(1, 12), random.randint(1, 28))))
        cls.part_purchase_event = PartPurchaseEventFactory.create(maintenance_report=cls.current_maintenance_reports[0])
        cls.service_provider_event = ServiceProviderEventFactory(maintenance_report=cls.current_maintenance_reports[0])

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_successful_maintenance_report_retrieval(self):
        response = self.client.get(reverse('overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("previous_report", response.data)
        self.assertIn("current_report", response.data)
        self.assertEqual(response.data['current_report']['total_maintenance_cost'], self.part_purchase_event.cost + self.service_provider_event.cost)


class GeneralMaintenanceDataTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.parts = PartFactory.create_batch(size=5)
        cls.service_providers = ServiceProviderFactory.create_batch(size=5)
        cls.parts_providers = PartsProviderFactory.create_batch(size=5)

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
