from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0003_timer_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="dashboardlayout",
            name="order",
            field=models.JSONField(
                default=list, verbose_name="Order on narrow screens"
            ),
        ),
    ]
