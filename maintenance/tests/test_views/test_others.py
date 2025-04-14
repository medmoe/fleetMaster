import random
from datetime import date

import factory
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from maintenance.factories import MaintenanceReportFactory, PartPurchaseEventFactory, ServiceProviderEventFactory, ServiceProviderFactory, \
    PartFactory, PartsProviderFactory
from vehicles.factories import VehicleFactory


class MaintenanceReportOverviewTestCases(APITestCase):

    @classmethod
    def setUpTestData(cls):
        current_year = timezone.now().year
        previous_year = current_year - 1
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)
        cls.vehicle = VehicleFactory.create(profile=cls.user_profile)
        cls.other_vehicle = VehicleFactory.create(profile=cls.user_profile)
        cls.service_providers = ServiceProviderFactory.create_batch(size=5)
        cls.current_maintenance_reports = MaintenanceReportFactory.create_batch(size=10, profile=cls.user_profile, vehicle=cls.vehicle,
                                                                                start_date=factory.LazyFunction(
                                                                                    lambda: date(current_year, random.randint(1, 12),
                                                                                                 random.randint(1, 28))))
        cls.previous_maintenance_reports = MaintenanceReportFactory.create_batch(size=5, profile=cls.user_profile, vehicle=cls.vehicle,
                                                                                 start_date=factory.LazyFunction(
                                                                                     lambda: date(previous_year, random.randint(1, 12),
                                                                                                  random.randint(1, 28))))

        cls.part_purchase_event = PartPurchaseEventFactory.create(maintenance_report=cls.current_maintenance_reports[0])
        cls.service_provider_event = ServiceProviderEventFactory(maintenance_report=cls.current_maintenance_reports[0])

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_successful_maintenance_report_retrieval(self):
        response = self.client.get(reverse('overview'), data={"vehicle_id": self.vehicle.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        m, n = len(self.current_maintenance_reports), len(self.previous_maintenance_reports)
        self.assertEqual(len(response.data), m + n)


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
