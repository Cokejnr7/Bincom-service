from django.urls import path
from . import views

urlpatterns = [
    path("poll-units/", views.polling_units, name="polling_units"),
    path("poll-unit/<int:unit_id>/", views.polling_result, name="polling_unit_result"),
    path("lga-result/", views.lga_result, name="lga_result"),
    path("create-poll-result/", views.create_poll_result, name="create_poll_result"),
]
