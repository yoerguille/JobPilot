from django.urls import path

from offers.cv import cv_offer_draft, cv_preview, cv_profile
from offers.views import application_detail, application_list, mark_application, search

urlpatterns = [
    path("", search, name="search"),
    path("perfil-cv/", cv_profile, name="cv_profile"),
    path("perfil-cv/vista-previa/", cv_preview, name="cv_preview"),
    path("perfil-cv/oferta/<str:posting>/", cv_offer_draft, name="cv_offer_draft"),
    path("candidaturas/", application_list, name="application_list"),
    path("candidaturas/marcar/<str:posting>/", mark_application, name="mark_application"),
    path("candidaturas/<int:pk>/", application_detail, name="application_detail"),
]
