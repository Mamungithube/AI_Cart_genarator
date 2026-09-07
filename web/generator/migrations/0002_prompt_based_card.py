# Safe migration - handles already-applied SQL changes gracefully
from django.db import migrations, models
from django.db import connection


def safe_add_prompt(apps, schema_editor):
    """Add prompt column only if it doesn't exist yet."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='generator_generatedcard' AND column_name='prompt'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE generator_generatedcard ADD COLUMN prompt TEXT NOT NULL DEFAULT ''")


def safe_remove_theme(apps, schema_editor):
    """Remove theme column only if it exists."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='generator_generatedcard' AND column_name='theme'
        """)
        if cursor.fetchone():
            cursor.execute("ALTER TABLE generator_generatedcard DROP COLUMN theme")


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0001_initial'),
    ]

    operations = [
        # Use RunPython for safe idempotent schema changes
        migrations.RunPython(safe_add_prompt, migrations.RunPython.noop),
        migrations.RunPython(safe_remove_theme, migrations.RunPython.noop),

        # Update Django's internal field state (no DB changes)
        migrations.AlterField(
            model_name='generatedcard',
            name='name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='generatedcard',
            name='designation',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='generatedcard',
            name='phone',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='generatedcard',
            name='email',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name='generatedcard',
            name='website',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name='generatedcard',
            name='company_name',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
