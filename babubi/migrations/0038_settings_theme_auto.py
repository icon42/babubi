from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("babubi", "0037_settings_theme"),
    ]

    operations = [
        migrations.AlterField(
            model_name="settings",
            name="theme",
            field=models.CharField(
                choices=[("auto", "Automatic"), ("light", "Light"), ("dark", "Dark")],
                default="auto",
                max_length=100,
                verbose_name="Theme",
            ),
        ),
    ]
