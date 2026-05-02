"""Root URL routes for the survey service."""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


urlpatterns = [
    path("", TemplateView.as_view(template_name="welcome.html"), name="welcome"),
    path("docs/", TemplateView.as_view(template_name="docs.html"), name="docs"),
    path("admin/", admin.site.urls),
    path("api/", include("surveys.urls")),
]
