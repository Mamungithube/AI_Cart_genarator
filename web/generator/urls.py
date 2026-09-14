from django.urls import path
from .views import (
    HealthCheckView,
    CardChatAPIView,
    CardSessionHistoryAPIView,
    OpenAIKeyConfigAPIView,
)

urlpatterns = [
    path('', HealthCheckView.as_view(), name='root-health'),
    path('api/generate-card/', CardChatAPIView.as_view(), name='card-chat'),
    path('api/generate-card/<uuid:session_id>/', CardSessionHistoryAPIView.as_view(), name='card-chat-history'),
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    path('health', HealthCheckView.as_view(), name='health-short'),
    path('api/config/openai-key/', OpenAIKeyConfigAPIView.as_view(), name='api-config-openai-key'),
    path('config/openai-key', OpenAIKeyConfigAPIView.as_view(), name='config-openai-key'),
]
