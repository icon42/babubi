import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0038_tummytime_notes"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChildProfile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sex",
                    models.CharField(
                        blank=True,
                        choices=[("boy", "Boy"), ("girl", "Girl")],
                        default="",
                        max_length=8,
                        verbose_name="Sex",
                    ),
                ),
                (
                    "child",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="core.child",
                    ),
                ),
            ],
            options={
                "default_permissions": (),
            },
        ),
    ]
