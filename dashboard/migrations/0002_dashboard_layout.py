import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0001_child_profile"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DashboardLayout",
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
                ("columns", models.JSONField(default=list, verbose_name="Columns")),
                ("hidden", models.JSONField(default=list, verbose_name="Hidden cards")),
                (
                    "actions",
                    models.JSONField(default=list, verbose_name="Quick actions"),
                ),
                (
                    "hidden_actions",
                    models.JSONField(default=list, verbose_name="Hidden quick actions"),
                ),
                (
                    "options",
                    models.JSONField(default=dict, verbose_name="Card settings"),
                ),
                (
                    "child",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dashboard_layouts",
                        to="core.child",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dashboard_layouts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "default_permissions": (),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "child"), name="unique_dashboard_layout"
                    )
                ],
            },
        ),
    ]
