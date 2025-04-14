from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from maintenance.factories import ServiceProviderFactory
from maintenance.models import ServiceProvider


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
