from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserProfileFactory
from maintenance.factories import PartsProviderFactory
from maintenance.models import PartsProvider


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
        cls.parts_provider = PartsProviderFactory.create(profile=cls.user_profile)

    def setUp(self):
        self.client.cookies['access'] = self.access_token

    def test_successful_retrieval_of_parts_provider(self):
        response = self.client.get(reverse("parts-provider-details", args=[self.parts_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

    def test_failed_update_of_parts_provider_when_not_owner(self):
        new_user_profile = UserProfileFactory.create()
        new_parts_provider = PartsProviderFactory.create(profile=new_user_profile)
        updated_parts_provider = {
            "name": "updated parts provider name",
            "address": "updated address",
        }
        response = self.client.put(reverse('parts-provider-details', args=[new_parts_provider.id]),
                                   updated_parts_provider, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_delete_of_parts_provider_when_not_owner(self):
        new_user_profile = UserProfileFactory.create()
        new_parts_provider = PartsProviderFactory.create(profile=new_user_profile)
        response = self.client.delete(reverse('parts-provider-details', args=[new_parts_provider.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
