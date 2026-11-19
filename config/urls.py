"""Main URL configuration for the Bincom election demo."""
from django.contrib import admin
from django.urls import include, path
from election.views import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="home"),
    path("election/", include("election.urls")),
]
