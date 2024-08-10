from django.urls import path

from .views import SignUpView, LogoutView, CustomTokenObtainPairView, TokenVerificationView

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenVerificationView.as_view(), name='verify_token'),
]
