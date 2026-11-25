from django.urls import path

from offers.views import search

urlpatterns = [path("", search, name="search")]
