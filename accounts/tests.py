from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile
from .factories import UserProfileFactory


class SignUpTestCases(APITestCase):
    def setUp(self):
        self.data = {
            'user': {
                'username': 'new_username',
                'password': 'password',
                'email': 'test@test.com',
            },
        }
        self.existed_user = User.objects.create_user(username="user", password="password", email="user@test.com")
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
    def setUp(self):
        self.user_profile = UserProfileFactory.create()

    def test_successful_login(self):
        response = self.client.post(reverse("login"), {"username": self.user_profile.user.username, "password": "password"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Make sure that the data is returned in the response
        self.assertEqual(response.data['user']['username'], self.user_profile.user.username)
        self.assertEqual(response.data['user']['email'], self.user_profile.user.email)
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


class CustomTokenRefreshViewTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse('token_refresh')
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_successful_token_refresh(self):
        refresh = str(RefreshToken.for_user(self.user))
        self.client.cookies['refresh'] = refresh
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertTrue('access' in response.cookies)

    def test_missing_refresh_token(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_refresh_token(self):
        self.client.cookies['refresh'] = 'invalid_refresh_token'

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Token is invalid or expired')