from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse_lazy
from django.views.generic import TemplateView


from . import views

app_name = "core"
urlpatterns = [
    path("signup", views.SignupView.as_view(), name="signup"),
    path("user", views.userindex, name="user"),
    path(
        "confirm",
        TemplateView.as_view(template_name="registration/confirm_request.html"),
        name="confirm",
    ),
    path("activate/<slug:uidb64>/<slug:token>/", views.activate, name="activate"),
    path("resend", views.Resend.as_view(), name="resend"),
    # Forward all other urls to django's default auth system
    # logout, password_reset, etc
    path("", include("django.contrib.auth.urls")),
]

auth_views.PasswordResetView.success_url = reverse_lazy("core:password_reset_done")
