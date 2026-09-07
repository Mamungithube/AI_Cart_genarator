from django.contrib import admin
from .models import GeneratedCard


@admin.register(GeneratedCard)
class GeneratedCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'company_name', 'email', 'created_at')
    search_fields = ('name', 'designation', 'email', 'company_name', 'prompt')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
