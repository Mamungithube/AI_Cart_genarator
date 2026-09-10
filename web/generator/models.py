import uuid
from django.db import models


class GeneratedCard(models.Model):
    # Original user prompt
    prompt = models.TextField(default='')

    # AI-extracted structured data
    name = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.CharField(max_length=150, blank=True)
    website = models.CharField(max_length=150, blank=True)
    company_name = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Generated Card'
        verbose_name_plural = 'Generated Cards'

    def __str__(self):
        return f"{self.name} — {self.designation} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class CardSession(models.Model):
    """
    Stateful conversational session for iterative visiting card design.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_state = models.JSONField(default=dict, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Card Session'
        verbose_name_plural = 'Card Sessions'

    def __str__(self):
        name = self.current_state.get('name', 'Untitled')
        return f"Session {self.id} — {name} (v{self.version})"


class CardMessage(models.Model):
    """
    Individual message turn in the card design conversation.
    """
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )
    session = models.ForeignKey(CardSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    card_data = models.JSONField(default=dict, blank=True, null=True)
    image_url = models.TextField(blank=True, default='')
    image_base64 = models.TextField(blank=True, default='')
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Card Message'
        verbose_name_plural = 'Card Messages'

    def __str__(self):
        return f"[{self.role}] {self.content[:50]} (v{self.version})"


class OpenAIKeyConfig(models.Model):
    """
    Stores AES-256 encrypted OpenAI API Key in the database.
    Allows clients to rotate/change API key dynamically without redeploying containers.
    """
    encrypted_key = models.TextField(help_text="AES-256 Fernet authenticated ciphertext")
    key_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256 hash fingerprint")
    masked_key = models.CharField(max_length=32, blank=True, help_text="Safe masked preview e.g. sk-proj...1234")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'OpenAI Key Configuration'
        verbose_name_plural = 'OpenAI Key Configurations'

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"OpenAI Key ({self.masked_key}) - {status}"

