# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.loader import MigrationLoader

OLD_LABEL = "babybuddy"
NEW_LABEL = "babubi"


class Command(BaseCommand):
    help = (
        "Moves a database created by Baby Buddy to the Babubi app label: "
        "renames its tables, content types and migration records. Does "
        "nothing when there is nothing left to move, so it is safe to run on "
        "every start, before migrate."
    )

    def handle(self, *args, **kwargs):
        tables = connection.introspection.table_names()
        if "django_migrations" not in tables:
            self.stdout.write("Empty database, nothing to move.")
            return

        old_tables = [t for t in tables if t.startswith(OLD_LABEL + "_")]
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app = %s", [OLD_LABEL]
            )
            (old_migrations,) = cursor.fetchone()
        if not old_tables and not old_migrations:
            self.stdout.write("Nothing left from Baby Buddy, nothing to move.")
            return

        # A newer Baby Buddy than the one Babubi builds on has migrations
        # Babubi lacks: its schema has columns the models do not know, so the
        # database is left as it is until Babubi catches up.
        unknown = self.unknown_migrations()
        if unknown:
            raise CommandError(
                "This database comes from a newer Baby Buddy than the one Babubi "
                "builds on: it has migrations Babubi does not know ({}). Update "
                "Babubi before moving it; nothing was changed.".format(
                    ", ".join(unknown)
                )
            )

        # Both labels at once means migrate already ran with the new label
        # and created fresh tables; merging them is a manual job.
        new_tables = [t for t in tables if t.startswith(NEW_LABEL + "_")]
        if new_tables:
            raise CommandError(
                "Found both {} and {} tables ({}); move the data by hand.".format(
                    OLD_LABEL, NEW_LABEL, ", ".join(sorted(old_tables + new_tables))
                )
            )

        with connection.schema_editor(atomic=True) as editor:
            for old in old_tables:
                editor.alter_db_table(None, old, NEW_LABEL + old[len(OLD_LABEL) :])
            editor.execute(
                "UPDATE django_migrations SET app = %s WHERE app = %s",
                [NEW_LABEL, OLD_LABEL],
            )
            if "django_content_type" in tables:
                editor.execute(
                    "UPDATE django_content_type SET app_label = %s WHERE app_label = %s",
                    [NEW_LABEL, OLD_LABEL],
                )

        self.stdout.write(
            "Moved from Baby Buddy: {} table(s), {} migration record(s).".format(
                len(old_tables), old_migrations
            )
        )

    def unknown_migrations(self):
        """The applied migrations, as Baby Buddy recorded them, with no file here."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT app, name FROM django_migrations")
            applied = cursor.fetchall()
        known = MigrationLoader(None, ignore_no_migrations=True).disk_migrations
        return sorted(
            "{}.{}".format(app, name)
            for app, name in applied
            if (NEW_LABEL if app == OLD_LABEL else app, name) not in known
        )
