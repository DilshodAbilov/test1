from django.urls import path
from .views import AdminRegisterView, AdminLoginView, GoogleAuthView

urlpatterns = [
    path("admin/register/", AdminRegisterView.as_view(), name="admin-register"),
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("google/auth/", GoogleAuthView.as_view(), name="google-auth"),
]
