from django.urls import path
from .views import home, info_score

urlpatterns = [
    path('', home, name='home'),
    path('info_score/<str:country_name>', info_score, name='info_score'),
]