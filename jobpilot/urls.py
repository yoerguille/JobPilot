from django.urls import path

from offers.cv import cv_offer_draft, cv_preview, cv_profile, cv_version, cv_versions, download_cv_version, save_cv_version
from offers.views import application_detail, application_list, mark_application, pending_applications, save_interested_offer, search

urlpatterns = [
    path("", search, name="search"),
    path("perfil-cv/", cv_profile, name="cv_profile"),
    path("perfil-cv/vista-previa/", cv_preview, name="cv_preview"),
    path("perfil-cv/oferta/<str:posting>/", cv_offer_draft, name="cv_offer_draft"),
    path("perfil-cv/oferta/<str:posting>/guardar-version/", save_cv_version, name="save_cv_version"),
    path("perfil-cv/versiones/", cv_versions, name="cv_versions"),
    path("perfil-cv/versiones/<int:pk>/", cv_version, name="cv_version"),
    path("perfil-cv/versiones/<int:pk>/pdf/", download_cv_version, name="download_cv_version"),
    path("candidaturas/", application_list, name="application_list"),
    path("candidaturas/pendientes/", pending_applications, name="pending_applications"),
    path("candidaturas/interesa/<str:posting>/", save_interested_offer, name="save_interested_offer"),
    path("candidaturas/marcar/<str:posting>/", mark_application, name="mark_application"),
    path("candidaturas/<int:pk>/", application_detail, name="application_detail"),
]
