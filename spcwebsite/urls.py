"""
URL configuration for spcwebsite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html"), name="index"),
    path("accounts/", include("core.urls")),
    path("eval/", include("eval.urls")),
    path("admin/", admin.site.urls),
    path(
        "download",
        TemplateView.as_view(template_name="download.html"),
        name="download",
    ),
    path(
        "faq",
        TemplateView.as_view(template_name="faq.html"),
        name="faq",
    ),
    path("captcha/", include("captcha.urls")),
]

if settings.DEBUG:
    urlpatterns.extend([static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)])
else:
    # TODO: Fix this! 
    urlpatterns.extend(
        [
            path("media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
        ]
    )
