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
