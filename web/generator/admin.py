from django.contrib import admin
from .models import GeneratedCard, CardSession, CardMessage


@admin.register(GeneratedCard)
class GeneratedCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'company_name', 'email', 'created_at')
    search_fields = ('name', 'designation', 'email', 'company_name', 'prompt')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)


class CardMessageInline(admin.TabularInline):
    model = CardMessage
    extra = 0
    readonly_fields = ('role', 'content', 'card_data', 'image_url', 'version', 'created_at')


@admin.register(CardSession)
class CardSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_name', 'version', 'created_at', 'updated_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [CardMessageInline]

    def get_name(self, obj):
        return obj.current_state.get('name', 'Untitled')
    get_name.short_description = 'Card Name'


@admin.register(CardMessage)
class CardMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'version', 'created_at')
    list_filter = ('role', 'version', 'created_at')

