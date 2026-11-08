import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_tummytime_notes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="diaperchange",
            name="color",
            field=models.CharField(
                blank=True,
                max_length=255,
                validators=[core.models.validate_diaper_colors],
                verbose_name="Color",
            ),
        ),
    ]
