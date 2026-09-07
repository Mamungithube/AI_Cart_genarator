from django.urls import path
from .views import GenerateCardAPIView, HealthCheckView

urlpatterns = [
    path('api/generate-card/', GenerateCardAPIView.as_view(), name='generate-card'),
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
]
