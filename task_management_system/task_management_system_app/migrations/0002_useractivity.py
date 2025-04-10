# Generated by Django 5.1 on 2025-03-11 17:25

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("task_management_system_app", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserActivity",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "activity_type",
                    models.CharField(
                        choices=[("LOGIN", "Login"), ("LOGOUT", "Logout")],
                        max_length=10,
                    ),
                ),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
