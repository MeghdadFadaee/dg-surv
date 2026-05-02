from django.urls import path

from . import views


urlpatterns = [
    path("surveys/", views.survey_list, name="survey-list"),
    path("surveys/<slug:slug>/", views.survey_detail, name="survey-detail"),
    path(
        "surveys/<slug:slug>/responses/",
        views.submit_survey_response,
        name="survey-response-submit",
    ),
]
