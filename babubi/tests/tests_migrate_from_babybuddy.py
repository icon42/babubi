# -*- coding: utf-8 -*-
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import CommandError, call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


def make_baby_buddy_database():
    """Puts the test database back in the shape Baby Buddy left it."""
    with connection.schema_editor(atomic=True) as editor:
        editor.alter_db_table(None, "babubi_settings", "babybuddy_settings")
        editor.execute(
            "UPDATE django_migrations SET app = 'babybuddy' WHERE app = 'babubi'"
        )
        editor.execute(
            "UPDATE django_content_type SET app_label = 'babybuddy' "
            "WHERE app_label = 'babubi'"
        )
    ContentType.objects.clear_cache()


def run():
    out = StringIO()
    call_command("migrate_from_babybuddy", stdout=out)
    return out.getvalue()


class MigrateFromBabyBuddyTestCase(TransactionTestCase):
    def count(self, sql):
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchone()[0]

    def test_moves_baby_buddy_database(self):
        migrations = self.count(
            "SELECT COUNT(*) FROM django_migrations WHERE app = 'babubi'"
        )
        make_baby_buddy_database()

        self.assertIn("Moved from Baby Buddy", run())

        tables = connection.introspection.table_names()
        self.assertIn("babubi_settings", tables)
        self.assertNotIn("babybuddy_settings", tables)
        self.assertEqual(
            self.count("SELECT COUNT(*) FROM django_migrations WHERE app = 'babubi'"),
            migrations,
        )
        self.assertEqual(
            self.count(
                "SELECT COUNT(*) FROM django_content_type "
                "WHERE app_label = 'babybuddy'"
            ),
            0,
        )
        # The moved database migrates cleanly afterwards.
        call_command("migrate", verbosity=0)

    def test_second_run_does_nothing(self):
        make_baby_buddy_database()
        run()
        self.assertIn("nothing to move", run())

    def test_babubi_database_is_left_alone(self):
        self.assertIn("nothing to move", run())

    def test_refuses_mixed_database(self):
        make_baby_buddy_database()
        with connection.schema_editor(atomic=True) as editor:
            editor.execute("CREATE TABLE babubi_settings (id integer)")
        with self.assertRaisesMessage(CommandError, "move the data by hand"):
            run()
        with connection.schema_editor(atomic=True) as editor:
            editor.execute("DROP TABLE babubi_settings")
        run()  # Leave the schema as the other tests expect it.

    def test_refuses_newer_baby_buddy(self):
        make_baby_buddy_database()
        recorder = MigrationRecorder(connection)
        recorder.record_applied("core", "0999_from_a_newer_baby_buddy")
        recorder.record_applied("webhooks", "0001_initial")
        with self.assertRaisesMessage(
            CommandError, "core.0999_from_a_newer_baby_buddy, webhooks.0001_initial"
        ):
            run()
        # Nothing was moved.
        self.assertIn("babybuddy_settings", connection.introspection.table_names())
        recorder.record_unapplied("core", "0999_from_a_newer_baby_buddy")
        recorder.record_unapplied("webhooks", "0001_initial")
        run()  # Leave the schema as the other tests expect it.
