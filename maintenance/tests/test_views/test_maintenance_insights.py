from datetime import datetime, date

from django.db import transaction
from django.db.models import Sum
from django.urls import reverse
from factory import RelatedFactoryList
from factory.fuzzy import FuzzyDate
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from maintenance.models import MaintenanceReport
from vehicles.factories import VehicleFactory


class FleetWideOverviewViewTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.access_token = AccessToken.for_user(cls.user_profile.user)

        # Mock vehicles and maintenance reports
        try:
            with transaction.atomic():
                cls.vehicles = VehicleFactory.create_batch(
                    size=6,
                    profile=cls.user_profile,
                    maintenance_reports=RelatedFactoryList(
                        'maintenance.factories.MaintenanceReportFactory',
                        factory_related_name='vehicle',
                        size=2,
                        start_date=FuzzyDate(date(datetime.now().year, 1, 1), date(datetime.now().year, 12, 31)),
                        profile=cls.user_profile,
                        part_purchase_events=RelatedFactoryList(
                            'maintenance.factories.PartPurchaseEventFactory',
                            factory_related_name='maintenance_report',
                            size=3,
                        ),
                        service_provider_events=RelatedFactoryList(
                            'maintenance.factories.ServiceProviderEventFactory',
                            factory_related_name='maintenance_report',
                            size=3,
                        )
                    )
                )
        except Exception as e:
            print(e)

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_failed_fleet_wide_overview_retrieval_with_unauthenticated_user(self):
        self.client.cookies['access'] = None
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_fleet_wide_overview_retrieval(self):
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that the response contains the correct numbers
        total_cost = MaintenanceReport.objects.aggregate(Sum('total_cost'))['total_cost__sum']
        self.assertEqual(response.data["total_maintenance_cost"]["year"], total_cost)
        self.assertEqual(response.data["YoY"], 0.0) # All the reports created in the setup created with start_date=current_year
        self.assertEqual(response.data["vehicle_avg_cost"], total_cost / len(self.vehicles))

    def test_correct_number_for_vehicle_health(self):
        # We need to modify the dates of the service in our fleet
        # All vehicles have good health
        for vehicle in self.vehicles:
            vehicle.last_service_date = date(2025, 1, 1)
            vehicle.next_service_due = date(2025, 3,1)
        response = self.client.get(reverse('fleet-wide-overview'))
        self.assertEqual(response.data["vehicle_avg_health"]["good"], 6.0)





