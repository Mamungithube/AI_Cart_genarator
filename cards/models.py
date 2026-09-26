import uuid
from django.db import models

class CardSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Corporate Business Card")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    
    # Current active design state for this session (kept in-memory / JSON, no disk image files)
    front_html = models.TextField(blank=True, default="")
    back_html = models.TextField(blank=True, default="")
    css = models.TextField(blank=True, default="")
    card_data = models.JSONField(default=dict, blank=True)
    image_base64 = models.TextField(blank=True, default="")
    image_url = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['-updated_at']

    @property
    def current_state(self):
        return self.card_data

    @property
    def current_version(self):
        return self.version

    def __str__(self):
        return f"{self.title} ({self.id}) v{self.version}"


class CardMessage(models.Model):
    SENDER_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CardSession, related_name='messages', on_delete=models.CASCADE)
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    message = models.TextField(blank=True, default="")
    # In-memory only data URI or string, NO disk image files saved
    reference_image = models.TextField(blank=True, default="")
    version = models.IntegerField(default=1)
    
    front_html = models.TextField(blank=True, default="")
    back_html = models.TextField(blank=True, default="")
    css = models.TextField(blank=True, default="")
    card_data = models.JSONField(default=dict, blank=True)
    image_base64 = models.TextField(blank=True, default="")
    image_url = models.TextField(blank=True, default="")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @property
    def role(self):
        return self.sender

    @property
    def content(self):
        return self.message

    def __str__(self):
        return f"[{self.sender}] {self.session.id}: {self.message[:30]}"


class GeneratedCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt = models.TextField(blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")
    designation = models.CharField(max_length=255, blank=True, default="")
    company_name = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=255, blank=True, default="")
    email = models.CharField(max_length=255, blank=True, default="")
    website = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.company_name}"
