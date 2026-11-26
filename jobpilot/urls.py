from django.urls import path

from offers.views import application_detail, mark_application, search

urlpatterns = [
    path("", search, name="search"),
    path("candidaturas/marcar/<str:posting>/", mark_application, name="mark_application"),
    path("candidaturas/<int:pk>/", application_detail, name="application_detail"),
]
