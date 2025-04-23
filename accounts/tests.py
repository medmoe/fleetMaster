from unittest.mock import patch

from allauth.socialaccount.models import SocialApp, SocialAccount
from allauth.socialaccount.signals import social_account_added
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase, RequestFactory
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from drivers.factories import DriverFactory
from vehicles.factories import VehicleFactory
from .factories import UserProfileFactory, UserFactory
from .models import UserProfile


class SignUpTestCases(APITestCase):
    def setUp(self):
        self.data = {
            'user': {
                'username': 'new_username',
                'password': 'password',
                'email': 'test@test.com',
            },
        }
        self.existed_user = UserFactory.create()
        self.initial_users_count = User.objects.count()

    def test_successful_registration(self):
        response = self.client.post(reverse('signup'), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(User.objects.count(), self.initial_users_count)
        # Assert user data is registered correctly
        created_user = UserProfile.objects.filter(user__username=response.data['user']['username']).first()
        user_data = self.data['user']
        attributes = ['username', 'email', 'password']
        for attribute in attributes:
            if attribute == 'password':
                self.assertNotEqual(getattr(created_user.user, attribute), user_data[attribute])
            else:
                self.assertEqual(getattr(created_user.user, attribute), user_data[attribute])

    def test_failed_registration_without_username(self):
        self.data['user'].pop('username')
        response = self.client.post(reverse('signup'), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), self.initial_users_count)

    def test_failed_registration_without_email(self):
        self.data['user'].pop('email')
        response = self.client.post(reverse('signup'), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), self.initial_users_count)

    def test_failed_registration_without_password(self):
        self.data['user'].pop('password')
        response = self.client.post(reverse('signup'), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), self.initial_users_count)

    def test_failed_registration_with_existed_username(self):
        self.data['user']['username'] = self.existed_user.username
        response = self.client.post(reverse('signup'), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), self.initial_users_count)

    def test_failed_registration_with_existed_email(self):
        self.data['user']['email'] = self.existed_user.email
        response = self.client.post(reverse('signup'), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), self.initial_users_count)

    def test_failed_registration_with_invalid_email(self):
        self.data['user']['email'] = "Invalid Email"
        response = self.client.post(reverse('signup'), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), self.initial_users_count)


class LoginTestCases(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_profile = UserProfileFactory.create()
        cls.vehicles = VehicleFactory.create_batch(size=2, profile=cls.user_profile)
        cls.drivers = DriverFactory.create_batch(size=5, profile=cls.user_profile)

    def test_successful_login(self):
        response = self.client.post(reverse("login"), {"username": self.user_profile.user.username, "password": "password"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert check on returned data
        for key, expected_value in [('username', self.user_profile.user.username), ('email', self.user_profile.user.email)]:
            self.assertEqual(response.data['user'][key], expected_value)
        for key, expected_length in [('drivers', len(self.drivers)), ('vehicles', len(self.vehicles))]:
            self.assertIn(key, response.data)
            self.assertEqual(len(response.data[key]), expected_length)

        # Make sure the password is not included in the response
        self.assertNotIn('password', response.data['user'])

        # Make sure that the access and refresh tokens are embedded in the cookies
        for key in ('refresh', 'access'):
            self.assertIn(key, response.cookies)

    def test_failed_login_with_wrong_credentials(self):
        response = self.client.post(reverse("login"), {"username": self.user_profile.user.username, "password": "InvalidPassword"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTestCases(APITestCase):
    def setUp(self) -> None:
        self.user_profile = UserProfileFactory.create()

    def test_successful_logout(self):
        response = self.client.post(reverse('login'), {"username": self.user_profile.user.username, "password": "password"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access = response.cookies.get('access')
        refresh = response.cookies.get('refresh')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertFalse(OutstandingToken.objects.filter(token=access.value).exists())
        self.assertTrue(BlacklistedToken.objects.filter(token__token=refresh.value).exists())


class TokenVerificationTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse('verify_token')
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.force_authenticate(user=self.user)

    def test_valid_access_token(self):
        access = str(AccessToken.for_user(self.user))
        self.client.cookies['access'] = access
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_access_token(self):
        self.client.cookies['access'] = "invalid_access_token"
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_access_token(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_token_refresh(self):
        refresh = str(RefreshToken.for_user(self.user))
        self.client.cookies['refresh'] = refresh
        self.client.cookies['access'] = "access_token"
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.cookies)
        self.assertTrue('access' in response.cookies)

    def test_missing_refresh_token(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_refresh_token(self):
        self.client.cookies['refresh'] = 'invalid_refresh_token'
        self.client.cookies['access'] = "access_token"

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Token is invalid or expired')

    def test_token_refresh_fail_when_user_does_not_exist(self):
        self.client.force_authenticate(user=None)
        refresh = str(RefreshToken.for_user(self.user))
        self.client.cookies['refresh'] = refresh
        self.client.cookies['access'] = "access_token"
        # remove the user
        UserProfile.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)



class UserProfileSignalTests(TestCase):

    def test_social_account_signal(self):
        """Test that a UserProfile is created when a social account is added"""
        # Setup
        factory = RequestFactory()
        request = factory.get('/')

        # Create a user but delete their profile to simulate a social login without profile
        user = User.objects.create_user(
            username='socialuser',
            email='social@example.com',
            password='socialpass'
        )
        UserProfile.objects.filter(user=user).delete()
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

        # Create a mock SocialLogin object
        class MockSocialLogin:
            def __init__(self, user):
                self.user = user

        sociallogin = MockSocialLogin(user)

        # Manually send the signal
        social_account_added.send(
            sender=SocialAccount,
            request=request,
            sociallogin=sociallogin
        )

        # Check that a profile was created by the signal
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
