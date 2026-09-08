from django.urls import path
from .views import (
    GenerateCardAPIView,
    HealthCheckView,
    CardChatAPIView,
    CardSessionHistoryAPIView,
)

urlpatterns = [
    path('api/generate-card/', GenerateCardAPIView.as_view(), name='generate-card'),
    path('api/chat-card/', CardChatAPIView.as_view(), name='card-chat'),
    path('api/chat-card/<uuid:session_id>/', CardSessionHistoryAPIView.as_view(), name='card-chat-history'),
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
]
