import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0002_prompt_based_card'),
    ]

    operations = [
        migrations.CreateModel(
            name='CardSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('current_state', models.JSONField(blank=True, default=dict)),
                ('version', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Card Session',
                'verbose_name_plural': 'Card Sessions',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='CardMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=20)),
                ('content', models.TextField()),
                ('card_data', models.JSONField(blank=True, default=dict, null=True)),
                ('image_url', models.CharField(blank=True, default='', max_length=500)),
                ('version', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='generator.cardsession')),
            ],
            options={
                'verbose_name': 'Card Message',
                'verbose_name_plural': 'Card Messages',
                'ordering': ['created_at'],
            },
        ),
    ]
