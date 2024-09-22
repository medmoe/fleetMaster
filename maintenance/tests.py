from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from .factories import PartFactory, PartsProviderFactory, ServiceProviderFactory
from .models import Part, PartsProvider, ServiceProvider


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
        response = self.client.put(reverse('service-provider-details', args=[self.service_provider.id]), updated_service_provider, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        for key, value in updated_service_provider.items():
            self.assertEqual(getattr(ServiceProvider.objects.get(id=self.service_provider.id), key), value)

    def test_failed_update_of_non_existed_service_provider(self):
        updated_service_provider = {
            "name": "updated service provider name",
            "address": "updated address",
        }
        response = self.client.put(reverse('service-provider-details', args=['9999']), updated_service_provider, format='json')
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
        response = self.client.put(reverse('service-provider-details', args=[self.service_provider.id]), updated_service_provider, format="json")
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
        response = self.client.put(reverse('parts-provider-details', args=[self.parts_provider.id]), updated_parts_provider, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        for key, value in updated_parts_provider.items():
            self.assertEqual(getattr(PartsProvider.objects.get(id=self.parts_provider.id), key), value)

    def test_failed_update_of_non_existed_parts_provider(self):
        updated_parts_provider = {
            "name": "updated parts provider name",
            "address": "updated address",
        }
        response = self.client.put(reverse('parts-provider-details', args=['9999']), updated_parts_provider, format='json')
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
        response = self.client.put(reverse('parts-provider-details', args=[self.parts_provider.id]), updated_parts_provider, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test DELETE method
        response = self.client.delete(reverse('parts-provider-details', args=[self.parts_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
