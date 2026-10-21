import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0002_dashboard_layout"),
    ]

    operations = [
        migrations.CreateModel(
            name="TimerProfile",
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
                    "kind",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("feeding", "Feeding"),
                            ("pumping", "Pumping"),
                            ("sleep", "Sleep"),
                            ("tummytime", "Tummy Time"),
                        ],
                        default="",
                        max_length=16,
                        verbose_name="Type",
                    ),
                ),
                (
                    "timer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="core.timer",
                    ),
                ),
            ],
            options={
                "default_permissions": (),
            },
        ),
    ]
