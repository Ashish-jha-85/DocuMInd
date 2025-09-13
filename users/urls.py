from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserProfileView, LogoutView, LoginView

urlpatterns = [
    # path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),  # returns access + refresh
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", UserProfileView.as_view(), name="user_profile"),
    path("logout/", LogoutView.as_view(), name="logout"),  # optional
]
