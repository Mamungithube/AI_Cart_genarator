from django.urls import path
from .views import ProcessCardView, EnhanceCardView

urlpatterns = [
    path('api/process-card/', ProcessCardView.as_view(), name='api-process-card'),
    path('process-card', ProcessCardView.as_view(), name='process-card'),
    path('api/enhance-card/', EnhanceCardView.as_view(), name='api-enhance-card'),
    path('enhance-card', EnhanceCardView.as_view(), name='enhance-card'),
]
