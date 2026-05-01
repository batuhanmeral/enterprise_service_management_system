from django.urls import path

from . import api_views

urlpatterns = [
    path('', api_views.DashboardAPIView.as_view(), name='api_dashboard'),
]
