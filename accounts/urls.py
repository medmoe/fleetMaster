from django.urls import path

from .views import SignUpView, LogoutView, CustomTokenObtainPairView, TokenVerificationView, FacebookDataDeletionView, FacebookLogin

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenVerificationView.as_view(), name='verify_token'),
    path('facebook-data-deletion/', FacebookDataDeletionView.as_view(), name='fb-data-deletion'),
    path('dj-rest-auth/facebook/', FacebookLogin.as_view(), name='fb_login'),

]
