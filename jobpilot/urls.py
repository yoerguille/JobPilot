from django.urls import path

from offers.views import application_detail, application_list, mark_application, search

urlpatterns = [
    path("", search, name="search"),
    path("candidaturas/", application_list, name="application_list"),
    path("candidaturas/marcar/<str:posting>/", mark_application, name="mark_application"),
    path("candidaturas/<int:pk>/", application_detail, name="application_detail"),
]
