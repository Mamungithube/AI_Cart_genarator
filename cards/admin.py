from django.contrib import admin
from .models import CardSession, CardMessage

class CardMessageInline(admin.TabularInline):
    model = CardMessage
    extra = 0
    readonly_fields = ('sender', 'message', 'reference_image', 'created_at')

@admin.register(CardSession)
class CardSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'id', 'created_at', 'updated_at')
    search_fields = ('title', 'id')
    inlines = [CardMessageInline]

@admin.register(CardMessage)
class CardMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'sender', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('message',)
