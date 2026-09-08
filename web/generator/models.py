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
    image_url = models.CharField(max_length=500, blank=True, default='')
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Card Message'
        verbose_name_plural = 'Card Messages'

    def __str__(self):
        return f"[{self.role}] {self.content[:50]} (v{self.version})"

