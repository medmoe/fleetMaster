from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from django.urls import path
from rest_auth.registration.views import SocialLoginView

from .views import SignUpView, LogoutView, CustomTokenObtainPairView, TokenVerificationView, FacebookDataDeletionView


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenVerificationView.as_view(), name='verify_token'),
    path('facebook-data-deletion/', FacebookDataDeletionView.as_view(), name='fb-data-deletion'),
    path('facebook/', FacebookLogin.as_view(), name='fb_login'),

]
