from django.urls import path

from .views import about, country, country_api, goal, healthz, home, info_score, search

urlpatterns = [
    path("", home, name="home"),
    path("about/", about, name="about"),
    path("search/", search, name="search"),
    path("country/<str:country_name>/", country, name="country"),
    path("goal/<int:number>/", goal, name="goal"),
    path("api/country/<str:country_name>/", country_api, name="country_api"),
    path("healthz", healthz, name="healthz"),
    # The original URL shape, kept so existing links keep working.
    path("info_score/<str:country_name>", info_score, name="info_score"),
]
