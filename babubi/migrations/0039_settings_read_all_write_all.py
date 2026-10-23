from django.db import migrations, models

# The fork's caregiver group, replaced by the per-user permission matrix.
CAREGIVER_GROUP = "caregiver"
READ_ONLY_GROUP = "read_only"


def groups_to_matrix(apps, schema_editor):
    """
    Give each member of the read-only group the "reads everything" flag, and
    each member of the caregiver group that group's permissions as their own,
    then drop the caregiver group. Group memberships are left as they are.
    """
    Group = apps.get_model("auth", "Group")
    Settings = apps.get_model("babubi", "Settings")
    read_only = Group.objects.filter(name=READ_ONLY_GROUP).first()
    if read_only is not None:
        Settings.objects.filter(user__groups=read_only).update(read_all=True)
    caregiver = Group.objects.filter(name=CAREGIVER_GROUP).first()
    if caregiver is not None:
        permissions = list(caregiver.permissions.all())
        for user in caregiver.user_set.all():
            user.user_permissions.add(*permissions)
        caregiver.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("babubi", "0038_settings_theme_auto"),
    ]

    operations = [
        migrations.AddField(
            model_name="settings",
            name="read_all",
            field=models.BooleanField(default=False, verbose_name="Reads everything"),
        ),
        migrations.AddField(
            model_name="settings",
            name="write_all",
            field=models.BooleanField(default=False, verbose_name="Writes everything"),
        ),
        migrations.RunPython(groups_to_matrix, migrations.RunPython.noop),
    ]
